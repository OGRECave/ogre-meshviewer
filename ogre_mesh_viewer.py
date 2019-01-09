import Ogre
import OgreRTShader
import OgreOverlay
import OgreBites
import OgreImgui
from OgreImgui import *

import os.path

RGN_MESHVIEWER = "OgreMeshViewer"

# we dispatch input events ourselves to give imgui precedence
class InputDispatcher(OgreBites.InputListener):

    def __init__(self, camman):
        OgreBites.InputListener.__init__(self)
        self.camman = camman

    def keyPressed(self, evt):
        if ImguiManager.getSingleton().keyPressed(evt):
            return True

        return self.camman.keyPressed(evt)

    def keyReleased(self, evt):
        if ImguiManager.getSingleton().keyReleased(evt):
            return True

        return self.camman.keyReleased(evt)

    def mouseMoved(self, evt):
        if ImguiManager.getSingleton().mouseMoved(evt):
            return True

        return self.camman.mouseMoved(evt)

    def mousePressed(self, evt):
        if ImguiManager.getSingleton().mousePressed(evt):
            return True

        return self.camman.mousePressed(evt)

    def mouseReleased(self, evt):
        if ImguiManager.getSingleton().mouseReleased(evt):
            return True

        return self.camman.mouseReleased(evt)

    def mouseWheelRolled(self, evt):
        if ImguiManager.getSingleton().mouseWheelRolled(evt):
            return True

        return self.camman.mouseWheelRolled(evt)


