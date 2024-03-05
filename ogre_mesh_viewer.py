#!/usr/bin/env python

import os.path
import time

import tkinter as tk
from tkinter import filedialog

import Ogre
import Ogre.RTShader as OgreRTShader
import Ogre.Bites as OgreBites
import Ogre.Overlay

import Ogre.ImGui as ImGui

RGN_MESHVIEWER = "OgreMeshViewer"
RGN_USERDATA   = "UserData"

VES2STR = ("ERROR", "Position", "Blend Weights", "Blend Indices", "Normal", "Diffuse", "Specular", "Texcoord", "Binormal", "Tangent")
VET2STR = ("float", "float2", "float3", "float4", "ERROR",
           "short", "short2", "short3", "short4", "ubyte4", "argb", "abgr",
           "double", "double2", "double3", "double4",
           "ushort", "ushort2", "ushort3", "ushort4",
           "int", "int2", "int3", "int4",
           "uint", "uint2", "uint3", "uint4",
           "byte4", "byte4n", "ubyte4n", "short2n", "short4n", "ushort2n", "ushort4n", "int1010102n")

ROP2STR = ("ERROR", "Point List", "Line List", "Line Strip", "Triangle List", "Triangle Strip", "Triangle Fan")

def show_vertex_decl(decl):
    flags = ImGui.TableFlags_Borders | ImGui.TableFlags_SizingStretchProp
    if not ImGui.BeginTable("vertexDecl", 3, flags):
        return
    ImGui.TableSetupColumn("Semantic")
    ImGui.TableSetupColumn("Type")
    ImGui.TableSetupColumn("Buffer")
    ImGui.TableHeadersRow()

    for e in decl.getElements():
        ImGui.TableNextRow()
        ImGui.TableNextColumn()
        ImGui.Text(VES2STR[e.getSemantic()])
        ImGui.TableNextColumn()
        ImGui.Text(VET2STR[e.getType()])
        ImGui.TableNextColumn()
        ImGui.Text(str(e.getSource()))
    ImGui.EndTable()

def printable(str):
    return str.encode("utf-8", "replace").decode()

def askopenfilename(initialdir=None):
    infile = filedialog.askopenfilename(
        title="Select Mesh File",
        initialdir=initialdir,
        filetypes=[("All files", "*"),
                   ("Ogre files", "*.mesh *.scene"),
                   ("Common mesh files", "*.obj *.fbx *.ply *.gltf *.glb ")])
    return infile

class MaterialCreator(Ogre.MeshSerializerListener):

    def __init__(self):
        Ogre.MeshSerializerListener.__init__(self)

    def processMaterialName(self, mesh, name):
        # ensure some material exists so we can display the name
        mat_mgr = Ogre.MaterialManager.getSingleton()
        if not mat_mgr.resourceExists(name, mesh.getGroup()):
            lmgr = Ogre.LogManager.getSingleton()
            try:
                mat = mat_mgr.create(name, mesh.getGroup())
                lmgr.logWarning(f"could not find material '{printable(mat.getName())}'")
            except RuntimeError:
                # do not crash if name is ""
                # this is illegal due to OGRE specs, but we want to show that in the UI
                lmgr.logError("sub-mesh uses empty material name")

    def processSkeletonName(self, mesh, name): pass

    def processMeshCompleted(self, mesh): pass

