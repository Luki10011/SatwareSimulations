import numpy as np
import pyqtgraph.opengl as gl

from PyQt6.QtGui import QColor, QImage
from PyQt6.QtWidgets import QWidget, QVBoxLayout

from core.physics.dataclasses.satellite_configuration import reaction_wheel_axes


class SatelliteScene(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self._body_item = None
        self._outline_items = []
        self._panel_items = []
        self._wheel_items = []
        self._axis_items = []
        
        self.setup_view()
        self.set_dimensions([], wheel_axes=None)

    def setup_view(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor(QColor("#080d1a"))
        self.view.setCameraPosition(distance=6, elevation=20, azimuth=35)
        layout.addWidget(self.view)
        self._draw_rgb_axes(length=1.5, width=3.5)


    def _clear_scene(self) -> None:
        all_items = [
            self._body_item,
            *self._outline_items,
            *self._panel_items,
            *self._wheel_items,
        ]
        for item in all_items:
            if item is not None:
                self.view.removeItem(item)
                
        self._body_item = None
        self._logo_item = None
        self._outline_items = []
        self._panel_items = []
        self._wheel_items = []
        self._axis_items = []

    def _draw_rgb_axes(self, length: float = 1.0, width: float = 4.0) -> None:
        """Draws the RGB axes (X, Y, Z) in the 3D scene with specified length and width."""
        axes_data = [
            ([0, 0, 0], [length, 0, 0], (1.0, 0.2, 0.2, 1.0)),  # X - Czerwony
            ([0, 0, 0], [0, length, 0], (0.2, 0.9, 0.2, 1.0)),  # Y - Zielony
            ([0, 0, 0], [0, 0, length], (100/255, 100/255, 255/255, 255/255)),  # Z - Niebieski
        ]
        
        for start, end, color in axes_data:
            line = gl.GLLinePlotItem(
                pos=np.array([start, end], dtype=np.float32),
                color=color,
                width=width,
                glOptions="opaque",
            )
            self.view.addItem(line)
            self._axis_items.append(line)

    def _create_box_mesh(
        self, 
        size, 
        translation=(0.0, 0.0, 0.0), 
        color=(0.25, 0.65, 0.95, 0.95), 
        gl_options="opaque"
    ):
        x_dim, y_dim, z_dim = size
        vertices = np.array([
            [-x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
            [x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
            [x_dim / 2.0 + translation[0], y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
            [-x_dim / 2.0 + translation[0], y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
            [-x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1], z_dim / 2.0 + translation[2]],
            [x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1], z_dim / 2.0 + translation[2]],
            [x_dim / 2.0 + translation[0], y_dim / 2.0 + translation[1], z_dim / 2.0 + translation[2]],
            [-x_dim / 2.0 + translation[0], y_dim / 2.0 + translation[1], z_dim / 2.0 + translation[2]],
        ], dtype=np.float32)

        faces = np.array([
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
        ], dtype=np.uint32)

        mesh_data = gl.MeshData(vertexes=vertices, faces=faces)
        return gl.GLMeshItem(meshdata=mesh_data, smooth=True, color=color, shader="shaded", glOptions=gl_options)


    
    def set_dimensions(self, dimensions, wheel_axes=None) -> None:

        if not dimensions or len(dimensions) < 3:
            return
        
        self._clear_scene()

        a, b, h = dimensions
        scale_factor = 1.6 / max(max(a, b, h), 0.2)
        a_scaled, b_scaled, h_scaled = a * scale_factor, b * scale_factor, h * scale_factor


        self._body_item = self._create_box_mesh(
            (a_scaled, b_scaled, h_scaled), 
            color=(0.15, 0.20, 0.28, 0.95), 
            gl_options="opaque"
        )
        self.view.addItem(self._body_item)

        outline_segments = [
            ((-a_scaled / 2.0, -b_scaled / 2.0, -h_scaled / 2.0), (a_scaled / 2.0, -b_scaled / 2.0, -h_scaled / 2.0)),
            ((a_scaled / 2.0, -b_scaled / 2.0, -h_scaled / 2.0), (a_scaled / 2.0, b_scaled / 2.0, -h_scaled / 2.0)),
            ((a_scaled / 2.0, b_scaled / 2.0, -h_scaled / 2.0), (-a_scaled / 2.0, b_scaled / 2.0, -h_scaled / 2.0)),
            ((-a_scaled / 2.0, b_scaled / 2.0, -h_scaled / 2.0), (-a_scaled / 2.0, -b_scaled / 2.0, -h_scaled / 2.0)),
            ((-a_scaled / 2.0, -b_scaled / 2.0, h_scaled / 2.0), (a_scaled / 2.0, -b_scaled / 2.0, h_scaled / 2.0)),
            ((a_scaled / 2.0, -b_scaled / 2.0, h_scaled / 2.0), (a_scaled / 2.0, b_scaled / 2.0, h_scaled / 2.0)),
            ((a_scaled / 2.0, b_scaled / 2.0, h_scaled / 2.0), (-a_scaled / 2.0, b_scaled / 2.0, h_scaled / 2.0)),
            ((-a_scaled / 2.0, b_scaled / 2.0, h_scaled / 2.0), (-a_scaled / 2.0, -b_scaled / 2.0, h_scaled / 2.0)),
            ((-a_scaled / 2.0, -b_scaled / 2.0, -h_scaled / 2.0), (-a_scaled / 2.0, -b_scaled / 2.0, h_scaled / 2.0)),
            ((a_scaled / 2.0, -b_scaled / 2.0, -h_scaled / 2.0), (a_scaled / 2.0, -b_scaled / 2.0, h_scaled / 2.0)),
            ((a_scaled / 2.0, b_scaled / 2.0, -h_scaled / 2.0), (a_scaled / 2.0, b_scaled / 2.0, h_scaled / 2.0)),
            ((-a_scaled / 2.0, b_scaled / 2.0, -h_scaled / 2.0), (-a_scaled / 2.0, b_scaled / 2.0, h_scaled / 2.0)),
        ]
        for start, end in outline_segments:
            line_item = gl.GLLinePlotItem(
                pos=np.array([start, end], dtype=np.float32),
                color=(0.5, 0.7, 0.9, 0.9),
                width=1.5,
                glOptions="opaque",
            )
            self.view.addItem(line_item)
            self._outline_items.append(line_item)

        pv_color = (0.08, 0.15, 0.35, 0.98)
        t = 0.008

        panels_config = [
            ((t, b_scaled * 0.85, h_scaled * 0.85), (a_scaled / 2.0 + t / 2.0, 0, 0)),
            ((t, b_scaled * 0.85, h_scaled * 0.85), (-a_scaled / 2.0 - t / 2.0, 0, 0)),
            ((a_scaled * 0.85, t, h_scaled * 0.85), (0, b_scaled / 2.0 + t / 2.0, 0)),
            ((a_scaled * 0.85, t, h_scaled * 0.85), (0, -b_scaled / 2.0 - t / 2.0, 0)),
            ((a_scaled * 0.85, b_scaled * 0.85, t), (0, 0, h_scaled / 2.0 + t / 2.0)),
            ((a_scaled * 0.85, b_scaled * 0.85, t), (0, 0, -h_scaled / 2.0 - t / 2.0)),
        ]

        for size, trans in panels_config:
            panel = self._create_box_mesh(size, translation=trans, color=pv_color)
            self.view.addItem(panel)
            self._panel_items.append(panel)


        # 6. Wektory osi kół reakcyjnych (bez fizycznej geometrii dysków)
        if wheel_axes is None:
            wheel_axes = [
                np.array([1.0, 0.0, 0.0], dtype=float),
                np.array([0.0, 1.0, 0.0], dtype=float),
                np.array([0.0, 0.0, 1.0], dtype=float),
            ]

        # Długość wektora osi (wychodzi lekko poza obrys satelity, co zapewnia świetną widoczność)
        vector_length = min(a_scaled, b_scaled, h_scaled) * 0.45

        for axis in wheel_axes:
            axis = np.array(axis, dtype=float)
            norm = np.linalg.norm(axis)
            if norm == 0.0:
                continue
            axis_unit = axis / norm
            end_point = axis_unit * vector_length

            # Rysowanie linii wektora osi koła (złoty / jaskrawożółty kolor)
            wheel_axis_line = gl.GLLinePlotItem(
                pos=np.array([[0.0, 0.0, 0.0], end_point], dtype=np.float32),
                color=(1.0, 0.84, 0.0, 0.95),  # Gold
                width=3.0,
                glOptions="opaque",
            )
            self.view.addItem(wheel_axis_line)
            self._wheel_items.append(wheel_axis_line)

            # Rysowanie punktu/węzła na końcu wektora osi
            tip_scatter = gl.GLScatterPlotItem(
                pos=np.array([end_point], dtype=np.float32),
                color=(1.0, 0.9, 0.3, 1.0),
                size=7.0,
                pxMode=True,
                glOptions="opaque",
            )
            self.view.addItem(tip_scatter)
            self._wheel_items.append(tip_scatter)

    def update_from_data(self, data: dict) -> None:
        mechanical = data.get("mechanical", {})
        dimensions = mechanical.get("dimensions") or [0.3, 0.2, 0.1]
        if len(dimensions) < 3:
            dimensions = [0.3, 0.2, 0.1]
        reaction_wheels = data.get("reaction_wheels", {})
        wheel_axes = reaction_wheel_axes(
            str(reaction_wheels.get("configuration", "principal")).strip().lower(),
            int(reaction_wheels.get("wheel_count", 3)),
        )
        self.set_dimensions(tuple(dimensions[:3]), wheel_axes=wheel_axes)