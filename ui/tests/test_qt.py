import sys
import pyqtgraph as pg
import pyqtgraph.opengl as gl
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import numpy as np

class OrbitViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Satellite Orbit Simulator 3D")
        self.resize(800, 600)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Create OpenGL View Widget for 3D visualization
        self.view = gl.GLViewWidget()
        self.layout.addWidget(self.view)

        # Add grid and axes for reference
        gx = gl.GLGridItem()
        self.view.addItem(gx)
        
        # Placeholder for satellite orbit (e.g., a circle)
        self.plot_orbit()

    def plot_orbit(self):
        # Example: Simple circle (points in 3D)
        theta = np.linspace(0, 2 * np.pi, 100)
        x = 5 * np.cos(theta)
        y = 5 * np.sin(theta)
        z = np.zeros_like(theta)
        
        points = np.vstack([x, y, z]).transpose()
        
        # Create line plot
        plt = gl.GLLinePlotItem(pos=points, color=(1, 1, 0, 1), width=2)
        self.view.addItem(plt)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = OrbitViewer()
    window.show()
    sys.exit(app.exec())