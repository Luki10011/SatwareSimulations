import pyfiglet
from utils.welcome import welcome
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_screen.main_window import MainWindow
import pyqtgraph as pg

PROJECT_NAME = "SatWare Simullations"
PROJECT_VERSION = "0.1.0"


def main() -> None:
    welcome(PROJECT_NAME, PROJECT_VERSION)
    pg.setConfigOptions(
        useOpenGL=True,  # Przenosi renderowanie linii na GPU
        antialias=False,  # Drastyczny wzrost FPS (wyłącza wygładzanie linii)
        enableExperimental=True,
    )
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()