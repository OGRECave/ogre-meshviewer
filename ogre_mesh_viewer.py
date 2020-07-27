import Ogre
import Ogre.RTShader as OgreRTShader
import Ogre.Bites as OgreBites

from Ogre.Overlay import *

import os.path

RGN_MESHVIEWER = "OgreMeshViewer"

VES2STR = ("ERROR", "Position", "Blend Weights", "Blend Indices", "Normal", "Diffuse", "Specular", "Texcoord", "Binormal", "Tangent")
VET2STR = ("float", "float2", "float3", "float4", "ERROR",
           "short", "short2", "short3", "short4", "ubyte4", "argb", "abgr",
           "double", "double2", "double3", "double4",
           "ushort", "ushort2", "ushort3", "ushort4",
           "int", "int2", "int3", "int4",
           "uint", "uint2", "uint3", "uint4",
           "byte4", "byte4n", "ubyte4n", "short2n", "short4n", "ushort2n", "ushort4n")


def show_vertex_decl(decl):
    Columns(2)
    Text("Semantic")
    NextColumn()
    Text("Type")
    NextColumn()
    Separator()

    for e in decl.getElements():
        Text(VES2STR[e.getSemantic()])
        NextColumn()
        Text(VET2STR[e.getType()])
        NextColumn()
    Columns(1)


class MaterialCreator(Ogre.MeshSerializerListener):

    def __init__(self):
        Ogre.MeshSerializerListener.__init__(self)

    def processMaterialName(self, mesh, name):
        # ensure some material exists so we can display the name
        mat_mgr = Ogre.MaterialManager.getSingleton()
        if not mat_mgr.resourceExists(name, mesh.getGroup()):
            try:
                mat_mgr.create(name, mesh.getGroup())
            except RuntimeError:
                # do not crash if name is ""
                # this is illegal due to OGRE specs, but we want to show that in the UI
                pass

    def processSkeletonName(self, mesh, name): pass

    def processMeshCompleted(self, mesh): pass

class LogWindow(Ogre.LogListener):
    def __init__(self):
        Ogre.LogListener.__init__(self)

        self.show = False
        self.items = []

        self.font = None
    
    def messageLogged(self, msg, lvl, *args):
        self.items.append((msg, lvl))

    def draw(self):
        if not self.show:
            return

        SetNextWindowSize(ImVec2(500, 400), ImGuiCond_FirstUseEver)
        self.show = Begin("Log", self.show)[1]

        PushFont(self.font)
        for msg, lvl in self.items:
            if lvl == 4:
                PushStyleColor(ImGuiCol_Text, ImVec4(1, 0.4, 0.4, 1))
            elif lvl == 3:
                PushStyleColor(ImGuiCol_Text, ImVec4(1, 0.8, 0.4, 1))
            TextWrapped(msg)
            if lvl > 2:
                PopStyleColor()
        PopFont()
        End()

