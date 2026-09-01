import datetime
import math
import numpy as np
import pyqtgraph.opengl as gl
from OpenGL.GL import (
    GL_MODELVIEW,
    GL_PROJECTION,
    glLoadIdentity,
    glMatrixMode,
    glMultMatrixf,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMatrix4x4, QVector3D
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ui.orbits.components.orbit_scene import OrbitSceneHelper
from utils.rotations import datetime_to_julian_date, euler_321_to_rotation_matrix, get_initial_gmst
from collections import deque

from utils.ui.multi_pass import MultiPassGLViewWidget

class SimulationScene(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.view = None
        self.earth = None
        self.satellite_items = []
        now = datetime.datetime.now(datetime.timezone.utc)
        current_jd = datetime_to_julian_date(now)
        
        self.initial_gmst = get_initial_gmst(current_jd)
        self.current_ecef_rotation = self.initial_gmst
        self._axis_items = []


        self.setup_view()

    def setup_view(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.view = MultiPassGLViewWidget(self)

        self.earth = OrbitSceneHelper.create_earth(rows=1000, cols=1000)
        self.view.add_background_item(self.earth)
        self.view.opts["glOptions"] = "opaque"

        # Tworzenie domyślnej geometrii satelity (wymiary w metrach: 2m x 1m x 1m)
        self.create_satellite((2.0, 1.0, 1.0))

        self.view.setCameraPosition(distance=0.005, azimuth=30, elevation=20)
        self._set_camera_limits(0.002, 0.2)
        self._ensure_ECEF_orientation(self.initial_gmst)

        layout.addWidget(self.view)

    def _set_camera_limits(self, min_dist: float, max_dist: float):
        """Set the minimum and maximum camera distance for zooming in/out."""
        original_wheel_event = self.view.wheelEvent

        def custom_wheel_event(event):
            delta = event.angleDelta().y()
            current_dist = self.view.opts['distance']

            if delta < 0 and current_dist >= max_dist:
                event.accept()  
                return

            if delta > 0 and current_dist <= min_dist:
                event.accept()  
                return

            original_wheel_event(event)

        self.view.wheelEvent = custom_wheel_event
    
    def _ensure_ECEF_orientation(self, angle_deg):
    
        self.earth.resetTransform()
        transform = QMatrix4x4()
        transform.rotate(angle_deg, 0.0, 0.0, 1.0)
        self.earth.setTransform(transform)
        
        self.view.update()

    def _draw_rgb_body_axes(self, length: float = 1.5, width: float = 4.0) -> None:
        """Rysuje osie lokalnego układu ciała."""

        axes_data = [
            ([0, 0, 0], [length, 0, 0], (1.0, 0.2, 0.2, 1.0)),
            ([0, 0, 0], [0, length, 0], (0.2, 0.9, 0.2, 1.0)),
            ([0, 0, 0], [0, 0, length], (100/255, 100/255, 255/255, 1.0)),
        ]

        for start, end, color in axes_data:
            line = gl.GLLinePlotItem(
                pos=np.array([start, end], dtype=np.float32),
                color=color,
                width=width,
                glOptions="opaque",
            )
            line.setVisible(False)
            self.view.add_foreground_item(line)
            self._axis_items.append(line)


    def show_body_frame(self, is_visible : bool):
        if self._axis_items:
            for item in self._axis_items:
                item.setVisible(is_visible)
        
    def _create_box_mesh(
        self,
        size: tuple[float, float, float],
        translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        color: tuple[float, float, float, float] = (0.25, 0.65, 0.95, 0.95),
        gl_options: str = "opaque",
    ) -> gl.GLMeshItem:
        x_dim, y_dim, z_dim = size
        dx, dy, dz = x_dim / 2.0, y_dim / 2.0, z_dim / 2.0
        tx, ty, tz = translation

        vertices = np.array(
            [
                [-dx + tx, -dy + ty, -dz + tz],
                [ dx + tx, -dy + ty, -dz + tz],
                [ dx + tx,  dy + ty, -dz + tz],
                [-dx + tx,  dy + ty, -dz + tz],
                [-dx + tx, -dy + ty,  dz + tz],
                [ dx + tx, -dy + ty,  dz + tz],
                [ dx + tx,  dy + ty,  dz + tz],
                [-dx + tx,  dy + ty,  dz + tz],
            ],
            dtype=np.float32,
        )

        # Poprawna orientacja ścianek (węzły przeciwnie do ruchu wskazówek zegara)
        faces = np.array(
            [
                [0, 2, 1], [0, 3, 2], # Dół (-Z)
                [4, 5, 6], [4, 6, 7], # Góra (+Z)
                [0, 1, 5], [0, 5, 4], # Przód (-Y)
                [2, 3, 7], [2, 7, 6], # Tył (+Y)
                [0, 4, 7], [0, 7, 3], # Lewo (-X)
                [1, 2, 6], [1, 6, 5], # Prawo (+X)
            ],
            dtype=np.uint32,
        )

        mesh_data = gl.MeshData(vertexes=vertices, faces=faces)
        # Shader "balloon" renderuje obiekty czytelnie niezależnie od słabego oświetlenia sceny
        return gl.GLMeshItem(
            meshdata=mesh_data, smooth=False, color=color, shader="balloon", glOptions=gl_options
        )
    
    def _add_box_outline(
        self,
        size: tuple[float, float, float],
        translation: tuple[float, float, float] = (0.0, 0.0, 0.0),
        color: tuple[float, float, float, float] = (0.5, 0.7, 0.9, 0.9),
        width: float = 1.5,
    ) -> None:
        """Tworzy 12 krawędzi obrysu dla prostopadłościanu w podanej pozycji."""
        dx, dy, dz = [s / 2.0 for s in size]
        tx, ty, tz = translation

        # 8 wierzchołków bryły
        v = np.array(
            [
                [-dx + tx, -dy + ty, -dz + tz],
                [dx + tx, -dy + ty, -dz + tz],
                [dx + tx, dy + ty, -dz + tz],
                [-dx + tx, dy + ty, -dz + tz],
                [-dx + tx, -dy + ty, dz + tz],
                [dx + tx, -dy + ty, dz + tz],
                [dx + tx, dy + ty, dz + tz],
                [-dx + tx, dy + ty, dz + tz],
            ],
            dtype=np.float32,
        )

        # Indeksy połączeń tworzące 12 krawędzi
        edges = [
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 0),  # Dolna podstawa
            (4, 5),
            (5, 6),
            (6, 7),
            (7, 4),  # Górna podstawa
            (0, 4),
            (1, 5),
            (2, 6),
            (3, 7),  # Pionowe krawędzie
        ]

        for p1, p2 in edges:
            line_item = gl.GLLinePlotItem(
                pos=np.array([v[p1], v[p2]], dtype=np.float32),
                color=color,
                width=width,
                glOptions="opaque",
            )
            self.view.add_foreground_item(line_item)
            self.satellite_items.append(line_item)


    def create_satellite(self, dimensions_m: tuple[float, float, float]) -> None:
        """Tworzy geometrię satelity (korpus + panele) przeliczoną z metrów na kilometry z obrysami."""
        self._clear_satellite()

        if not dimensions_m or len(dimensions_m) < 3:
            return

        a_m, b_m, h_m = dimensions_m
        a_km, b_km, h_km = a_m / 1000.0, b_m / 1000.0, h_m / 1000.0

        # 1. Korpus satelity (jaśniejszy odcień szarości/niebieskiego)
        body_item = self._create_box_mesh(
            (a_km, b_km, h_km),
            color=(0.15, 0.20, 0.28, 0.95),
            gl_options="opaque",
        )
        self.view.add_foreground_item(body_item)
        self.satellite_items.append(body_item)

        self._add_box_outline(
            size=(a_km, b_km, h_km),
            translation=(0.0, 0.0, 0.0),
            color=(0.5, 0.7, 0.9, 0.9),
            width=2.0,
        )

        # 2. Panele słoneczne (wyrazisty granat/niebieski)
        pv_color = (0.08, 0.15, 0.35, 0.98)
        t_km = max(0.00001, 0.008 / 1000.0)

        panels_config = [
            ((t_km, b_km * 0.85, h_km * 0.85), (a_km / 2.0 + t_km / 2.0, 0, 0)),
            ((t_km, b_km * 0.85, h_km * 0.85), (-a_km / 2.0 - t_km / 2.0, 0, 0)),
            ((a_km * 0.85, t_km, h_km * 0.85), (0, b_km / 2.0 + t_km / 2.0, 0)),
            ((a_km * 0.85, t_km, h_km * 0.85), (0, -b_km / 2.0 - t_km / 2.0, 0)),
            ((a_km * 0.85, b_km * 0.85, t_km), (0, 0, h_km / 2.0 + t_km / 2.0)),
            ((a_km * 0.85, b_km * 0.85, t_km), (0, 0, -h_km / 2.0 - t_km / 2.0)),
        ]

        for size, trans in panels_config:
            panel = self._create_box_mesh(size, translation=trans, color=pv_color)
            self.view.add_foreground_item(panel)
            self.satellite_items.append(panel)
        self.view.update()

    def update_satellite_state(
        self,
        position_km: tuple[float, float, float] | np.ndarray,
        quat_orientation: tuple[float, float, float, float],
        track_camera: bool = True,
    ) -> None:

        if not self.satellite_items:
            return

        if not self._axis_items:
            self._draw_rgb_body_axes()
            self.show_body_frame(False)

        x, y, z = position_km

        # ==========================================================
        # QUATERNION -> ROTATION MATRIX
        # Zakładamy kolejność: (qw, qx, qy, qz)
        # ==========================================================

        qw, qx, qy, qz = map(float, quat_orientation)

        # Normalizacja - zabezpieczenie przed niewielkimi błędami numerycznymi
        norm = math.sqrt(
            qw * qw +
            qx * qx +
            qy * qy +
            qz * qz
        )

        if norm < 1e-12:
            return

        qw /= norm
        qx /= norm
        qy /= norm
        qz /= norm

        R = np.array([
            [
                1 - 2 * (qy * qy + qz * qz),
                2 * (qx * qy - qz * qw),
                2 * (qx * qz + qy * qw),
            ],
            [
                2 * (qx * qy + qz * qw),
                1 - 2 * (qx * qx + qz * qz),
                2 * (qy * qz - qx * qw),
            ],
            [
                2 * (qx * qz - qy * qw),
                2 * (qy * qz + qx * qw),
                1 - 2 * (qx * qx + qy * qy),
            ],
        ], dtype=np.float32)

        # ==========================================================
        # ROTATION MATRIX -> QMatrix4x4
        # ==========================================================

        transform = QMatrix4x4(
            float(R[0, 0]), float(R[0, 1]), float(R[0, 2]), 0.0,
            float(R[1, 0]), float(R[1, 1]), float(R[1, 2]), 0.0,
            float(R[2, 0]), float(R[2, 1]), float(R[2, 2]), 0.0,
            0.0,            0.0,            0.0,            1.0,
        )

        # ==========================================================
        # APLIKACJA ROTACJI
        # ==========================================================

        for item in self.view.foreground_items:
            item.setTransform(transform)

        for axis in self._axis_items:
            axis.setTransform(transform)

        # ==========================================================
        # POZYCJA SATELITY
        # ==========================================================

        if self.view:
            self.view.set_satellite_position(x, y, z)
            self.view.update()

    def _clear_satellite(self) -> None:
        for item in self.satellite_items:
            self.view.removeItem(item)
        self.satellite_items.clear()


