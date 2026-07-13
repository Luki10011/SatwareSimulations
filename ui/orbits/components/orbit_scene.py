from __future__ import annotations

import numpy as np
import pyqtgraph.opengl as gl
from PIL import Image


class OrbitSceneHelper:
    """Helper methods for building 3D scene elements used by the orbit designer."""

    @staticmethod
    def create_eci_vectors() -> list[gl.GLLinePlotItem]:
        length = 20000.0
        width = 5.0

        x_points = np.array([[0, 0, 0], [length, 0, 0]], dtype=np.float32)
        x_axis = gl.GLLinePlotItem(pos=x_points, color=(1.0, 0.0, 0.0, 1.0), width=width, glOptions='opaque')

        y_points = np.array([[0, 0, 0], [0, length, 0]], dtype=np.float32)
        y_axis = gl.GLLinePlotItem(pos=y_points, color=(0.0, 1.0, 0.0, 1.0), width=width, glOptions='opaque')

        z_points = np.array([[0, 0, 0], [0, 0, length]], dtype=np.float32)
        z_axis = gl.GLLinePlotItem(pos=z_points, color=(0.0, 0.3, 1.0, 1.0), width=width, glOptions='opaque')

        return [x_axis, y_axis, z_axis]

    @staticmethod
    def create_earth() -> gl.GLMeshItem:
        rows = 1000
        cols = 1000
        radius = 6371.0

        try:
            img = Image.open("assets\\graphics\\earth_surface.jpg")
            img = img.convert("RGBA")
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            texture_data = np.array(img)
            img_h, img_w, _ = texture_data.shape

            verts = []
            faces = []
            v_colors = []

            for i in range(rows + 1):
                lat_frac = i / rows
                lat = (np.pi * lat_frac) - (np.pi / 2.0)
                y_pixel = int(lat_frac * (img_h - 1))

                for j in range(cols + 1):
                    lon_frac = j / cols
                    lon = 2.0 * np.pi * lon_frac
                    x_pixel = int(lon_frac * (img_w - 1))

                    x = radius * np.cos(lat) * np.cos(lon)
                    y = radius * np.cos(lat) * np.sin(lon)
                    z = radius * np.sin(lat)
                    verts.append([x, y, z])

                    pixel_color = texture_data[y_pixel, x_pixel] / 255.0
                    v_colors.append(pixel_color)

            for i in range(rows):
                for j in range(cols):
                    p1 = i * (cols + 1) + j
                    p2 = p1 + 1
                    p3 = (i + 1) * (cols + 1) + j
                    p4 = p3 + 1

                    faces.append([p1, p2, p4])
                    faces.append([p1, p4, p3])

            verts = np.array(verts, dtype=np.float32)
            faces = np.array(faces, dtype=np.uint32)
            v_colors = np.array(v_colors, dtype=np.float32)

            mesh_data = gl.MeshData(vertexes=verts, faces=faces, vertexColors=v_colors)
            return gl.GLMeshItem(meshdata=mesh_data, smooth=True, glOptions='opaque')
        except FileNotFoundError:
            print("Texture file not found; falling back to a simple Earth mesh.")
            mesh_data = gl.MeshData.sphere(rows=rows, cols=cols, radius=radius)
            return gl.GLMeshItem(meshdata=mesh_data, smooth=True, color=(0.2, 0.4, 0.8, 1.0))

    @staticmethod
    def create_angle_arc(vector1, vector2, radius=3000.0, num_segments=500, annotation=None, 
                     normal=None, color=None, shortest_path=False):
        """Create a 3D arc between two vectors using a counter-clockwise sweep around the supplied plane normal."""
        v1 = np.asarray(vector1, dtype=np.float32)
        v2 = np.asarray(vector2, dtype=np.float32)

        norm_v1 = np.linalg.norm(v1)
        norm_v2 = np.linalg.norm(v2)
        if norm_v1 < 1e-12 or norm_v2 < 1e-12:
            return None

        v1_u = v1 / norm_v1
        v2_u = v2 / norm_v2

        if normal is None:
            cross = np.cross(v1_u, v2_u)
            normal_norm = np.linalg.norm(cross)
            if normal_norm < 1e-8:
                return None
            normal = cross / normal_norm
        else:
            normal = np.asarray(normal, dtype=np.float32)
            normal_norm = np.linalg.norm(normal)
            if normal_norm < 1e-8:
                return None
            normal = normal / normal_norm

        tangent = np.cross(normal, v1_u)
        tangent_norm = np.linalg.norm(tangent)
        if tangent_norm < 1e-8:
            return None
        tangent = tangent / tangent_norm

        signed_angle = np.arctan2(np.dot(v2_u, tangent), np.dot(v1_u, v2_u))
        
        if not shortest_path:
            if signed_angle < 0.0:
                signed_angle += 2.0 * np.pi

        arc_points = []
        for i in range(num_segments + 1):
            t = i / num_segments
            angle = t * signed_angle
            rotated = (
                v1_u * np.cos(angle)
                + tangent * np.sin(angle)
            )
            arc_points.append(rotated * radius)

        if color is None:
            color = (1.0, 1.0, 0.0, 1.0)

        arc_points = np.array(arc_points, dtype=np.float32)
        arc_item = gl.GLLinePlotItem(pos=arc_points, color=color, width=2, glOptions='opaque')

        arc_label = None
        if annotation is not None:
            middle_index = len(arc_points) // 2
            center_of_arc = arc_points[middle_index]
            arc_label = gl.GLTextItem(pos=center_of_arc, text=annotation, color=(255, 255, 255, 255), glOptions='opaque')

        return arc_item, arc_label