class LogWindow(Ogre.LogListener):
    def __init__(self):
        Ogre.LogListener.__init__(self)

        self.show = False
        self.items = []

        self.font = None
    
    def messageLogged(self, msg, lvl, *args):
        ts = time.strftime("%T", time.localtime())
        self.items.append((ts, printable(msg.replace("%", "%%")), lvl))

    def draw(self):
        if not self.show:
            return

        ImGui.SetNextWindowSize(ImGui.ImVec2(500, 400), ImGui.Cond_FirstUseEver)
        self.show = ImGui.Begin("Log", self.show)[1]

        ImGui.PushFont(self.font)
        for ts, msg, lvl in self.items:
            ImGui.PushStyleColor(ImGui.Col_Text, ImGui.ImVec4(0.6, 0.6, 0.6, 1))
            ImGui.Text(ts)
            ImGui.PopStyleColor()
            ImGui.SameLine()
            if lvl == 4:
                ImGui.PushStyleColor(ImGui.Col_Text, ImGui.ImVec4(1, 0.4, 0.4, 1))
            elif lvl == 3:
                ImGui.PushStyleColor(ImGui.Col_Text, ImGui.ImVec4(1, 0.8, 0.4, 1))
            ImGui.TextWrapped(msg)
            if lvl > 2:
                ImGui.PopStyleColor()
        ImGui.PopFont()
        ImGui.End()

