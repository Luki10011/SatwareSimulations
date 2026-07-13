import sys
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox, QWidget, QVBoxLayout, 
                             QLabel, QStackedWidget, QPushButton, QStyle)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QAction

from ui.main_screen.components.predefined_orbit import PredefinedOrbitDialog
from ui.main_screen.components.welcome_screen import MainScreenWelcome
from ui.orbits.orbit_designer import OrbitDesigner  
import os
from utils.constants import ORBITS_DATA


class MainWindow(QMainWindow):
    """Główne okno aplikacji zarządzające menu i przełączaniem widoków."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orbit Dynamic Analyzer - Praca Magisterska")
        self.resize(1280, 720) 
        
        # self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        self.load_stylesheet("ui/utils/styles.qss")
        
        self.central_stacked_widget = QStackedWidget()
        self.setCentralWidget(self.central_stacked_widget)
        
        self.init_screens()
        
        self.init_menu_bar()

    def load_stylesheet(self, filename):
        """Reads a QSS stylesheet from a file and applies it to the application."""
        if os.path.exists(filename):
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Error while loading stylesheet: {e}")
                # Awaryjny styl podstawowy w razie błędu odczytu pliku
                self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        else:
            print(f"Warning: File not found {filename}. Applying default style.")
            self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

    def init_screens(self):
        """Creates and registers screens within the QStackedWidget."""
        self.welcome_screen = MainScreenWelcome()
        self.central_stacked_widget.addWidget(self.welcome_screen)
  
        self.orbit_designer_screen = OrbitDesigner()
        
        self.central_stacked_widget.addWidget(self.orbit_designer_screen)
        
        self.central_stacked_widget.setCurrentIndex(0)

    def init_menu_bar(self):
        """Configures the menu bar at the top of the screen."""
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
                font-size: 10pt;
            }
            QMenuBar::item:selected {
                background-color: #3e3e3e;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3e3e3e;
            }
            QMenu::item:selected {
                background-color: #e81123;
            }
            QMenu::item {
                margin: 2px 4px;
                font-size: 10pt;
            }
        """)
        
        file_menu = menu_bar.addMenu("&System")
        
        home_action = QAction("Start Screen", self)
        home_action.triggered.connect(self.show_welcome_screen)
        file_menu.addAction(home_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("&Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close_application)
        file_menu.addAction(exit_action)
        
        orbit_tools_menu = menu_bar.addMenu("&Orbit Tools")
        
        designer_action = QAction("&Create new Orbit", self)
        designer_action.triggered.connect(self.show_orbit_designer)
        orbit_tools_menu.addAction(designer_action)

        load_orbit_action = QAction("&Load Orbit from File", self)
        load_orbit_action.triggered.connect(self.load_orbit)
        orbit_tools_menu.addAction(load_orbit_action)

        load_predefined_orbit_action = QAction("&Load Predefined Orbit type", self)
        load_predefined_orbit_action.triggered.connect(self.load_predefined_orbit)
        orbit_tools_menu.addAction(load_predefined_orbit_action)

        satellite_menu = menu_bar.addMenu("&Satellite Tools")
        satellite_action = QAction("&Create new Satellite Configuration", self)
        satellite_menu.addAction(satellite_action)

        load_satellite_action = QAction("&Load Satellite Configuration from File", self)
        satellite_menu.addAction(load_satellite_action)

    def close_application(self):
        reply = QMessageBox.question(self, "Exit Application", "You are exiting the application. Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
        else:
            return

    def load_predefined_orbit(self):
        """ Loads a predefined orbit from the ORBITS_DATA and passes it to the orbit designer screen. """
        dialog = PredefinedOrbitDialog(ORBITS_DATA, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            orbit_data = dialog.get_selected_orbit_data()
            
            if orbit_data:
                elements = orbit_data["elements"]
                
                self.orbit_designer_screen.load_predefined_orbit(elements)

                self.central_stacked_widget.setCurrentIndex(1)

    def show_welcome_screen(self):
        """Switches to welcome screen view."""
        if self.central_stacked_widget.currentIndex() != 0:
            reply = QMessageBox.question(self, "Returning to Welcome Screen", "You are returning to the welcome screen. Any unsaved changes will be lost.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.orbit_designer_screen.reset_designer()
            else:
                return
        
        self.central_stacked_widget.setCurrentIndex(0)

    def show_orbit_designer(self):
        """Switches to orbit designer view."""
        if self.central_stacked_widget.currentIndex() == 1:
            reply = QMessageBox.question(self, "Orbit Designer", "You are returning to the orbit designer. Any unsaved changes will be lost.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.orbit_designer_screen.reset_designer()
            else:
                return
        self.central_stacked_widget.setCurrentIndex(1)

    def load_orbit(self):
        """Opens a file dialog to load orbit data from a JSON file and passes it to the orbit designer screen."""
        self.orbit_designer_screen.destroy()
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Orbit Data",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            self.orbit_designer_screen.load_orbit_from_file(file_path)
            self.central_stacked_widget.setCurrentIndex(1)

        return

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Ustawienie systemowego stylu dla lepszego renderowania widgetów Qt
    # app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
