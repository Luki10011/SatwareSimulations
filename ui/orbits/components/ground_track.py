from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QRectF
import pyqtgraph as pg
import numpy as np
from PIL import Image
import os
from utils.constants import CONSTANTS

class GroundTrackWindow(QWidget):
    def __init__(self, eci_positions, times=None, initial_gmst=None, parent=None):
        """
        :param eci_positions: list or np.array of [x, y, z] positions in km
        :param times: list or np.array of time steps in seconds. If None, assumes dt=10s
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Satellite Ground Track Analysis")
        self.resize(900, 500)
        self.setMinimumSize(600, 350)
        
        self.OMEGA_E = CONSTANTS["omega_E"]  # Earth's rotation speed (rad/s)
        self.initial_gmst = initial_gmst
        self.map_item = None
        
        self._init_ui()
        self._load_map_background("assets/graphics/earth_surface.jpg") 
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
        # self.plot_widget.getPlotItem().setMenuEnabled(False)
        
        
        view_box = self.plot_widget.getViewBox()
        view_box.setLimits(xMin=-180, xMax=180, yMin=-90, yMax=90)
        
        self.plot_widget.setLabel('bottom', 'Longitude', units='°')
        self.plot_widget.setLabel('left', 'Latitude', units='°')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        
        styles = {'color': '#a9b7c6', 'font-size': '11px'}
        self.plot_widget.getAxis('bottom').setLabel(**styles)
        self.plot_widget.getAxis('left').setLabel(**styles)
        
        layout.addWidget(self.plot_widget)
        
        self.lbl_info = QLabel("Orbit ground track segmented relative to Earth's rotation.")
        self.lbl_info.setStyleSheet("color: #7a7a7a; font-size: 11px;")
        layout.addWidget(self.lbl_info)

    def _load_map_background(self, image_path: str):
        if not os.path.exists(image_path):
            print(f"Error: File {image_path} doesn't exist. Ignoring .")
            return

        try:
            img = Image.open(image_path).convert("RGB")
            
            img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            img_data = np.array(img)

            self.map_item = pg.ImageItem(img_data, axisOrder='row-major')
            
            self.map_item.setRect(QRectF(-180, -90, 360, 180))
            
            self.map_item.setZValue(-100)
            self.plot_widget.addItem(self.map_item)
        except Exception as e:
            print(f"Błąd podczas ładowania mapy tła: {e}")

    def generate_track(self, eci_positions, times=None):
        if eci_positions is None or len(eci_positions) == 0:
            return
            
        self.plot_widget.clear()
        
        # Ponowne dodanie tła mapy po wyczyszczeniu widoku
        if self.map_item is not None:
            self.plot_widget.addItem(self.map_item)
        
        longitudes = []
        latitudes = []
        
        if times is None:
            times = np.arange(len(eci_positions))   
            
        gmst_start = self.initial_gmst if self.initial_gmst is not None else 0.0
        
        for i, pos in enumerate(eci_positions):
            t = times[i]
            x, y, z = pos[0], pos[1], pos[2]
            
            r_xy = np.sqrt(x**2 + y**2)
            if r_xy < 1e-6:
                continue
                
            lat = np.degrees(np.arctan2(z, r_xy))
            lon_inertial = np.degrees(np.arctan2(y, x))
            
            earth_rotation = gmst_start + np.degrees(self.OMEGA_E * t)
            lon_geo = lon_inertial - earth_rotation
            
            lon_geo = (lon_geo + 180) % 360 - 180
            
            longitudes.append(lon_geo)
            latitudes.append(lat)
            
        if not longitudes:
            return
            
        segments = []
        curr_lon, curr_lat = [longitudes[0]], [latitudes[0]]
        
        for i in range(1, len(longitudes)):
            # Segmentacja przy przekraczaniu krawędzi mapy (+180/-180 deg)
            if abs(longitudes[i] - longitudes[i-1]) > 180.0:
                segments.append((curr_lon, curr_lat))
                curr_lon = []
                curr_lat = []
            curr_lon.append(longitudes[i])
            curr_lat.append(latitudes[i])
            
        if curr_lon:
            segments.append((curr_lon, curr_lat))
            
        track_pen = pg.mkPen(color='#ff9f29', width=2.5, style=Qt.PenStyle.SolidLine)
        for lon_seg, lat_seg in segments:
            self.plot_widget.plot(lon_seg, lat_seg, pen=track_pen)
            
        if len(longitudes) > 0:
            # Punkt startowy (zielony) i końcowy (czerwony)
            self.plot_widget.plot([longitudes[0]], [latitudes[0]], pen=None, symbol='o', symbolSize=8, symbolBrush='g')
            self.plot_widget.plot([longitudes[-1]], [latitudes[-1]], pen=None, symbol='x', symbolSize=10, symbolBrush='r')