class MeshViewerGui(Ogre.RenderTargetListener):

    def __init__(self, app):
        Ogre.RenderTargetListener.__init__(self)
        self.show_about = False
        self.show_metrics = False
        self.show_render_settings = False
        self.side_panel_visible = True

        self.app = app

        self.highlighted = -1
        self.orig_mat = None
        self.logwin = app.logwin

        self.lod_idx_override = -1

    def draw_about(self):
        flags = ImGui.WindowFlags_AlwaysAutoResize
        self.show_about = ImGui.Begin("About OgreMeshViewer", self.show_about, flags)[1]
        ImGui.Text("By Pavel Rojtberg")
        ImGui.Text("OgreMeshViewer is licensed under the MIT License.")
        ImGui.Text("See LICENSE for more information.")
        ImGui.Separator()
        ImGui.BulletText(f"Ogre:  {Ogre.__version__}")
        ImGui.BulletText(f"ImGui: {ImGui.GetVersion()}")
        ImGui.End()

    def draw_render_settings(self):
        flags = ImGui.WindowFlags_AlwaysAutoResize
        self.show_render_settings = ImGui.Begin("Renderer Settings", self.show_render_settings, flags)[1]

        app.next_rendersystem = Ogre.Overlay.DrawRenderingSettings(app.next_rendersystem)

        ImGui.Separator()

        if ImGui.Button("Apply & Restart"):
            app.restart = True
            app.getRoot().queueEndRendering()

        ImGui.End()

    def draw_metrics(self):
        win = self.app.getRenderWindow()
        stats = win.getStatistics()

        ImGui.SetNextWindowPos(ImGui.ImVec2(win.getWidth() - 10, win.getHeight() - 10), ImGui.Cond_Always, ImGui.ImVec2(1, 1))
        ImGui.SetNextWindowBgAlpha(0.3)
        flags = ImGui.WindowFlags_NoMove | ImGui.WindowFlags_NoTitleBar | ImGui.WindowFlags_NoResize | \
                ImGui.WindowFlags_AlwaysAutoResize | ImGui.WindowFlags_NoSavedSettings | ImGui.WindowFlags_NoFocusOnAppearing | \
                ImGui.WindowFlags_NoNav
        self.show_metrics = ImGui.Begin("Metrics", self.show_metrics, flags)[1]
        ImGui.Text("Metrics")
        ImGui.Separator()
        ImGui.Text(f"Average FPS: {stats.avgFPS:.2f}")
        ImGui.Text(f"Batches: {stats.batchCount}")
        ImGui.Text(f"Triangles: {stats.triangleCount}")
        ImGui.End()

    def draw_loading(self):
        win = self.app.getRenderWindow()
        ImGui.SetNextWindowPos(ImGui.ImVec2(win.getWidth() * 0.5, win.getHeight() * 0.5), 0, ImGui.ImVec2(0.5, 0.5))

        flags = ImGui.WindowFlags_NoTitleBar | ImGui.WindowFlags_NoResize | ImGui.WindowFlags_NoSavedSettings
        ImGui.Begin("Loading", True, flags)
        ImGui.Text(self.app.filename)
        ImGui.Separator()
        ImGui.Text("Loading..            ")
        ImGui.End()

    def preRenderTargetUpdate(self, evt):
        if not self.app.cam.getViewport().getOverlaysEnabled():
            return

        Ogre.Overlay.ImGuiOverlay.NewFrame()

        entity = self.app.entity

        if entity is None and self.app.attach_node is None:
            self.draw_loading()
            return

        if ImGui.BeginMainMenuBar():

            if ImGui.BeginMenu("File"):
                if ImGui.MenuItem("Open File"):
                    app.infile = askopenfilename(app.filedir)
                    if app.infile:
                        app.restart = True
                        app.getRoot().queueEndRendering()
                if ImGui.MenuItem("Renderer Settings"):
                    self.show_render_settings = True
                if ImGui.MenuItem("Save Screenshot", "P"):
                    self.app._save_screenshot()
                if ImGui.MenuItem("Quit", "Esc"):
                    self.app.getRoot().queueEndRendering()
                ImGui.EndMenu()

            if entity is not None and ImGui.BeginMenu("View"):
                enode = entity.getParentSceneNode()
                if ImGui.MenuItem("Side Panel", "N", self.side_panel_visible):
                    self.side_panel_visible = not self.side_panel_visible
                ImGui.Separator()
                if ImGui.MenuItem("Show Axes", "A", self.app.axes_visible):
                    self.app._toggle_axes()
                if ImGui.MenuItem("Show Bounding Box", "B", enode.getShowBoundingBox()):
                    self.app._toggle_bbox()
                if ImGui.MenuItem("Wireframe Mode", "W", app.cam.getPolygonMode() == Ogre.PM_WIREFRAME):
                    self.app._toggle_wireframe_mode()

                if entity.hasSkeleton() and ImGui.MenuItem("Show Skeleton", None, entity.getDisplaySkeleton()):
                    entity.setDisplaySkeleton(not entity.getDisplaySkeleton())
                ImGui.EndMenu()

            if ImGui.BeginMenu("Help"):
                if ImGui.MenuItem("Metrics", None, self.show_metrics):
                    self.show_metrics = not self.show_metrics
                if ImGui.MenuItem("Log"):
                    self.logwin.show = True
                if ImGui.MenuItem("About"):
                    self.show_about = True
                ImGui.EndMenu()

            ImGui.EndMainMenuBar()

        if self.show_about:
            self.draw_about()

        if self.show_metrics:
            self.draw_metrics()

        if self.show_render_settings:
            self.draw_render_settings()

        self.logwin.draw()

        if entity is None:
            # no sidebar yet when loading .scene
            return

        if self.side_panel_visible is False:
            # hide side panel
            return

        # Mesh Info Sidebar
        mesh = entity.getMesh()

        ImGui.SetNextWindowSize(ImGui.ImVec2(300, ImGui.GetFontSize()*25), ImGui.Cond_FirstUseEver)
        ImGui.SetNextWindowPos(ImGui.ImVec2(0, ImGui.GetFontSize()*1.5))
        flags = ImGui.WindowFlags_NoTitleBar | ImGui.WindowFlags_NoMove
        ImGui.Begin("MeshProps", None, flags)
        ImGui.Text(mesh.getName())

        highlight = -1

        if ImGui.CollapsingHeader("Geometry"):
            if mesh.sharedVertexData:
                if ImGui.TreeNode(f"Shared Vertices: {mesh.sharedVertexData.vertexCount}"):
                    show_vertex_decl(mesh.sharedVertexData.vertexDeclaration)
                    ImGui.TreePop()
            else:
                ImGui.Text("Shared Vertices: None")

            for i, sm in enumerate(mesh.getSubMeshes()):
                submesh_details = ImGui.TreeNode(f"SubMesh #{i}")
                if ImGui.IsItemHovered():
                    highlight = i

                if submesh_details:
                    ImGui.BulletText(f"Material: {printable(sm.getMaterialName())}")
                    op = ROP2STR[sm.operationType] if sm.operationType <= 6 else "Control Points"
                    ImGui.BulletText(f"Operation: {op}")

                    if sm.indexData.indexCount:
                        bits = sm.indexData.indexBuffer.getIndexSize() * 8
                        ImGui.BulletText(f"Indices: {sm.indexData.indexCount} ({bits} bit)")
                    else:
                        ImGui.BulletText("Indices: None")

                    if sm.vertexData:
                        if ImGui.TreeNode(f"Vertices: {sm.vertexData.vertexCount}"):
                            show_vertex_decl(sm.vertexData.vertexDeclaration)
                            ImGui.TreePop()
                    else:
                        ImGui.BulletText("Vertices: shared")
                    ImGui.TreePop()

        if self.highlighted > -1:
            entity.getSubEntities()[self.highlighted].setMaterialName(self.orig_mat)
            self.highlighted = -1

        if highlight > -1:
            self.orig_mat = printable(entity.getSubEntities()[highlight].getMaterial().getName())
            entity.getSubEntities()[highlight].setMaterial(self.app.highlight_mat)
            self.highlighted = highlight

        animations = entity.getAllAnimationStates()
        if animations is not None and ImGui.CollapsingHeader("Animations"):
            controller_mgr = Ogre.ControllerManager.getSingleton()

            if entity.hasSkeleton():
                ImGui.Text(f"Skeleton: {mesh.getSkeletonName()}")
                # self.entity.setUpdateBoundingBoxFromSkeleton(True)
            if mesh.hasVertexAnimation():
                ImGui.Text("Vertex Animations")

            for name, astate in animations.getAnimationStates().items():
                if ImGui.TreeNode(name):
                    ImGui.PushID(name)
                    if astate.getEnabled():
                        if ImGui.Button("Reset"):
                            astate.setEnabled(False)
                            astate.setTimePosition(0)
                            if name in self.app.active_controllers:
                                controller_mgr.destroyController(self.app.active_controllers[name])
                    elif ImGui.Button("Play"):
                        astate.setEnabled(True)
                        self.app.active_controllers[name] = controller_mgr.createFrameTimePassthroughController(
                            Ogre.AnimationStateControllerValue.create(astate, True))
                    changed = False
                    if astate.getLength() > 0:
                        ImGui.SameLine()
                        changed, value = ImGui.SliderFloat("", astate.getTimePosition(), 0, astate.getLength(), "%.3fs")
                    if changed:
                        astate.setEnabled(True)
                        astate.setTimePosition(value)
                    ImGui.PopID()
                    ImGui.TreePop()

        lod_count = mesh.getNumLodLevels()
        if lod_count > 1 and ImGui.CollapsingHeader("LOD levels"):
            if self.lod_idx_override > -1:
                entity.setMeshLodBias(1, self.lod_idx_override, self.lod_idx_override)
            else:
                entity.setMeshLodBias(1)  # reset LOD override
            strategy = mesh.getLodStrategy().getName()
            curr_idx = entity.getCurrentLodIndex()
            ImGui.AlignTextToFramePadding()
            ImGui.Text(f"Strategy: {strategy}")
            ImGui.SameLine()
            
            if ImGui.Checkbox("active", self.lod_idx_override == -1)[1]:
                self.lod_idx_override = -1
            elif self.lod_idx_override == -1:
                self.lod_idx_override = curr_idx
            
            for i in range(lod_count):
                txt = "Base Mesh" if i == 0 else f"Level {i}: {mesh.getLodLevel(i).userValue:.2f}"
                ImGui.Bullet()
                if ImGui.Selectable(txt, i == curr_idx):
                    self.lod_idx_override = i

                if ImGui.IsItemHovered():
                    # force this LOD level
                    entity.setMeshLodBias(1, i, i)

        if ImGui.CollapsingHeader("Bounds"):
            bounds = mesh.getBounds()
            s = bounds.getSize()
            ImGui.BulletText(f"Size: {s[0]:.2f}, {s[1]:.2f}, {s[2]:.2f}")
            c = bounds.getCenter()
            ImGui.BulletText(f"Center: {c[0]:.2f}, {c[1]:.2f}, {c[2]:.2f}")
            ImGui.BulletText(f"Radius: {mesh.getBoundingSphereRadius():.2f}")

        if ImGui.CollapsingHeader("Transform"):
            flags = ImGui.TableFlags_Borders | ImGui.TableFlags_SizingStretchProp

            enode = entity.getParentSceneNode()

            p = [
                round(enode.getPosition().x, 2),
                round(enode.getPosition().y, 2),
                round(enode.getPosition().z, 2)
            ]
            ImGui.BulletText(f"Position: {p[0]:.2f}, {p[1]:.2f}, {p[2]:.2f}")

            o = [
                round(enode.getOrientation().getYaw().valueDegrees(), 2),
                round(enode.getOrientation().getPitch().valueDegrees(), 2),
                round(enode.getOrientation().getRoll().valueDegrees(), 2)
            ]
            ImGui.BulletText(f"Orientation: {o[0]:.2f}, {o[1]:.2f}, {o[2]:.2f}")

            s = [
                round(enode.getScale().x, 2),
                round(enode.getScale().y, 2),
                round(enode.getScale().z, 2)
            ]
            ImGui.BulletText(f"Scale: {s[0]:.2f}, {s[1]:.2f}, {s[2]:.2f}")

        ImGui.End()

