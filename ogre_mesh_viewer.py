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
           "byte4", "byte4n", "ubyte4n", "short2n", "short4n", "ushort2n", "ushort4n", "int1010102n",
           "half", "half2", "half3", "half4")

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

_rgbcol = ((1, 0.6, 0.6, 1), (0.6, 1, 0.6, 1), (0.6, 0.6, 1, 1))
_xyzstr = ("X {0:.2f}", "Y {0:.2f}", "Z {0:.2f}")
def draw_lbl_table_row(lbl, val, valstr = _xyzstr, valcol = _rgbcol):
    ImGui.TableNextRow()
    ImGui.TableNextColumn()
    ImGui.Text(lbl)
    for s, v, c in zip(valstr, val, valcol):
        ImGui.TableNextColumn()
        if v is None:
            continue
        ImGui.PushStyleColor(ImGui.Col_Text, ImGui.ImVec4(*c))
        ImGui.Text(s.format(v))
        ImGui.PopStyleColor()

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

class GridFloor:
    def __init__(self, scale, parent_node):
        self.material = Ogre.MaterialManager.getSingleton().create("VertexColour", RGN_MESHVIEWER)
        p = self.material.getTechnique(0).getPass(0)
        p.setLightingEnabled(False)
        p.setVertexColourTracking(Ogre.TVC_AMBIENT)

        self.plane_node = parent_node.createChildSceneNode()
        self.plane_node.setScale(scale, scale, scale)

        self.planes = [self._create_plane(i) for i in range(3)]

    def show_plane(self, plane):
        for i, grid in enumerate(self.planes):
            grid.setVisible(i == plane)

    def _create_plane(self, plane):
        normal = [0, 0, 0]
        normal[plane] = 1

        axis_color = [[0, 0, 0], [0, 0, 0]]
        axis_color[0][(plane + 2) % 3] = 1
        axis_color[1][(plane + 1) % 3] = 1

        grid_color = (0.2, 0.2, 0.2)

        # Compute the other axes based on the normal vector
        axis = [Ogre.Vector3(normal[1], normal[2], normal[0]),
                Ogre.Vector3(normal[2], normal[0], normal[1])]

        o = self.plane_node.getCreator().createManualObject(f"MeshViewer/plane{plane}")
        o.begin(self.material, Ogre.RenderOperation.OT_LINE_LIST)
        o.setQueryFlags(0)
        o.setVisible(False)

        for i in range(2):
            for j in range(-5, 6):
                cl = axis_color[i] if j == 0 else grid_color
                o.position(-axis[i] + axis[1 - i] * j/5)
                o.colour(cl)
                o.position(axis[i]  + axis[1 - i] * j/5)
                o.colour(cl)

        o.end()

        self.plane_node.attachObject(o)
        return o

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
        self.show_material = None
        self.side_panel_visible = True

        self.app = app

        self.highlighted = -1
        self.orig_mat = None
        self.logwin = app.logwin

        self.lod_idx_override = -1

    def draw_about(self):
        flags = ImGui.WindowFlags_AlwaysAutoResize
        self.show_about = ImGui.Begin("About OgreMeshViewer", self.show_about, flags)[1]
        ImGui.TextLinkOpenURL("OgreMeshViewer", "https://github.com/OGRECave/ogre-meshviewer")
        ImGui.SameLine(0, 0)
        ImGui.Text(" is licensed under the ")
        ImGui.SameLine(0, 0)
        ImGui.TextLinkOpenURL("MIT License.", "https://github.com/OGRECave/ogre-meshviewer/blob/master/LICENSE")
        ImGui.Text("by Pavel Rojtberg and contributors.")
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

        stats_dict = {
            "Average FPS":  f"{stats.avgFPS:.2f}",
            "Batches":      f"{stats.batchCount}",
            "Triangles":    f"{stats.triangleCount}"
        }

        ImGui.Text("Metrics")
        ImGui.Separator()
        if ImGui.BeginTable("Metrics", 2):
            for stat, value in stats_dict.items():
                ImGui.TableNextRow()
                ImGui.TableSetColumnIndex(0)
                ImGui.Text(stat)
                ImGui.TableSetColumnIndex(1)
                ImGui.Text(value)
            ImGui.EndTable()
        ImGui.End()

    def draw_loading(self):
        win = self.app.getRenderWindow()
        ImGui.SetNextWindowPos(ImGui.ImVec2(win.getWidth() * 0.5, win.getHeight() * 0.5), 0, ImGui.ImVec2(0.5, 0.5))

        flags = ImGui.WindowFlags_NoTitleBar | ImGui.WindowFlags_NoResize | ImGui.WindowFlags_NoSavedSettings
        ImGui.Begin("Loading", True, flags)
        ImGui.Text(self.app.filename)
        ImGui.Separator()
        ImGui.Text("\uf252 Loading..            ")
        ImGui.End()

    def draw_material(self, matname):
        if not ImGui.Begin("Material Details", True, 0)[1]:
            self.show_material = None

        ImGui.Text(f"\uf1b2 {printable(matname)}")

        matmgr = Ogre.MaterialManager.getSingleton()
        matmgr.setActiveScheme(self.app.cam.getViewport().getMaterialScheme())

        noalpha = ImGui.ColorEditFlags_NoAlpha

        mat = matmgr.getByName(matname)
        t = mat.getBestTechnique()
        passes = t.getPasses()

        for p in passes:
            if len(passes) > 1:
                ImGui.Text(f"Pass #{p.getIndex()}")
                ImGui.Separator()
            ImGui.ColorButton("##diffuse", ImGui.ImVec4(*p.getDiffuse()))
            ImGui.SameLine()
            ImGui.Text("Diffuse")
            ImGui.ColorButton("##specular", ImGui.ImVec4(*p.getSpecular()), noalpha)
            ImGui.SameLine()
            ImGui.Text("Specular")
            ImGui.ColorButton("##ambient", ImGui.ImVec4(*p.getAmbient()), noalpha)
            ImGui.SameLine()
            ImGui.Text("Ambient")

            tus = p.getTextureUnitStates()

            if len(tus) == 0:
                continue
            ImGui.Text("")
            ImGui.Text("Textures")
            ImGui.Separator()
            for tex in p.getTextureUnitStates():
                status = " (failed)" if tex.isBlank() else ""
                ImGui.Text(f"\uf03e {tex.getTextureName()}{status}")

        ImGui.End()

    def load_file(self):
        infile = askopenfilename(app.filedir)
        if not infile:
            return

        app.infile = infile
        app.reload()

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
                if ImGui.MenuItem("Open..", "F1"):
                    self.load_file()
                if ImGui.MenuItem("Reload", "F5"):
                    app.reload(keep_cam=True)
                if ImGui.MenuItem("Save Screenshot", "P"):
                    self.app._save_screenshot()
                ImGui.Separator()
                if ImGui.MenuItem("Renderer Settings"):
                    self.show_render_settings = True
                if ImGui.MenuItem("Quit", "Esc"):
                    self.app.getRoot().queueEndRendering()
                ImGui.EndMenu()

            if ImGui.BeginMenu("View"):
                if ImGui.MenuItem("Side Panel", "N", self.side_panel_visible):
                    self.side_panel_visible = not self.side_panel_visible
                if ImGui.BeginMenu("Fixed Camera Yaw"):
                    if ImGui.MenuItem("Disabled", "", self.app.fixed_yaw_axis == -1):
                        self.app.fixed_yaw_axis = -1
                        self.app.update_fixed_camera_yaw()
                    ImGui.Separator()
                    if ImGui.MenuItem("X Axis", "", self.app.fixed_yaw_axis == 0):
                        self.app.fixed_yaw_axis = 0
                        self.app.update_fixed_camera_yaw()
                    if ImGui.MenuItem("Y Axis", "", self.app.fixed_yaw_axis == 1):
                        self.app.fixed_yaw_axis = 1
                        self.app.update_fixed_camera_yaw()
                    if ImGui.MenuItem("Z Axis", "", self.app.fixed_yaw_axis == 2):
                        self.app.fixed_yaw_axis = 2
                        self.app.update_fixed_camera_yaw()
                    ImGui.EndMenu()
                if ImGui.MenuItem("Orthographic Projection", "KP5", self.app.cam.getProjectionType() == Ogre.PT_ORTHOGRAPHIC):
                    self.app._toggle_projection()
                if ImGui.MenuItem("Wireframe Mode", "W", app.cam.getPolygonMode() == Ogre.PM_WIREFRAME):
                    self.app._toggle_wireframe_mode()
                ImGui.EndMenu()

            if entity is not None and ImGui.BeginMenu("Overlay"):
                enode = entity.getParentSceneNode()
                if ImGui.MenuItem("Axes", "A", self.app.axes_visible):
                    self.app._toggle_axes()
                if ImGui.MenuItem("Grid", "G", self.app.grid_visible):
                    self.app._toggle_grid()
                if ImGui.MenuItem("Bounding Box", "B", enode.getShowBoundingBox()):
                    self.app._toggle_bbox()
                if entity.hasSkeleton() and ImGui.MenuItem("Skeleton", None, entity.getDisplaySkeleton()):
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

        if self.show_material is not None:
            self.draw_material(self.show_material)

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
        ImGui.Text("\uf016 "+mesh.getName())

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
                    ImGui.BulletText("Material:")
                    ImGui.SameLine()
                    if ImGui.TextLink("\uf1b2 "+printable(sm.getMaterialName())):
                        self.show_material = sm.getMaterialName()
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

            if mesh.getEdgeList():
                ImGui.Text("\uf05a EdgeLists present")

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
                ImGui.Text(f"\uf183 Skeleton: {mesh.getSkeletonName()}")
                # self.entity.setUpdateBoundingBoxFromSkeleton(True)
            if mesh.hasVertexAnimation():
                ImGui.Text("\uf1e0 Vertex Animations")

            for name, astate in animations.getAnimationStates().items():
                if ImGui.TreeNode(name):
                    ImGui.PushID(name)
                    if astate.getEnabled():
                        if ImGui.Button("\uf048 Reset"):
                            astate.setEnabled(False)
                            astate.setTimePosition(0)
                            if name in self.app.active_controllers:
                                controller_mgr.destroyController(self.app.active_controllers[name])
                    elif ImGui.Button("\uf04b Play"):
                        astate.setEnabled(True)
                        self.app.active_controllers[name] = controller_mgr.createFrameTimePassthroughController(
                            Ogre.AnimationStateControllerValue.create(astate, True))

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

            if ImGui.BeginTable("Bounds", 4, ImGui.TableFlags_SizingStretchProp):
                s = bounds.getSize()
                draw_lbl_table_row("Size", s)
                c = bounds.getCenter()
                draw_lbl_table_row("Center", c)
                draw_lbl_table_row("Radius", (mesh.getBoundingSphereRadius(), None, None), ("{0:.2f}", None, None), ((1, 1, 1, 1), None, None))
                ImGui.EndTable()

        if self.app.attach_node and ImGui.CollapsingHeader("Transform"):
            enode = entity.getParentSceneNode()

            if ImGui.BeginTable("Transform", 4, ImGui.TableFlags_SizingStretchProp):
                p = enode._getDerivedPosition()
                draw_lbl_table_row("Position", p)
                q = enode._getDerivedOrientation()
                o = [q.getPitch().valueDegrees(), q.getYaw().valueDegrees(), q.getRoll().valueDegrees()]
                draw_lbl_table_row("Orientation", o)
                s = enode._getDerivedScale()
                draw_lbl_table_row("Scale", s)
                ImGui.EndTable()

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
        self.fixed_yaw_axis = 1
        self.default_tilt = Ogre.Degree(20)
        self.grid_floor = None
        self.grid_visible = True

        self.active_controllers = {}

        self.next_rendersystem = ""
        self.next_campose = None

        # in case we want to show the file dialog
        root = tk.Tk()
        root.withdraw()

    def keyPressed(self, evt):
        if evt.keysym.sym == OgreBites.SDLK_ESCAPE:
            self.getRoot().queueEndRendering()
        if evt.keysym.sym == OgreBites.SDLK_KP_5:
            self._toggle_projection()
        elif evt.keysym.sym == ord("b"):
            self._toggle_bbox()
        elif evt.keysym.sym == ord("n"):
            self.gui.side_panel_visible = not self.gui.side_panel_visible
        elif evt.keysym.sym == ord("a"):
            self._toggle_axes()
        elif evt.keysym.sym == ord("g"):
            self._toggle_grid()
        elif evt.keysym.sym == ord("p"):
            self._save_screenshot()
        elif evt.keysym.sym == ord("w"):
            self._toggle_wireframe_mode()
        elif evt.keysym.sym == OgreBites.SDLK_F1:
            self.gui.load_file()
        elif evt.keysym.sym == OgreBites.SDLK_F5:
            self.reload(keep_cam=True)

        return True

    def mousePressed(self, evt):
        vp = self.cam.getViewport()
        ray = self.cam.getCameraToViewportRay(evt.x / vp.getActualWidth(), evt.y / vp.getActualHeight())
        self.ray_query.setRay(ray)
        self.ray_query.setSortByDistance(True)
        for hit in self.ray_query.execute():
            if evt.clicks == 2:
                self.camman.setPivotOffset(ray.getPoint(hit.distance))
                return True
            
            new_entity = hit.movable.castEntity()

            if self.attach_node and new_entity and evt.button == OgreBites.BUTTON_LEFT:
                if self.entity is not None:
                    self.entity.getParentSceneNode().showBoundingBox(False)

                self.entity = new_entity
                self.entity.getParentSceneNode().showBoundingBox(True)
            break

        return True

    def mouseWheelRolled(self, evt):
        if self.cam.getProjectionType() == Ogre.PT_ORTHOGRAPHIC:
            camnode = self.camman.getCamera()
            diam = camnode.getPosition().length()
            self.cam.setOrthoWindowHeight(diam)

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

    def _toggle_grid(self):
        self.grid_visible = not self.grid_visible

        if self.grid_visible:
            self.grid_floor.show_plane(self.fixed_yaw_axis)
        else:
            self.grid_floor.show_plane(-1)

    def _toggle_projection(self):
        if self.cam.getProjectionType() == Ogre.PT_PERSPECTIVE:
            self.cam.setProjectionType(Ogre.PT_ORTHOGRAPHIC)
            camnode = self.camman.getCamera()
            diam = camnode.getPosition().length()
            self.cam.setOrthoWindowHeight(diam)
        else:
            self.cam.setProjectionType(Ogre.PT_PERSPECTIVE)

    def _save_screenshot(self):
        name = os.path.splitext(self.filename)[0]
        outpath = os.path.join(self.filedir, f"screenshot_{name}_")

        Ogre.LogManager.getSingleton().logMessage(f"Screenshot saved to folder: {os.path.normpath(self.filedir)}")

        self.cam.getViewport().setOverlaysEnabled(False)
        self.getRenderWindow().update(False)
        self.getRenderWindow().writeContentsToTimestampedFile(outpath, ".png")
        self.cam.getViewport().setOverlaysEnabled(True)

    def update_fixed_camera_yaw(self):
        camnode = self.camman.getCamera()
        diam = camnode.getPosition().length()
        camnode.setOrientation(Ogre.Quaternion.IDENTITY)

        yaw_axis = [0, 0, 0]
        yaw_axis[self.fixed_yaw_axis] = 1
        camnode.setFixedYawAxis(self.fixed_yaw_axis != -1, yaw_axis)
        self.camman.setFixedYaw(self.fixed_yaw_axis != -1)
        if self.grid_visible:
            self.grid_floor.show_plane(self.fixed_yaw_axis)

        if self.next_campose:
            camnode.setPosition(self.next_campose[0])
            camnode.setOrientation(self.next_campose[1])
            self.next_campose = None
        elif self.fixed_yaw_axis == 0:
            self.camman.setYawPitchDist(0, 0, diam)
            camnode.roll(-Ogre.Degree(90))
        elif self.fixed_yaw_axis == 2:
            self.camman.setYawPitchDist(0, self.default_tilt - Ogre.Degree(90), diam)
        else:
            self.camman.setYawPitchDist(0, self.default_tilt, diam)

    def reload(self, keep_cam=False):
        if not app.infile:
            return

        if keep_cam:
            camnode = self.camman.getCamera()
            # multiply to store a copy instead of a reference
            self.next_campose = (camnode.getPosition()*1, camnode.getOrientation()*1)

        app.restart = True
        app.getRoot().queueEndRendering()

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

        rgm.setWorldResourceGroupName(RGN_USERDATA) # used by .scene loader

    def setup(self):
        if self.next_rendersystem:
            self.getRoot().setRenderSystem(self.getRoot().getRenderSystemByName(self.next_rendersystem))

        OgreBites.ApplicationContext.setup(self)

        self.restart = False
        imgui_overlay = self.initialiseImGui()
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

        # imgui needs warmup to render on first frame
        # see https://github.com/ocornut/imgui/issues/1893#issuecomment-399102821
        self.getRenderWindow().update(False)
        self.getRoot().renderOneFrame()

        Ogre.LogManager.getSingleton().logMessage(f"Opening file: {os.path.normpath(self.infile)}")

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
            self.attach_node = None
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

        self.grid_floor = GridFloor(diam, scn_mgr.getRootSceneNode())

        self.camman = OgreBites.CameraMan(camnode)
        self.camman.setStyle(OgreBites.CS_ORBIT)

        # We need to set YawPitchDist to initial values, so "diam" is properly set
        self.camman.setYawPitchDist(0, self.default_tilt, diam)
        self.update_fixed_camera_yaw()

        self.input_dispatcher = OgreBites.InputListenerChain([self.getImGuiInputListener(), self.camman, self])
        self.addInputListener(self.input_dispatcher)

    def windowResized(self, win):
        # remember the resolution for next start
        self.getRoot().getRenderSystem().setConfigOption("Video Mode", f"{win.getWidth()} x {win.getHeight()}")

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
