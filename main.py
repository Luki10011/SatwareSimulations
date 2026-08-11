import pyfiglet
from utils.welcome import welcome
import sys
from PyQt6.QtWidgets import QApplication
from ui.main_screen.main_window import MainWindow

PROJECT_NAME = "SatWare Simullations"
PROJECT_VERSION = "0.1.0"


def main() -> None:
    welcome(PROJECT_NAME, PROJECT_VERSION)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()