class MeshViewer(OgreBites.ApplicationContext, OgreBites.InputListener):

    def __init__(self, infile, rescfg):
        OgreBites.ApplicationContext.__init__(self, "OgreMeshViewer")
        OgreBites.InputListener.__init__(self)

        self.infile = infile
        if not self.infile:
            self.infile = askopenfilename()
        if not self.infile:
            raise SystemExit("No file selected")

        self.filename = None
        self.filedir = None
        self.rescfg = rescfg

        self.entity = None
        self.attach_node = None
        self.highlight_mat = None
        self.restart = False
        self.axes_visible = False

        self.active_controllers = {}

        self.next_rendersystem = ""

        # in case we want to show the file dialog
        root = tk.Tk()
        root.withdraw()

    def keyPressed(self, evt):
        if evt.keysym.sym == OgreBites.SDLK_ESCAPE:
            self.getRoot().queueEndRendering()
        elif evt.keysym.sym == ord("b"):
            self._toggle_bbox()
        elif evt.keysym.sym == ord("n"):
            self.gui.side_panel_visible = not self.gui.side_panel_visible
        elif evt.keysym.sym == ord("a"):
            self._toggle_axes()
        elif evt.keysym.sym == ord("p"):
            self._save_screenshot()
        elif evt.keysym.sym == ord("w"):
            self._toggle_wireframe_mode()

        return True

    def mousePressed(self, evt):
        vp = self.cam.getViewport()
        ray = self.cam.getCameraToViewportRay(evt.x / vp.getActualWidth(), evt.y / vp.getActualHeight())
        self.ray_query.setRay(ray)
        self.ray_query.setSortByDistance(True)
        for hit in self.ray_query.execute():
            if evt.button == OgreBites.BUTTON_RIGHT:
                self.camman.setPivotOffset(ray.getPoint(hit.distance))
                return True

            if hit.movable:
                if hit.movable.getMovableType() == "Entity":
                    new_entity = self.scn_mgr.getEntity(hit.movable.getName())

                    if evt.button == OgreBites.BUTTON_LEFT:
                        if self.entity is not None:
                            self.entity.getParentSceneNode().showBoundingBox(False)

                        self.entity = new_entity
                        self.entity.getParentSceneNode().showBoundingBox(True)

            break
        return True

    def _toggle_bbox(self):
        enode = self.entity.getParentSceneNode()
        enode.showBoundingBox(not enode.getShowBoundingBox())

    def _toggle_wireframe_mode(self):
        polygon_mode = self.cam.getPolygonMode()

        if polygon_mode == Ogre.PM_SOLID:
            self.cam.setPolygonMode(Ogre.PM_WIREFRAME)
        if polygon_mode == Ogre.PM_WIREFRAME:
            self.cam.setPolygonMode(Ogre.PM_SOLID)

    def _toggle_axes(self):
        if not self.axes_visible:
            self.scn_mgr.addListener(self.axes)
        else:
            self.scn_mgr.removeListener(self.axes)
        
        self.axes_visible = not self.axes_visible

    def _save_screenshot(self):
        name = os.path.splitext(self.filename)[0]
        outpath = os.path.join(self.filedir, f"screenshot_{name}_")

        Ogre.LogManager.getSingleton().logMessage(f"Screenshot saved to folder: {self.filedir}")

        self.cam.getViewport().setOverlaysEnabled(False)
        self.getRoot().renderOneFrame()
        self.getRenderWindow().writeContentsToTimestampedFile(outpath, ".png")
        self.cam.getViewport().setOverlaysEnabled(True)

    def locateResources(self):
        self.filename = os.path.basename(self.infile)
        self.filedir = os.path.dirname(self.infile)

        rgm = Ogre.ResourceGroupManager.getSingleton()
        # ensure our resource group is separate, even with a local resources.cfg
        rgm.createResourceGroup(RGN_MESHVIEWER, False)

        # use parent implementation to locate system-wide RTShaderLib
        OgreBites.ApplicationContext.locateResources(self)

        if self.rescfg:
            cfg = Ogre.ConfigFile()
            cfg.loadDirect(self.rescfg)

            for sec, settings in cfg.getSettingsBySection().items():
                for kind, loc in settings.items():
                    rgm.addResourceLocation(loc, kind, sec)

        # explicitly add mesh location to be safe
        if not rgm.resourceLocationExists(self.filedir, RGN_USERDATA):
            rgm.addResourceLocation(self.filedir, "FileSystem", RGN_USERDATA)

        # add fonts to default resource group
        rgm.addResourceLocation(os.path.dirname(__file__) + "/fonts", "FileSystem", RGN_MESHVIEWER)
        
    def loadResources(self):
        rgm = Ogre.ResourceGroupManager.getSingleton()
        rgm.initialiseResourceGroup(Ogre.RGN_INTERNAL)
        rgm.initialiseResourceGroup(RGN_MESHVIEWER)

        # only capture default group
        self.logwin = LogWindow()
        Ogre.LogManager.getSingleton().getDefaultLog().addListener(self.logwin)
        rgm.initialiseResourceGroup(RGN_USERDATA)

    def setup(self):
        if self.next_rendersystem:
            self.getRoot().setRenderSystem(self.getRoot().getRenderSystemByName(self.next_rendersystem))

        OgreBites.ApplicationContext.setup(self)
        self.addInputListener(self)

        self.restart = False
        imgui_overlay = Ogre.Overlay.ImGuiOverlay()
        ImGui.GetIO().IniFilename = self.getFSLayer().getWritablePath("imgui.ini")

        root = self.getRoot()
        scn_mgr = root.createSceneManager()
        scn_mgr.addRenderQueueListener(self.getOverlaySystem())
        self.scn_mgr = scn_mgr

        # set listener to deal with missing materials
        self.mat_creator = MaterialCreator()
        Ogre.MeshManager.getSingleton().setListener(self.mat_creator)

        # HiDPI
        pixel_ratio = self.getDisplayDPI() / 96
        Ogre.Overlay.OverlayManager.getSingleton().setPixelRatio(pixel_ratio)
        ImGui.GetStyle().ScaleAllSizes(pixel_ratio)

        # for picking
        self.ray_query = scn_mgr.createRayQuery(Ogre.Ray())

        imgui_overlay.addFont("UIText", RGN_MESHVIEWER)
        self.logwin.font = imgui_overlay.addFont("LogText", RGN_MESHVIEWER)

        imgui_overlay.show()
        Ogre.Overlay.OverlayManager.getSingleton().addOverlay(imgui_overlay)
        imgui_overlay.disown()  # owned by OverlayMgr now

        shadergen = OgreRTShader.ShaderGenerator.getSingleton()
        shadergen.addSceneManager(scn_mgr)  # must be done before we do anything with the scene

        scn_mgr.setAmbientLight((.1, .1, .1))

        self.highlight_mat = Ogre.MaterialManager.getSingleton().create("Highlight", RGN_MESHVIEWER)
        self.highlight_mat.getTechniques()[0].getPasses()[0].setEmissive((1, 1, 0))

        main_cam_name = "MeshViewer/Cam"
        self.cam = scn_mgr.createCamera(main_cam_name)
        self.cam.setAutoAspectRatio(True)
        camnode = scn_mgr.getRootSceneNode().createChildSceneNode()
        camnode.attachObject(self.cam)

        vp = self.getRenderWindow().addViewport(self.cam)
        vp.setBackgroundColour((.3, .3, .3))

        self.gui = MeshViewerGui(self)
        self.getRenderWindow().addListener(self.gui)

        self.getRoot().renderOneFrame()
        self.getRoot().renderOneFrame()

        if self.filename.lower().endswith(".scene"):
            self.attach_node = scn_mgr.getRootSceneNode().createChildSceneNode()
            self.attach_node.loadChildren(self.filename)

            self.attach_node._update(True, False)
            diam = self.attach_node._getWorldAABB().getSize().length()

            for c in scn_mgr.getCameras().values():
                if c.getName() == main_cam_name:
                    continue
                # the camera frustum of any contained camera blows the above heuristic
                # so use the camera position instead
                diam = c.getDerivedPosition().length()
                break
        else:
            self.entity = scn_mgr.createEntity(self.filename)
            scn_mgr.getRootSceneNode().createChildSceneNode().attachObject(self.entity)
            diam = self.entity.getBoundingBox().getSize().length()

        self.cam.setNearClipDistance(diam * 0.01)

        self.axes = Ogre.DefaultDebugDrawer()
        self.axes.setStatic(True)
        self.axes.drawAxes(Ogre.Affine3.IDENTITY, diam / 4)
        self.axes_visible = False

        if len(scn_mgr.getMovableObjects("Light")) == 0:
            # skip creating light, if scene already contains one
            light = scn_mgr.createLight("MainLight")
            light.setType(Ogre.Light.LT_DIRECTIONAL)
            light.setSpecularColour(Ogre.ColourValue.White)
            camnode.attachObject(light)

        self.camman = OgreBites.CameraMan(camnode)
        self.camman.setStyle(OgreBites.CS_ORBIT)
        self.camman.setYawPitchDist(0, 0.3, diam)
        self.camman.setFixedYaw(False)

        self.imgui_input = OgreBites.ImGuiInputListener()
        self.input_dispatcher = OgreBites.InputListenerChain([self.imgui_input, self.camman])
        self.addInputListener(self.input_dispatcher)

    def shutdown(self):
        self.scn_mgr.removeListener(self.axes)
        Ogre.LogManager.getSingleton().getDefaultLog().removeListener(self.logwin)
        OgreBites.ApplicationContext.shutdown(self)

        self.entity = None
        self.axes = None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ogre Mesh Viewer")
    parser.add_argument("infile", nargs="?", help="path to a ogre .mesh, ogre .scene or any format supported by assimp")
    parser.add_argument("-c", "--rescfg", help="path to the resources.cfg")
    args = parser.parse_args()
    app = MeshViewer(args.infile, args.rescfg)

    while True:  # allow auto restart
        try:
            app.initApp()
            app.getRoot().startRendering()
            app.closeApp()
        except RuntimeError as e:
            raise SystemExit(e) from e

        if not app.restart: break
