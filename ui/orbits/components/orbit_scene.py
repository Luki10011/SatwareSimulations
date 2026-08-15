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
    def create_ecef_vectors() -> list[gl.GLLinePlotItem]:
        """Create the ECEF coordinate axes with distinctive colors."""
        length = 20000.0
        width = 4.0

        # Kolory: Pomarańczowy (X), Żółty (Y), Fuksja (Z)
        x_points = np.array([[0, 0, 0], [length, 0, 0]], dtype=np.float32)
        x_axis = gl.GLLinePlotItem(pos=x_points, color=(1.0, 0.6, 0.0, 1.0), width=width, glOptions='opaque')

        y_points = np.array([[0, 0, 0], [0, length, 0]], dtype=np.float32)
        y_axis = gl.GLLinePlotItem(pos=y_points, color=(0.9, 0.9, 0.0, 1.0), width=width, glOptions='opaque')

        z_points = np.array([[0, 0, 0], [0, 0, length]], dtype=np.float32)
        z_axis = gl.GLLinePlotItem(pos=z_points, color=(0.8, 0.0, 0.8, 1.0), width=width, glOptions='opaque')

        return [x_axis, y_axis, z_axis]

    @staticmethod
    def create_eci_labels(length: float = 20000.0) -> list[gl.GLTextItem]:
        """Create text labels for the static ECI frame axes."""
        return [
            gl.GLTextItem(pos=np.array([length * 1.05, 0, 0], dtype=np.float32), text="X_ECI", color=(255, 100, 100, 255)),
            gl.GLTextItem(pos=np.array([0, length * 1.05, 0], dtype=np.float32), text="Y_ECI", color=(100, 255, 100, 255)),
            gl.GLTextItem(pos=np.array([0, 0, length * 1.05], dtype=np.float32), text="Z_ECI", color=(100, 100, 255, 255))
        ]

    @staticmethod
    def create_ecef_labels(length: float = 20000.0) -> list[gl.GLTextItem]:
        """Create text labels for the rotating ECEF frame axes."""
        return [
            gl.GLTextItem(pos=np.array([length * 1.05, 0, 0], dtype=np.float32), text="X_ECEF", color=(255, 180, 50, 255)),
            gl.GLTextItem(pos=np.array([0, length * 1.05, 0], dtype=np.float32), text="Y_ECEF", color=(220, 255, 50, 255)),
            gl.GLTextItem(pos=np.array([0, 0, length * 1.05], dtype=np.float32), text="Z_ECEF", color=(255, 50, 255, 255))
        ]



    @staticmethod
    def create_earth(rows=500, cols=1000, radius=6371.0) -> gl.GLMeshItem:
        try:
            # ============================================================
            # 1. Wczytanie tekstury
            # ============================================================

            img = Image.open("assets\\graphics\\earth_surface.jpg")
            img = img.convert("RGBA")
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            texture_data = np.asarray(img, dtype=np.uint8)
            img_h, img_w, _ = texture_data.shape

            # ============================================================
            # 2. Siatka współrzędnych
            # ============================================================

            # Szerokość geograficzna:
            # -PI/2 ... +PI/2
            lat = np.linspace(
                -np.pi / 2.0,
                np.pi / 2.0,
                rows + 1,
                dtype=np.float32
            )

            # Długość geograficzna:
            # 0 ... 2PI
            lon = np.linspace(
                0.0,
                2.0 * np.pi,
                cols + 1,
                dtype=np.float32
            )

            lat_grid, lon_grid = np.meshgrid(
                lat,
                lon,
                indexing="ij"
            )

            cos_lat = np.cos(lat_grid)

            # ============================================================
            # 3. Wierzchołki
            # ============================================================

            x = radius * cos_lat * np.cos(lon_grid)
            y = radius * cos_lat * np.sin(lon_grid)
            z = radius * np.sin(lat_grid)

            verts = np.stack(
                (x, y, z),
                axis=-1
            ).reshape(-1, 3)

            verts = np.ascontiguousarray(
                verts,
                dtype=np.float32
            )

            # ============================================================
            # 4. Normalne
            #
            # Dla kuli:
            #
            # normal = position / radius
            #
            # Nie musimy pozwalać MeshData liczyć ich iteracyjnie.
            # ============================================================

            normals = verts / np.float32(radius)

            normals = np.ascontiguousarray(
                normals,
                dtype=np.float32
            )

            # ============================================================
            # 5. Kolory z tekstury
            #
            # Zamiast float32 / 255:
            # zostawiamy uint8.
            #
            # PyQtGraph/OpenGL potrafi użyć ich bezpośrednio jako
            # znormalizowanych wartości kolorów.
            # ============================================================

            y_pixels = np.linspace(
                0,
                img_h - 1,
                rows + 1,
                dtype=np.int32
            )

            # Odpowiada Twojemu:
            #
            # u_texture = (lon_frac + 0.5) % 1.0
            #
            lon_frac = np.linspace(
                0.0,
                1.0,
                cols + 1,
                dtype=np.float32
            )

            u_texture = (lon_frac + 0.5) % 1.0

            x_pixels = (
                u_texture * (img_w - 1)
            ).astype(np.int32)

            v_colors = texture_data[
                y_pixels[:, None],
                x_pixels[None, :]
            ]

            v_colors = np.ascontiguousarray(
                v_colors.reshape(-1, 4),
                dtype=np.uint8
            )

            # ============================================================
            # 6. Indeksy trójkątów
            # ============================================================

            vertex_cols = cols + 1

            i = np.arange(
                rows,
                dtype=np.uint32
            )[:, None]

            j = np.arange(
                cols,
                dtype=np.uint32
            )[None, :]

            p1 = i * vertex_cols + j
            p2 = p1 + 1
            p3 = (i + 1) * vertex_cols + j
            p4 = p3 + 1

            # shape:
            # (rows, cols, 2, 3)
            #
            # Trójkąty:
            #
            # p1 p2 p4
            # p1 p4 p3

            faces = np.stack(
                (
                    np.stack((p1, p2, p4), axis=-1),
                    np.stack((p1, p4, p3), axis=-1)
                ),
                axis=2
            )

            faces = faces.reshape(-1, 3)

            faces = np.ascontiguousarray(
                faces,
                dtype=np.uint32
            )

            # ============================================================
            # 7. MeshData
            # ============================================================

            mesh_data = gl.MeshData(
                vertexes=verts,
                faces=faces,
                vertexColors=v_colors
            )

            # ============================================================
            # 8. GLMeshItem
            # ============================================================

            return gl.GLMeshItem(
                meshdata=mesh_data,
                smooth=True,
                computeNormals=False,
                glOptions="opaque"
            )

        except FileNotFoundError:
            print(
                "Texture file not found; "
                "falling back to a simple Earth mesh."
            )

            mesh_data = gl.MeshData.sphere(
                rows=rows,
                cols=cols,
                radius=radius
            )

            return gl.GLMeshItem(
                meshdata=mesh_data,
                smooth=True,
                color=(0.2, 0.4, 0.8, 1.0)
            )

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