class MeshViewerGui(Ogre.RenderTargetListener):

    def __init__(self, app):
        Ogre.RenderTargetListener.__init__(self)
        self.show_about = False
        self.show_metrics = False

        self.app = app
        self.entity = app.entity

        self.highlighted = -1
        self.orig_mat = None
        self.logwin = app.logwin

    def draw_about(self):
        flags = ImGuiWindowFlags_AlwaysAutoResize
        self.show_about = Begin("About OgreMeshViewer", self.show_about, flags)[1]
        Text("By Pavel Rojtberg")
        Text("OgreMeshViewer is licensed under the MIT License, see LICENSE for more information.")
        Separator()
        BulletText("Ogre:  %s" % Ogre.__version__)
        BulletText("imgui: %s" % GetVersion())
        End()

    def draw_metrics(self):
        win = self.app.getRenderWindow()
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

    def preRenderTargetUpdate(self, evt):
        if not self.app.cam.getViewport().getOverlaysEnabled():
            return

        ImGuiOverlay.NewFrame()

        if BeginMainMenuBar():
            if BeginMenu("File"):
                if MenuItem("Select Renderer"):
                    self.app.getRoot().queueEndRendering()
                    self.app.restart = True
                if MenuItem("Save Screenshot", "P"):
                    self.app._save_screenshot()
                if MenuItem("Quit", "Esc"):
                    self.app.getRoot().queueEndRendering()
                EndMenu()
            if BeginMenu("View"):
                enode = self.entity.getParentSceneNode()
                if MenuItem("Show Axes", "A", self.app.axes.getVisible()):
                    self.app._toggle_axes()
                if MenuItem("Show Bounding Box", "B", enode.getShowBoundingBox()):
                    self.app._toggle_bbox()
                if self.entity.hasSkeleton() and MenuItem("Show Skeleton", None, self.entity.getDisplaySkeleton()):
                    self.entity.setDisplaySkeleton(not self.entity.getDisplaySkeleton())
                EndMenu()

            if BeginMenu("Help"):
                if MenuItem("Metrics", None, self.show_metrics):
                    self.show_metrics = not self.show_metrics
                if MenuItem("Log"):
                    self.logwin.show = True
                if MenuItem("About"):
                    self.show_about = True
                EndMenu()

            EndMainMenuBar()

        if self.show_about:
            self.draw_about()

        if self.show_metrics:
            self.draw_metrics()

        # Mesh Info Sidebar
        mesh = self.entity.getMesh()

        SetNextWindowSize(ImVec2(300, 500), ImGuiCond_FirstUseEver)
        SetNextWindowPos(ImVec2(0, 30))
        flags = ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoMove
        Begin("MeshProps", None, flags)
        Text(mesh.getName())

        highlight = -1

        if CollapsingHeader("Geometry"):
            if mesh.sharedVertexData:
                if TreeNode("Shared Vertices: {}".format(mesh.sharedVertexData.vertexCount)):
                    show_vertex_decl(mesh.sharedVertexData.vertexDeclaration)
                    TreePop()
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
                        if TreeNode("Vertices: {}".format(sm.vertexData.vertexCount)):
                            show_vertex_decl(sm.vertexData.vertexDeclaration)
                            TreePop()
                    else:
                        BulletText("Vertices: shared")
                    TreePop()

        if self.highlighted > -1:
            self.entity.getSubEntities()[self.highlighted].setMaterialName(self.orig_mat)

        if highlight > -1:
            self.orig_mat = self.entity.getSubEntities()[highlight].getMaterial().getName()
            self.entity.getSubEntities()[highlight].setMaterial(self.app.highlight_mat)
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
                            if name in self.app.active_controllers:
                                controller_mgr.destroyController(self.app.active_controllers[name])
                    elif Button("Play"):
                        astate.setEnabled(True)
                        self.app.active_controllers[name] = controller_mgr.createFrameTimePassthroughController(
                            Ogre.AnimationStateControllerValue.create(astate, True))
                    changed = False
                    if astate.getLength() > 0:
                        SameLine()
                        changed, value = SliderFloat("", astate.getTimePosition(), 0, astate.getLength(), "%.3fs")
                    if changed:
                        astate.setEnabled(True)
                        astate.setTimePosition(value)
                    TreePop()

        lod_count = mesh.getNumLodLevels()
        if lod_count > 1 and CollapsingHeader("LOD levels"):
            self.entity.setMeshLodBias(1)  # reset LOD override
            strategy = mesh.getLodStrategy().getName()
            curr_idx = self.entity.getCurrentLodIndex()
            Text("Strategy: {}".format(strategy))
            for i in range(lod_count):
                txt = "Base Mesh" if i == 0 else "Level {}: {:.2f}".format(i, mesh.getLodLevel(i).userValue)
                Bullet()
                Selectable(txt, i == curr_idx)
                if IsItemHovered():
                    # force this LOD level
                    self.entity.setMeshLodBias(1, i, i)

        if CollapsingHeader("Bounds"):
            bounds = mesh.getBounds()
            s = bounds.getSize()
            BulletText("Size: {:.2f}, {:.2f}, {:.2f}".format(s[0], s[1], s[2]))
            c = bounds.getCenter()
            BulletText("Center: {:.2f}, {:.2f}, {:.2f}".format(c[0], c[1], c[2]))
            BulletText("Radius: {:.2f}".format(mesh.getBoundingSphereRadius()))

        End()

        self.logwin.draw()

        # ShowDemoWindow()