class MeshViewer(OgreBites.ApplicationContext, OgreBites.InputListener):

    def __init__(self, meshname, rescfg):
        OgreBites.ApplicationContext.__init__(self, "OgreMeshViewer", False)
        OgreBites.InputListener.__init__(self)

        self.show_about = False
        self.show_metrics = False
        self.meshname = os.path.basename(meshname)
        self.meshdir = os.path.dirname(meshname)
        self.rescfg = rescfg
        self.highlighted = -1
        self.orig_mat = None
        self.highlight_mat = None
        self.restart = False

        self.active_controllers = {}

    def keyPressed(self, evt):
        if evt.keysym.sym == OgreBites.SDLK_ESCAPE:
            self.getRoot().queueEndRendering()
        elif evt.keysym.sym == ord("b"):
            self._toggle_bbox()
        elif evt.keysym.sym == ord("a"):
            self._toggle_axes()

        return True

    def mousePressed(self, evt):
        if evt.clicks != 2:
            return True
        vp = self.cam.getViewport()
        ray = self.cam.getCameraToViewportRay(evt.x / vp.getActualWidth(), evt.y / vp.getActualHeight())
        self.ray_query.setRay(ray)
        for hit in self.ray_query.execute():
            self.camman.setPivotOffset(ray.getPoint(hit.distance))
            break
        return True

    def _toggle_bbox(self):
        enode = self.entity.getParentSceneNode()
        enode.showBoundingBox(not enode.getShowBoundingBox())

    def _toggle_axes(self):
        self.axes.setVisible(not self.axes.getVisible())

    def draw_about(self):
        flags = ImGuiWindowFlags_AlwaysAutoResize
        self.show_about = Begin("About OgreMeshViewer", self.show_about, flags)[1]
        Text("By Pavel Rojtberg")
        Text("OgreMeshViewer is licensed under the MIT License, see LICENSE for more information.")
        Separator()
        BulletText("Ogre:      %s" % Ogre.__version__)
        BulletText("OgreImgui: %s" % OgreImgui.__version__)
        End()

    def draw_metrics(self):
        win = self.getRenderWindow()
        stats = win.getStatistics()

        SetNextWindowPos(ImVec2(win.getWidth() - 10, win.getHeight() - 10), ImGuiCond_Always, ImVec2(1, 1))
        SetNextWindowBgAlpha(0.3)
        flags = ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_AlwaysAutoResize | ImGuiWindowFlags_NoSavedSettings | ImGuiWindowFlags_NoFocusOnAppearing | ImGuiWindowFlags_NoNav
        self.show_metrics = Begin("Metrics", self.show_metrics, flags)[1]
        Text("Metrics")
        Separator()
        Text("Average FPS: {:.2f}".format(stats.avgFPS))
        Text("Batches: {}".format(stats.batchCount))
        Text("Triangles: {}".format(stats.triangleCount))
        End()

    def frameStarted(self, evt):
        OgreBites.ApplicationContext.frameStarted(self, evt)

        ImguiManager.getSingleton().newFrame(
            evt.timeSinceLastFrame,
            Ogre.Rect(0, 0, self.getRenderWindow().getWidth(), self.getRenderWindow().getHeight()))

        if BeginMainMenuBar():
            if BeginMenu("File"):
                if MenuItem("Select Renderer"):
                    self.getRoot().queueEndRendering()
                    self.restart = True
                if MenuItem("Quit", "Esc"):
                    self.getRoot().queueEndRendering()
                EndMenu()
            if BeginMenu("View"):
                enode = self.entity.getParentSceneNode()
                if MenuItem("Show Axes", "A", self.axes.getVisible()):
                    self._toggle_axes()
                if MenuItem("Show Bounding Box", "B", enode.getShowBoundingBox()):
                    self._toggle_bbox()
                if self.entity.hasSkeleton() and MenuItem("Show Skeleton", None, self.entity.getDisplaySkeleton()):
                    self.entity.setDisplaySkeleton(not self.entity.getDisplaySkeleton())
                EndMenu()

            if BeginMenu("Help"):
                if MenuItem("Metrics", None, self.show_metrics):
                    self.show_metrics = not self.show_metrics
                if MenuItem("About"):
                    self.show_about = True
                EndMenu()

            EndMainMenuBar()

        if self.show_about:
            self.draw_about()

        if self.show_metrics:
            self.draw_metrics()

        # Mesh Info Sidebar
        mesh = Ogre.MeshManager.getSingleton().getByName(self.meshname)

        SetNextWindowPos(ImVec2(0, 30))
        flags = ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoMove
        Begin("MeshProps", None, flags)
        Text(self.meshname)

        highlight = -1

        if CollapsingHeader("Geometry"):
            if mesh.sharedVertexData:
                Text("Shared Vertices: {}".format(mesh.sharedVertexData.vertexCount))
            else:
                Text("Shared Vertices: None")

            for i, sm in enumerate(mesh.getSubMeshes()):
                submesh_details = TreeNode("SubMesh #{}".format(i))
                if IsItemHovered():
                    highlight = i

                if submesh_details:
                    BulletText("Material: {}".format(sm.getMaterialName()))
                    if sm.indexData:
                        bits = sm.indexData.indexBuffer.getIndexSize() * 8
                        BulletText("Indices: {} ({} bit)".format(sm.indexData.indexCount, bits))
                    else:
                        BulletText("Indices: None")

                    if sm.vertexData:
                        BulletText("Vertices: {}".format(sm.vertexData.vertexCount))
                    else:
                        BulletText("Vertices: shared")
                    TreePop()

        if self.highlighted > -1:
            self.entity.getSubEntities()[self.highlighted].setMaterialName(self.orig_mat)

        if highlight > -1:
            self.orig_mat = self.entity.getSubEntities()[highlight].getMaterial().getName()
            self.entity.getSubEntities()[highlight].setMaterial(self.highlight_mat)
            self.highlighted = highlight

        animations = self.entity.getAllAnimationStates()
        if animations is not None and CollapsingHeader("Animations"):
            controller_mgr = Ogre.ControllerManager.getSingleton()

            if self.entity.hasSkeleton():
                Text("Skeleton: {}".format(mesh.getSkeletonName()))
                # self.entity.setUpdateBoundingBoxFromSkeleton(True)
            if mesh.hasVertexAnimation():
                Text("Vertex Animations")

            for name, astate in animations.getAnimationStates().items():
                if TreeNode(name):
                    if astate.getEnabled():
                        if Button("Reset"):
                            astate.setEnabled(False)
                            astate.setTimePosition(0)
                            if name in self.active_controllers:
                                controller_mgr.destroyController(self.active_controllers[name])
                    elif Button("Play"):
                        astate.setEnabled(True)
                        self.active_controllers[name] = controller_mgr.createFrameTimePassthroughController(
                            Ogre.AnimationStateControllerValue.create(astate, True))
                    changed = False
                    if astate.getLength() > 0:
                        SameLine()
                        changed, value = SliderFloat("", astate.getTimePosition(), 0, astate.getLength(), "%.3fs")
                    if changed:
                        astate.setEnabled(True)
                        astate.setTimePosition(value)
                    TreePop()

        if CollapsingHeader("Bounds"):
            bounds = mesh.getBounds()
            s = bounds.getSize()
            BulletText("Size: {:.2f}, {:.2f}, {:.2f}".format(s[0], s[1], s[2]))
            c = bounds.getCenter()
            BulletText("Center: {:.2f}, {:.2f}, {:.2f}".format(c[0], c[1], c[2]))
            BulletText("Radius: {:.2f}".format(mesh.getBoundingSphereRadius()))

        End()

        # ShowDemoWindow()

        return True

    def locateResources(self):
        rgm = Ogre.ResourceGroupManager.getSingleton()
        # ensure our resource group is separate, even with a local resources.cfg
        rgm.createResourceGroup(RGN_MESHVIEWER, False)

        # use parent implementation to locate system-wide RTShaderLib
        OgreBites.ApplicationContext.locateResources(self)

        # allow override by local resources.cfg
        if not self.getFSLayer().fileExists("resources.cfg"):
            # we use the fonts from SdkTrays.zip
            trays_loc = self.getDefaultMediaDir()+"/packs/SdkTrays.zip"
            rgm.addResourceLocation(trays_loc, "Zip", RGN_MESHVIEWER)

        if self.rescfg:
            cfg = Ogre.ConfigFile()
            cfg.loadDirect(self.rescfg)

            for sec, settings in cfg.getSettingsBySection().items():
                for kind, loc in settings.items():
                    rgm.addResourceLocation(loc, kind, sec)

        # explicitly add mesh location to be safe
        if not rgm.resourceLocationExists(self.meshdir, Ogre.RGN_DEFAULT):
            rgm.addResourceLocation(self.meshdir, "FileSystem", Ogre.RGN_DEFAULT)

    def setup(self):
        OgreBites.ApplicationContext.setup(self)
        self.addInputListener(self)

        self.restart = False
        self.imgui_mgr = ImguiManager()
        GetIO().IniFilename = self.getFSLayer().getWritablePath("imgui.ini")

        root = self.getRoot()
        scn_mgr = root.createSceneManager()
        self.scn_mgr = scn_mgr

        # for picking
        self.ray_query = scn_mgr.createRayQuery(Ogre.Ray())

        self.imgui_mgr.addFont("SdkTrays/Value", RGN_MESHVIEWER)
        self.imgui_mgr.init(scn_mgr)

        shadergen = OgreRTShader.ShaderGenerator.getSingleton()
        shadergen.addSceneManager(scn_mgr)  # must be done before we do anything with the scene

        scn_mgr.setAmbientLight(Ogre.ColourValue(.1, .1, .1))

        self.highlight_mat = Ogre.MaterialManager.getSingleton().create("Highlight", RGN_MESHVIEWER)
        self.highlight_mat.getTechniques()[0].getPasses()[0].setEmissive(Ogre.ColourValue(1, 1, 0))

        self.entity = scn_mgr.createEntity(self.meshname)
        scn_mgr.getRootSceneNode().createChildSceneNode().attachObject(self.entity)

        diam = self.entity.getBoundingBox().getSize().length()

        axes_node = scn_mgr.getRootSceneNode().createChildSceneNode()
        axes_node.getDebugRenderable()  # make sure Ogre/Debug/AxesMesh is created
        self.axes = scn_mgr.createEntity("Ogre/Debug/AxesMesh")
        axes_node.attachObject(self.axes)
        axes_node.setScale(Ogre.Vector3(diam / 4))
        self.axes.setVisible(False)
        self.axes.setQueryFlags(0) # exclude from picking

        self.cam = scn_mgr.createCamera("myCam")
        self.cam.setNearClipDistance(diam * 0.01)
        self.cam.setAutoAspectRatio(True)
        camnode = scn_mgr.getRootSceneNode().createChildSceneNode()
        camnode.attachObject(self.cam)

        light = scn_mgr.createLight("MainLight")
        light.setType(Ogre.Light.LT_DIRECTIONAL)
        camnode.attachObject(light)

        vp = self.getRenderWindow().addViewport(self.cam)
        vp.setBackgroundColour(Ogre.ColourValue(.3, .3, .3))

        self.camman = OgreBites.CameraMan(camnode)
        self.camman.setStyle(OgreBites.CS_ORBIT)
        self.camman.setYawPitchDist(Ogre.Radian(0), Ogre.Radian(0.3), diam)
        self.camman.setFixedYaw(False)

        self.input_dispatcher = InputDispatcher(self.camman)
        self.addInputListener(self.input_dispatcher)
    
    def shutdown(self):
        OgreBites.ApplicationContext.shutdown(self)
        self.imgui_mgr = None
        
        if self.restart:
            # make sure empty rendersystem is written
            self.getRoot().shutdown()
            self.getRoot().setRenderSystem(None)

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ogre Mesh Viewer")
    parser.add_argument("meshfile", help="path to a .mesh")
    parser.add_argument("-c", "--rescfg", help="path to the resources.cfg")
    args = parser.parse_args() 
    app = MeshViewer(args.meshfile, args.rescfg)

    while True: # allow auto restart
        app.initApp()
        app.getRoot().startRendering()
        app.closeApp()

        if not app.restart: break
