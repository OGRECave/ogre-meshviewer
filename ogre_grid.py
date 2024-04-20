#!/usr/bin/env python

import Ogre
import math

GRID_MATERIAL = "MeshViewer/VertexColour"

class GridFloor:
    def __init__(self, scene, resource_group):
        self.scn_mgr = scene
        self.resource_group = resource_group
        self.plane_names = ["YZPlane", "XZPlane", "XYPlane"]
        self.normals = [
            (1, 0, 0),  # YZPlane normal
            (0, 1, 0),  # XZPlane normal
            (0, 0, 1)   # XYPlane normal
            ]
        self.axis_colors = [
            Ogre.ColourValue(1, 0, 0, 1),
            Ogre.ColourValue(0, 1, 0, 1),
            Ogre.ColourValue(0, 0, 1, 1)
            ]

    def nearest_power_of_two(self, n):
        if n < 1:
            return 1

        # Calculate the logarithm base 2 and find the floor and ceil
        log2_n = math.log2(n)
        lower_power = 2 ** math.floor(log2_n)
        higher_power = 2 ** math.ceil(log2_n)

        # Compare which power of two is closer to the original number
        if abs(lower_power - n) < abs(higher_power - n):
            return lower_power
        else:
            return higher_power

    def show_plane(self, plane):
        for p in range(0, 3):
            plane_name = "MeshViewer/" + self.plane_names[p]
            plane_node = self.scn_mgr.getSceneNode(plane_name)
            plane_node.setVisible(p == plane)

    def create_material(self):
        material = Ogre.MaterialManager.getSingleton().create(GRID_MATERIAL, self.resource_group);
        p = material.getTechnique(0).getPass(0);
        p.setLightingEnabled(False);
        p.setVertexColourTracking(Ogre.TVC_AMBIENT);

    def create_planes(self, diam):
        self.create_material()
        if diam < 1:
            subdiv = int(self.nearest_power_of_two(1/diam))
        else:
            subdiv = 1

        for plane in range(0, 3):
            plane_name = "MeshViewer/" + self.plane_names[plane]
            self.create_plane(plane, int(math.ceil(diam)), subdiv)

    def create_plane(self, plane, diam, subdiv):
        cl = None
        axis_color = None
        plane_name = "MeshViewer/" + self.plane_names[plane]
        min_val = -diam
        max_val = diam

        normal = self.normals[plane]

        color_X = self.axis_colors[0]
        color_Y = self.axis_colors[1]
        color_Z = self.axis_colors[2]

        if plane == 0:
            axis_color = [color_Y, color_Z]
        elif plane == 1:
            axis_color = [color_X, color_Z]
        elif plane == 2:
            axis_color = [color_Y, color_X]

        c1 = 0.2
        c2 = 0.4
        grid_color = Ogre.ColourValue(c1, c1, c1, 1)
        subd_color = Ogre.ColourValue(c2, c2, c2, 1)

        # Compute the other axes based on the normal vector
        axis = [
            Ogre.Vector3(normal[1], normal[2], normal[0]),
            Ogre.Vector3(normal[2], normal[0], normal[1])
            ]

        o = self.scn_mgr.createManualObject(plane_name);
        o.begin(GRID_MATERIAL, Ogre.RenderOperation.OT_LINE_LIST, self.resource_group)
        o.setQueryFlags(0)

        for i in range(0, 2):
            for j in range(min_val * subdiv, max_val * subdiv + 1):
                if j == 0:
                    cl = axis_color[i]
                elif (j * (1/subdiv)) % 1 == 0:
                    cl = grid_color
                else:
                    cl = subd_color
                o.position(axis[i] * min_val + axis[1 - i] * j * (1/subdiv))
                o.colour(cl)
                o.position(axis[i] * max_val + axis[1 - i] * j * (1/subdiv))
                o.colour(cl)

        o.end()

        plane_node = self.scn_mgr.getRootSceneNode().createChildSceneNode(plane_name)
        plane_node.attachObject(o)
        plane_node.setVisible(False)
