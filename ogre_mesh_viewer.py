import Ogre
import OgreRTShader
import OgreOverlay
import OgreBites
import OgreImgui
from OgreImgui import *

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

    def __init__(self, meshname):
        OgreBites.ApplicationContext.__init__(self, "OgreMeshViewer", False)
        OgreBites.InputListener.__init__(self)

        self.show_about = False
        self.show_metrics = False
        self.mesh = meshname
        self.highlighted = -1
        self.orig_mat = None
        self.highlight_mat = None

        self.animation_states = []

    def keyPressed(self, evt):
        if evt.keysym.sym == OgreBites.SDLK_ESCAPE:
            self.getRoot().queueEndRendering()

        return True

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

        for a in self.animation_states:
            a.addTime(evt.timeSinceLastFrame)

        ImguiManager.getSingleton().newFrame(
            evt.timeSinceLastFrame,
            Ogre.Rect(0, 0, self.getRenderWindow().getWidth(), self.getRenderWindow().getHeight()))

        if BeginMainMenuBar():
            if BeginMenu("File"):
                if MenuItem("Quit", "Esc"):
                    self.getRoot().queueEndRendering()
                EndMenu()
            if BeginMenu("View"):
                if MenuItem("Show Bounding Box", None, self.scn_mgr.getShowBoundingBoxes()):
                    self.scn_mgr.showBoundingBoxes(not self.scn_mgr.getShowBoundingBoxes())
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
        mesh = Ogre.MeshManager.getSingleton().getByName(self.mesh)

        SetNextWindowPos(ImVec2(0, 30))
        flags = ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoMove
        Begin("MeshProps", None, flags)
        Text(self.mesh)

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

        if mesh.hasSkeleton() and CollapsingHeader("Skeleton"):
            Text(mesh.getSkeletonName())
            skel = mesh.getSkeleton()

            # self.entity.setUpdateBoundingBoxFromSkeleton(True)

            for i in range(skel.getNumAnimations()):
                name = skel.getAnimation(i).getName()
                if TreeNode(name):
                    astate = self.entity.getAnimationState(name)
                    if astate.getEnabled():
                        if Button("Reset"):
                            astate.setEnabled(False)
                            astate.setTimePosition(0)
                            if astate in self.animation_states:
                                self.animation_states.remove(astate)
                    elif Button("Play"):
                        astate.setEnabled(True)
                        self.animation_states.append(astate)
                    SameLine()
                    changed, value = SliderFloat("", astate.getTimePosition(), 0, astate.getLength())
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

    def setup(self):
        OgreBites.ApplicationContext.setup(self)
        self.addInputListener(self)

        ImguiManager.createSingleton()
        GetIO().IniFilename = self.getFSLayer().getWritablePath("imgui.ini")

        root = self.getRoot()
        scn_mgr = root.createSceneManager()
        self.scn_mgr = scn_mgr

        ImguiManager.getSingleton().addFont("SdkTrays/Value", "Essential")
        ImguiManager.getSingleton().init(scn_mgr)

        shadergen = OgreRTShader.ShaderGenerator.getSingleton()
        shadergen.addSceneManager(scn_mgr)  # must be done before we do anything with the scene

        scn_mgr.setAmbientLight(Ogre.ColourValue(.1, .1, .1))

        cam = scn_mgr.createCamera("myCam")
        cam.setNearClipDistance(5)
        cam.setAutoAspectRatio(True)
        camnode = scn_mgr.getRootSceneNode().createChildSceneNode()
        camnode.attachObject(cam)

        self.highlight_mat = Ogre.MaterialManager.getSingleton().create("Viewer/Highlight", "General")
        self.highlight_mat.getTechniques()[0].getPasses()[0].setEmissive(Ogre.ColourValue(1, 1, 0))

        vp = self.getRenderWindow().addViewport(cam)
        vp.setBackgroundColour(Ogre.ColourValue(.3, .3, .3))

        self.entity = scn_mgr.createEntity(self.mesh)

        diam = self.entity.getBoundingBox().getSize().length()

        node = scn_mgr.getRootSceneNode().createChildSceneNode()
        node.attachObject(self.entity)

        camman = OgreBites.CameraMan(camnode)
        camman.setStyle(OgreBites.CS_ORBIT)
        camman.setYawPitchDist(Ogre.Radian(0), Ogre.Radian(0.3), diam)

        light = scn_mgr.createLight("MainLight")
        lightnode = scn_mgr.getRootSceneNode().createChildSceneNode()
        lightnode.setPosition(Ogre.Vector3(0, 1, 1.5) * diam)
        lightnode.attachObject(light)

        self.input_dispatcher = InputDispatcher(camman)
        self.addInputListener(self.input_dispatcher)

if __name__ == "__main__":
    import sys
    app = MeshViewer(sys.argv[1])
    app.initApp()
    app.getRoot().startRendering()
    app.closeApp()
