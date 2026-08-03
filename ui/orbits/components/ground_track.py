import os
from PIL import Image
import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget
from utils.constants import CONSTANTS


class GroundTrackWindow(QWidget):

    def __init__(
        self, eci_positions, times=None, initial_gmst=None, parent=None
    ):
        """
        :param eci_positions: list or np.array of [x, y, z] positions in km (single orbit)
        :param times: list or np.array of time steps in seconds.
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Satellite Ground Track Analysis")
        self.resize(950, 550)
        self.setMinimumSize(600, 400)

        self.OMEGA_E = CONSTANTS["omega_E"]  # Earth's rotation speed (rad/s)
        self.initial_gmst = (
            initial_gmst if initial_gmst is not None else 0.0
        )
        self.map_item = None

        # Zapamiętanie surowych danych dla pojedynczej orbity
        self.raw_eci = (
            np.array(eci_positions) if eci_positions is not None else None
        )

        if times is None and self.raw_eci is not None:
            self.raw_times = (
                np.arange(len(self.raw_eci)) * 10.0
            )  # domyślnie dt = 10s
        else:
            self.raw_times = np.array(times) if times is not None else None

        # Obliczenie okresu orbitalnego T z dostarczonych punktów
        if self.raw_times is not None and len(self.raw_times) > 1:
            self.orbit_period = float(self.raw_times[-1] - self.raw_times[0])
            if self.orbit_period <= 0:
                self.orbit_period = 5400.0  # fallback ~90 min
        else:
            self.orbit_period = 5400.0

        # Wyznaczenie granicy liczby obiegów w ciągu 24h (86400 s)
        self.max_orbits_24h = int(np.clip(86400.0 / self.orbit_period, 1, 50))

        self._init_ui()
        self._load_map_background("assets/graphics/earth_surface.jpg")
        self.generate_track(num_orbits=1)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        

        # --- PANEL KONTROLNY (GÓRNY PAS) ---
        ctrl_layout = QHBoxLayout()

        

        lbl_spin = QLabel("Number of Orbits:")
        lbl_spin.setStyleSheet(
            "color: #a9b7c6; font-weight: bold; font-size: 12px;"
        )

        self.spin_orbits = QSpinBox()
        self.spin_orbits.setRange(1, self.max_orbits_24h)
        self.spin_orbits.setValue(1)

        self.spin_orbits.valueChanged.connect(self._on_orbits_changed)

        lbl_limit_info = QLabel(f"(Within 24 hours at most: {self.max_orbits_24h})")
        lbl_limit_info.setStyleSheet("color: #7a7a7a; font-size: 11px; background-color: #2c2c2c;")

        ctrl_layout.addWidget(lbl_spin)
        ctrl_layout.addWidget(self.spin_orbits)
        ctrl_layout.addWidget(lbl_limit_info)
        ctrl_layout.addStretch()

        layout.addLayout(ctrl_layout)

        # --- WYKRES MAPY (PyQtGraph) ---
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#1e1e1e")
        self.plot_widget.setXRange(-180, 180, padding=0)
        self.plot_widget.setYRange(-90, 90, padding=0)
        self.plot_widget.setMouseEnabled(x=False, y=False)

        view_box = self.plot_widget.getViewBox()
        view_box.setLimits(xMin=-180, xMax=180, yMin=-90, yMax=90)

        self.plot_widget.setLabel(
            "bottom", "Longitude", units="°"
        )
        self.plot_widget.setLabel(
            "left", "Latitude", units="°"
        )
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)

        styles = {"color": "#a9b7c6", "font-size": "11px"}
        self.plot_widget.getAxis("bottom").setLabel(**styles)
        self.plot_widget.getAxis("left").setLabel(**styles)

        layout.addWidget(self.plot_widget)

        self.lbl_info = QLabel(
            "Ground Track of the satellite"
        )
        self.lbl_info.setStyleSheet("color: #7a7a7a; font-size: 11px;")
        layout.addWidget(self.lbl_info)
        

    def _load_map_background(self, image_path: str):
        if not os.path.exists(image_path):
            print(f"Error: File {image_path} doesn't exist.")
            return

        try:
            img = Image.open(image_path).convert("RGB")
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            img_data = np.array(img)

            self.map_item = pg.ImageItem(img_data, axisOrder="row-major")
            self.map_item.setRect(QRectF(-180, -90, 360, 180))
            self.map_item.setZValue(-100)
            self.plot_widget.addItem(self.map_item)
        except Exception as e:
            print(f"Błąd podczas ładowania mapy tła: {e}")

    def _on_orbits_changed(self, value: int):
        self.generate_track(num_orbits=value)

    def generate_track(self, num_orbits=1):
        if self.raw_eci is None or len(self.raw_eci) == 0:
            return

        self.plot_widget.clear()

        if self.map_item is not None:
            self.plot_widget.addItem(self.map_item)

        n_points = len(self.raw_eci)
        eci_ext = np.tile(self.raw_eci, (num_orbits, 1))

        time_offsets = np.repeat(
            np.arange(num_orbits) * self.orbit_period, n_points
        )
        times_ext = np.tile(self.raw_times, num_orbits) + time_offsets

        x = eci_ext[:, 0]
        y = eci_ext[:, 1]
        z = eci_ext[:, 2]

        r_xy = np.sqrt(x**2 + y**2)
        valid_mask = r_xy >= 1e-6

        if not np.any(valid_mask):
            return

        x, y, z, r_xy, t = (
            x[valid_mask],
            y[valid_mask],
            z[valid_mask],
            r_xy[valid_mask],
            times_ext[valid_mask],
        )

        lat = np.degrees(np.arctan2(z, r_xy))
        lon_inertial = np.degrees(np.arctan2(y, x))

        earth_rotation = self.initial_gmst + np.degrees(self.OMEGA_E * t)
        lon_geo = (lon_inertial - earth_rotation + 180.0) % 360.0 - 180.0

        diffs = np.abs(np.diff(lon_geo))
        split_indices = np.where(diffs > 180.0)[0] + 1

        lon_segments = np.split(lon_geo, split_indices)
        lat_segments = np.split(lat, split_indices)

        track_pen = pg.mkPen(
            color="#ff9f29", width=2.0, style=Qt.PenStyle.SolidLine
        )
        for lons, lats in zip(lon_segments, lat_segments):
            if len(lons) > 1:
                self.plot_widget.plot(lons, lats, pen=track_pen)

        if len(lon_geo) > 0:
            self.plot_widget.plot(
                [lon_geo[0]],
                [lat[0]],
                pen=None,
                symbol="o",
                symbolSize=8,
                symbolBrush="g",
            )
            self.plot_widget.plot(
                [lon_geo[-1]],
                [lat[-1]],
                pen=None,
                symbol="x",
                symbolSize=10,
                symbolBrush="r",
            )