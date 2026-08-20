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

        self.view = gl.GLViewWidget()
        self.view.setProjection = self._custom_set_projection

        self.earth = OrbitSceneHelper.create_earth(rows=1000, cols=1000)

        self.view.addItem(self.earth)
        self.view.opts["glOptions"] = "opaque"

        self.view.setCameraPosition(distance=0.005, azimuth=30, elevation=20)

        self._set_camera_limits(0.005, 0.005)
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
        
        if hasattr(self, 'ecef_vectors'):
            for vector in self.ecef_vectors:
                vector.resetTransform()
                vector.rotate(angle_deg, 0, 0, 1)
            for label in self.ecef_labels:
                label.resetTransform()
                label.rotate(angle_deg, 0, 0, 1)
        
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
            self.view.addItem(line)
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
        vertices = np.array(
            [
                [-x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
                [ x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
                [ x_dim / 2.0 + translation[0],  y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
                [-x_dim / 2.0 + translation[0],  y_dim / 2.0 + translation[1], -z_dim / 2.0 + translation[2]],
                [-x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1],  z_dim / 2.0 + translation[2]],
                [ x_dim / 2.0 + translation[0], -y_dim / 2.0 + translation[1],  z_dim / 2.0 + translation[2]],
                [ x_dim / 2.0 + translation[0],  y_dim / 2.0 + translation[1],  z_dim / 2.0 + translation[2]],
                [-x_dim / 2.0 + translation[0],  y_dim / 2.0 + translation[1],  z_dim / 2.0 + translation[2]],
            ],
            dtype=np.float32,
        )

        faces = np.array(
            [
                [0, 1, 2], [0, 2, 3],
                [4, 6, 5], [4, 7, 6],
                [0, 4, 5], [0, 5, 1],
                [1, 5, 6], [1, 6, 2],
                [2, 6, 7], [2, 7, 3],
                [3, 7, 4], [3, 4, 0],
            ],
            dtype=np.uint32,
        )

        mesh_data = gl.MeshData(vertexes=vertices, faces=faces)
        return gl.GLMeshItem(
            meshdata=mesh_data, smooth=True, color=color, shader="shaded", glOptions=gl_options
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
            self.view.addItem(line_item)
            self.satellite_items.append(line_item)


    def create_satellite(self, dimensions_m: tuple[float, float, float]) -> None:
        """Tworzy geometrię satelity (korpus + panele) przeliczoną z metrów na kilometry z obrysami."""
        self._clear_satellite()

        if not dimensions_m or len(dimensions_m) < 3:
            return

        a_m, b_m, h_m = dimensions_m
        # Konwersja skali z metrów na kilometry
        a_km, b_km, h_km = a_m / 1000.0, b_m / 1000.0, h_m / 1000.0

        # 1. Korpus satelity + Obrys
        body_item = self._create_box_mesh(
            (a_km, b_km, h_km),
            color=(0.15, 0.20, 0.28, 0.95),
            gl_options="opaque",
        )
        self.view.addItem(body_item)
        self.satellite_items.append(body_item)

        self._add_box_outline(
            size=(a_km, b_km, h_km),
            translation=(0.0, 0.0, 0.0),
            color=(0.5, 0.7, 0.9, 0.9),
            width=1.5,
        )

        # 2. Panele słoneczne
        pv_color = (0.08, 0.15, 0.35, 0.98)
        t_km = 0.008 / 1000.0  # Grubość panelu w km (~8 mm)

        panels_config = [
            (
                (t_km, b_km * 0.85, h_km * 0.85),
                (a_km / 2.0 + t_km / 2.0, 0, 0),
            ),
            (
                (t_km, b_km * 0.85, h_km * 0.85),
                (-a_km / 2.0 - t_km / 2.0, 0, 0),
            ),
            (
                (a_km * 0.85, t_km, h_km * 0.85),
                (0, b_km / 2.0 + t_km / 2.0, 0),
            ),
            (
                (a_km * 0.85, t_km, h_km * 0.85),
                (0, -b_km / 2.0 - t_km / 2.0, 0),
            ),
            (
                (a_km * 0.85, b_km * 0.85, t_km),
                (0, 0, h_km / 2.0 + t_km / 2.0),
            ),
            (
                (a_km * 0.85, b_km * 0.85, t_km),
                (0, 0, -h_km / 2.0 - t_km / 2.0),
            ),
        ]

        for size, trans in panels_config:
            panel = self._create_box_mesh(size, translation=trans, color=pv_color)
            self.view.addItem(panel)
            self.satellite_items.append(panel)

    def update_satellite_state(
        self,
        position_km: tuple[float, float, float] | np.ndarray,
        euler_deg:tuple[float, float, float],
        track_camera: bool = True,
    ) -> None:

        if not self.satellite_items:
            return

        if not self._axis_items:
            self._draw_rgb_body_axes()

        x, y, z = position_km
        roll, pitch, yaw = euler_deg

        transform = QMatrix4x4()
        transform.translate(float(x), float(y), float(z))

        transform.rotate(float(yaw),   0, 0, 1)
        transform.rotate(float(pitch), 0, 1, 0)
        transform.rotate(float(roll),  1, 0, 0)

        # Satelita
        for item in self.satellite_items:
            item.setTransform(transform)

        # Osie ciała
        for axis in self._axis_items:
            axis.setTransform(transform)

        if track_camera and self.view:
            target_pos = QVector3D(float(x), float(y), float(z))
            self.view.setCameraPosition(pos=target_pos)
            self.view.update()

    def _clear_satellite(self) -> None:
        for item in self.satellite_items:
            self.view.removeItem(item)
        self.satellite_items.clear()

    def _custom_set_projection(self, region=None, viewport=None) -> None:
        """
        Własna projekcja dla sceny orbitalnej.

        Kamera:
            center   -> pozycja satelity
            distance -> odległość kamery od satelity

        Jednostką sceny jest kilometr.

        Projekcja zachowuje normalne zachowanie GLViewWidget,
        ale rozszerza zakres far plane tak, aby jednocześnie można było
        obserwować satelitę oraz Ziemię znajdującą się tysiące kilometrów
        od centrum widoku.
        """

        self.view.makeCurrent()

        # ------------------------------------------------------------
        # Viewport
        # ------------------------------------------------------------

        if viewport is None:
            viewport = self.view.getViewport()

        if region is None:
            region = viewport

        x0, y0, w, h = viewport

        w = max(1, int(w))
        h = max(1, int(h))

        # ------------------------------------------------------------
        # Parametry kamery
        # ------------------------------------------------------------

        distance = float(
            self.view.opts.get("distance", 1.0)
        )

        distance = max(distance, 1e-9)

        fov = float(
            self.view.opts.get("fov", 60.0)
        )

        # ------------------------------------------------------------
        # Zakres sceny
        # ------------------------------------------------------------
        #
        # Ziemia:
        #
        #   R = 6371 km
        #
        # GEO:
        #
        #   r = 42164 km
        #
        # Dodajemy margines, żeby projekcja nie była obcinana
        # dla dalszych obiektów.
        #

        EARTH_RADIUS = 6371.0
        MAX_ORBIT_RADIUS = 50000.0
        SCENE_MARGIN = 10000.0

        # ------------------------------------------------------------
        # Near plane
        # ------------------------------------------------------------
        #
        # Near jest zależny od odległości kamery od satelity,
        # a NIE odległości satelity od środka Ziemi.
        #
        # Przykład:
        #
        # distance = 0.004 km = 4 m
        #
        # near = 0.00004 km = 4 cm
        #

        z_near = max(
            1e-6,
            distance * 0.01
        )

        # Nie pozwalamy, aby near stał się za duży.
        z_near = min(
            z_near,
            0.1
        )

        # ------------------------------------------------------------
        # Far plane
        # ------------------------------------------------------------
        #
        # Kamera jest oddalona od centrum tylko o "distance".
        #
        # Najdalszy interesujący obiekt znajduje się mniej więcej
        # w odległości:
        #
        #     center_radius + scene radius
        #
        # od kamery.
        #

        center = self.view.opts["center"]

        center_radius = math.sqrt(
            float(center.x()) ** 2
            + float(center.y()) ** 2
            + float(center.z()) ** 2
        )

        # Promień sceny obejmujący Ziemię i orbity.
        scene_radius = max(
            EARTH_RADIUS,
            MAX_ORBIT_RADIUS
        )

        z_far = (
            center_radius
            + scene_radius
            + SCENE_MARGIN
            + distance
        )

        z_far = max(
            z_far,
            10000.0
        )

        # ------------------------------------------------------------
        # Ochrona depth buffera
        # ------------------------------------------------------------

        MAX_DEPTH_RATIO = 1e8

        z_near = max(
            z_near,
            z_far / MAX_DEPTH_RATIO
        )

        # ------------------------------------------------------------
        # Frustum
        # ------------------------------------------------------------
        #
        # Używamy dokładnie tego samego mechanizmu,
        # którego używa GLViewWidget.
        #
        # To ważne — nie używamy tutaj perspective() + glMultMatrixf().
        #

        r = z_near * math.tan(
            0.5 * math.radians(fov)
        )

        t = r * h / w

        left = r * (
            ((region[0] - x0) * (2.0 / w)) - 1.0
        )

        right = r * (
            ((region[0] + region[2] - x0) * (2.0 / w)) - 1.0
        )

        bottom = t * (
            ((region[1] - y0) * (2.0 / h)) - 1.0
        )

        top = t * (
            ((region[1] + region[3] - y0) * (2.0 / h)) - 1.0
        )

        projection = QMatrix4x4()

        projection.frustum(
            left,
            right,
            bottom,
            top,
            z_near,
            z_far
        )

        # ------------------------------------------------------------
        # PyQtGraph
        # ------------------------------------------------------------

        self.view._projectionStack.clear()
        self.view._projectionStack.append(projection)