class MeshViewer(OgreBites.ApplicationContext, OgreBites.InputListener):

    def __init__(self, meshname, rescfg):
        OgreBites.ApplicationContext.__init__(self, "OgreMeshViewer")
        OgreBites.InputListener.__init__(self)

        self.meshname = os.path.basename(meshname)
        self.meshdir = os.path.dirname(meshname)
        self.rescfg = rescfg

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
        elif evt.keysym.sym == ord("p"):
            self._save_screenshot()

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

    def _save_screenshot(self):
        name = os.path.splitext(self.meshname)[0]
        outpath = os.path.join(self.meshdir, "screenshot_{}_".format(name))

        self.cam.getViewport().setOverlaysEnabled(False)
        self.getRoot().renderOneFrame()
        self.getRenderWindow().writeContentsToTimestampedFile(outpath, ".png")
        self.cam.getViewport().setOverlaysEnabled(True)

    def locateResources(self):
        rgm = Ogre.ResourceGroupManager.getSingleton()
        # ensure our resource group is separate, even with a local resources.cfg
        rgm.createResourceGroup(RGN_MESHVIEWER, False)

        # use parent implementation to locate system-wide RTShaderLib
        OgreBites.ApplicationContext.locateResources(self)

        # allow override by local resources.cfg
        if not self.getFSLayer().fileExists("resources.cfg"):
            # we use the fonts from SdkTrays.zip
            trays_loc = self.getDefaultMediaDir() + "/packs/SdkTrays.zip"
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
        
    def loadResources(self):
        rgm = Ogre.ResourceGroupManager.getSingleton()
        rgm.initialiseResourceGroup(Ogre.RGN_INTERNAL)
        rgm.initialiseResourceGroup(RGN_MESHVIEWER)

        # only capture default group
        self.logwin = LogWindow()
        Ogre.LogManager.getSingleton().getDefaultLog().addListener(self.logwin)
        rgm.initialiseResourceGroup(Ogre.RGN_DEFAULT)

    def setup(self):
        OgreBites.ApplicationContext.setup(self)
        self.addInputListener(self)

        self.restart = False
        imgui_overlay = ImGuiOverlay()
        GetIO().IniFilename = self.getFSLayer().getWritablePath("imgui.ini")

        root = self.getRoot()
        scn_mgr = root.createSceneManager()
        scn_mgr.addRenderQueueListener(self.getOverlaySystem())
        self.scn_mgr = scn_mgr

        # set listener to deal with missing materials
        self.mat_creator = MaterialCreator()
        Ogre.MeshManager.getSingleton().setListener(self.mat_creator)

        # for picking
        self.ray_query = scn_mgr.createRayQuery(Ogre.Ray())

        imgui_overlay.addFont("SdkTrays/Value", RGN_MESHVIEWER)
        self.logwin.font = GetIO().Fonts.AddFontDefault()
        imgui_overlay.show()
        OverlayManager.getSingleton().addOverlay(imgui_overlay)
        imgui_overlay.disown()  # owned by OverlayMgr now

        shadergen = OgreRTShader.ShaderGenerator.getSingleton()
        shadergen.addSceneManager(scn_mgr)  # must be done before we do anything with the scene

        scn_mgr.setAmbientLight(Ogre.ColourValue(.1, .1, .1))

        self.highlight_mat = Ogre.MaterialManager.getSingleton().create("Highlight", RGN_MESHVIEWER)
        self.highlight_mat.getTechniques()[0].getPasses()[0].setEmissive(Ogre.ColourValue(1, 1, 0))

        self.entity = scn_mgr.createEntity(self.meshname)
        scn_mgr.getRootSceneNode().createChildSceneNode().attachObject(self.entity)

        self.gui = MeshViewerGui(self)
        self.getRenderWindow().addListener(self.gui)

        diam = self.entity.getBoundingBox().getSize().length()

        axes_node = scn_mgr.getRootSceneNode().createChildSceneNode()
        axes_node.getDebugRenderable()  # make sure Ogre/Debug/AxesMesh is created
        self.axes = scn_mgr.createEntity("Ogre/Debug/AxesMesh")
        axes_node.attachObject(self.axes)
        axes_node.setScale(Ogre.Vector3(diam / 4))
        self.axes.setVisible(False)
        self.axes.setQueryFlags(0)  # exclude from picking

        self.cam = scn_mgr.createCamera("myCam")
        self.cam.setNearClipDistance(diam * 0.01)
        self.cam.setAutoAspectRatio(True)
        camnode = scn_mgr.getRootSceneNode().createChildSceneNode()
        camnode.attachObject(self.cam)

        light = scn_mgr.createLight("MainLight")
        light.setType(Ogre.Light.LT_DIRECTIONAL)
        light.setSpecularColour(Ogre.ColourValue.White)
        camnode.attachObject(light)

        vp = self.getRenderWindow().addViewport(self.cam)
        vp.setBackgroundColour(Ogre.ColourValue(.3, .3, .3))

        self.camman = OgreBites.CameraMan(camnode)
        self.camman.setStyle(OgreBites.CS_ORBIT)
        self.camman.setYawPitchDist(Ogre.Radian(0), Ogre.Radian(0.3), diam)
        self.camman.setFixedYaw(False)

        self.imgui_input = OgreBites.ImGuiInputListener()
        self.input_dispatcher = OgreBites.InputListenerChain([self.imgui_input, self.camman])
        self.addInputListener(self.input_dispatcher)

    def shutdown(self):
        Ogre.LogManager.getSingleton().getDefaultLog().removeListener(self.logwin)
        OgreBites.ApplicationContext.shutdown(self)

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

    while True:  # allow auto restart
        app.initApp()
        app.getRoot().startRendering()
        app.closeApp()

        if not app.restart: break
