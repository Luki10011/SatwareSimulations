import numpy as np
import pyqtgraph.opengl as gl

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QWidget, QVBoxLayout


class SatelliteScene(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self._body_item = None
        self._outline_items = []
        self._panel_items = []
        self._wheel_items = []
        self.setup_view()
        self.set_dimensions((0.3, 0.2, 0.1), wheel_count=3)

    def setup_view(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.view = gl.GLViewWidget()
        self.view.setBackgroundColor(QColor("#0f172a"))
        self.view.setCameraPosition(distance=3.8, elevation=20, azimuth=35)
        layout.addWidget(self.view)

        axis_item = gl.GLAxisItem()
        axis_item.setSize(x=1.2, y=1.2, z=1.2)
        self.view.addItem(axis_item)

    def _clear_scene(self) -> None:
        for item in [self._body_item, *self._outline_items, *self._panel_items, *self._wheel_items]:
            if item is not None:
                self.view.removeItem(item)
        self._body_item = None
        self._outline_items = []
        self._panel_items = []
        self._wheel_items = []

    def _create_box_mesh(self, size, translation=(0.0, 0.0, 0.0), color=(0.25, 0.65, 0.95, 0.95)):
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
        return gl.GLMeshItem(meshdata=mesh_data, smooth=True, color=color, shader="shaded", glOptions="opaque")

    def set_dimensions(self, dimensions, wheel_count: int = 3) -> None:
        self._clear_scene()

        a, b, h = dimensions
        scale_factor = 1.6 / max(max(a, b, h), 0.2)
        a_scaled = a * scale_factor
        b_scaled = b * scale_factor
        h_scaled = h * scale_factor

        self._body_item = self._create_box_mesh((a_scaled, b_scaled, h_scaled), color=(0.28, 0.62, 0.90, 0.95))
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
                color=(0.95, 0.98, 1.0, 0.95),
                width=1.4,
                glOptions="opaque",
            )
            self.view.addItem(line_item)
            self._outline_items.append(line_item)

        panel_width = a_scaled * 0.75
        panel_height = h_scaled * 0.7
        panel_thickness = 0.02
        for translation in [(-a_scaled / 2.0 - panel_thickness / 2.0, 0.0, 0.0), (a_scaled / 2.0 + panel_thickness / 2.0, 0.0, 0.0)]:
            panel_item = self._create_box_mesh((panel_thickness, panel_width, panel_height), translation=translation, color=(0.2, 0.24, 0.3, 0.95))
            self.view.addItem(panel_item)
            self._panel_items.append(panel_item)

        wheel_radius = min(a_scaled, b_scaled, h_scaled) * 0.12
        if wheel_count >= 3:
            wheel_positions = [
                (0.0, b_scaled * 0.55, 0.0),
                (-a_scaled * 0.3, -b_scaled * 0.25, 0.0),
                (a_scaled * 0.3, -b_scaled * 0.25, 0.0),
            ]
        else:
            wheel_positions = [(0.0, b_scaled * 0.55, 0.0)]

        for x_pos, y_pos, z_pos in wheel_positions[:max(wheel_count, 1)]:
            wheel_mesh = gl.MeshData.sphere(rows=12, cols=12, radius=wheel_radius)
            wheel_item = gl.GLMeshItem(meshdata=wheel_mesh, smooth=True, color=(0.95, 0.8, 0.25, 1.0), shader="shaded", glOptions="opaque")
            wheel_item.translate(x_pos, y_pos, z_pos, local=False)
            self.view.addItem(wheel_item)
            self._wheel_items.append(wheel_item)

    def update_from_data(self, data: dict) -> None:
        mechanical = data.get("mechanical", {})
        dimensions = mechanical.get("dimensions") or [0.3, 0.2, 0.1]
        if len(dimensions) < 3:
            dimensions = [0.3, 0.2, 0.1]
        reaction_wheels = data.get("reaction_wheels", {})
        self.set_dimensions(tuple(dimensions[:3]), wheel_count=int(reaction_wheels.get("wheel_count", 3)))