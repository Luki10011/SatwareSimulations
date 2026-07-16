from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
from utils.constants import CONSTANTS

class GroundTrackWindow(QWidget):
    def __init__(self, eci_positions, times=None, parent=None):
        """
        :param eci_positions: list or np.array of [x, y, z] positions in km
        :param times: list or np.array of time steps in seconds. If None, assumes dt=10s
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Satellite Ground Track Analysis")
        self.resize(900, 500)
        self.setMinimumSize(600, 350)
        
        self.OMEGA_E = CONSTANTS["omega_E"]  # Earth's rotation speed (rad/s)
        
        self._init_ui()
        self.generate_track(eci_positions, times)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Configure pyqtgraph plot for map projection
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('#1e1e1e')
        self.plot_widget.setXRange(-180, 180, padding=0)
        self.plot_widget.setYRange(-90, 90, padding=0)

        
        self.plot_widget.setMouseEnabled(x=False, y=False)
        
        self.plot_widget.getPlotItem().setMenuEnabled(False)
        
        view_box = self.plot_widget.getViewBox()
        view_box.setLimits(xMin=-180, xMax=180, yMin=-90, yMax=90)
        
        # Labels and Grid
        self.plot_widget.setLabel('bottom', 'Longitude', units='°')
        self.plot_widget.setLabel('left', 'Latitude', units='°')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        
        # Style axes
        styles = {'color': '#a9b7c6', 'font-size': '11px'}
        self.plot_widget.getAxis('bottom').setLabel(**styles)
        self.plot_widget.getAxis('left').setLabel(**styles)
        
        layout.addWidget(self.plot_widget)
        
        # Info footer
        self.lbl_info = QLabel("Orbit ground track segmented relative to Earth's rotation.")
        self.lbl_info.setStyleSheet("color: #7a7a7a; font-size: 11px;")
        layout.addWidget(self.lbl_info)

    def generate_track(self, eci_positions, times=None):
        if eci_positions is None or len(eci_positions) == 0:
            return
            
        self.plot_widget.clear()
        
        longitudes = []
        latitudes = []
        
        # Fallback for time vector if not explicitly provided
        if times is None:
            times = np.arange(len(eci_positions)) * 10.0  # default dt = 10s
            
        for i, pos in enumerate(eci_positions):
            t = times[i]
            x, y, z = pos[0], pos[1], pos[2]
            
            r_xy = np.sqrt(x**2 + y**2)
            if r_xy < 1e-6:
                continue
                
            # 1. Calculate Latitude
            lat = np.degrees(np.arctan2(z, r_xy))
            
            # 2. Calculate Longitude in ECI and transform to ECEF (sub-satellite point)
            lon_interial = np.degrees(np.arctan2(y, x))
            lon_geo = lon_interial - np.degrees(self.OMEGA_E * t)
            
            # 3. Normalize longitude to [-180, 180]
            lon_geo = (lon_geo + 180) % 360 - 180
            
            longitudes.append(lon_geo)
            latitudes.append(lat)
            
        # 4. Segment tracking data to prevent ugly wraparound lines at +/-180 longitude
        segments = []
        curr_lon, curr_lat = [longitudes[0]], [latitudes[0]]
        
        for i in range(1, len(longitudes)):
            # If the step jumps drastically, we crossed the map border
            if abs(longitudes[i] - longitudes[i-1]) > 180.0:
                segments.append((curr_lon, curr_lat))
                curr_lon = []
                curr_lat = []
            curr_lon.append(longitudes[i])
            curr_lat.append(latitudes[i])
            
        if curr_lon:
            segments.append((curr_lon, curr_lat))
            
        # 5. Plot each independent segment
        track_pen = pg.mkPen(color='#ff9f29', width=2.5, style=Qt.PenStyle.SolidLine)
        for lon_seg, lat_seg in segments:
            self.plot_widget.plot(lon_seg, lat_seg, pen=track_pen)
            
        # 6. Highlight Start (Green) and Current/End Position (Red)
        if len(longitudes) > 0:
            self.plot_widget.plot([longitudes[0]], [latitudes[0]], pen=None, symbol='o', symbolSize=8, symbolBrush='g')
            self.plot_widget.plot([longitudes[-1]], [latitudes[-1]], pen=None, symbol='x', symbolSize=10, symbolBrush='r')