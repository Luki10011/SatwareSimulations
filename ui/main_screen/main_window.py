import sys
import os
from PyQt6.QtWidgets import (QApplication, QDialog, QFileDialog, QMainWindow, QMessageBox, QWidget, QVBoxLayout, 
                             QLabel, QStackedWidget, QPushButton, QStyle, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QAction, QMatrix4x4

from ui.main_screen.components.predefined_orbit import PredefinedOrbitDialog
from ui.main_screen.components.welcome_screen import MainScreenWelcome
from ui.orbits.orbit_designer import OrbitDesigner  
from ui.main_screen.components.loading_screen import LoadingScreen
from utils.constants import ORBITS_DATA



class MainWindow(QMainWindow):
    """Główne okno aplikacji zarządzające menu i przełączaniem widoków."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Orbit Dynamic Analyzer - Praca Magisterska")
        self.resize(1280, 720) 
        
        self.load_stylesheet("ui/utils/styles.qss")
        
        self._is_switching = False 
        
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
                self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")
        else:
            print(f"Warning: File not found {filename}. Applying default style.")
            self.setStyleSheet("background-color: #1e1e1e; color: #ffffff;")

    def init_screens(self):
        """Tworzy i rejestruje ekrany wewnątrz QStackedWidget od razu przy starcie."""
        # Index 0: Welcome screen
        self.welcome_screen = MainScreenWelcome()
        self.welcome_screen.orbit_item.connectClick(self.show_orbit_designer)
        self.welcome_screen.satellite_item.connectClick(lambda : print("Satellite item clicked"))
        self.welcome_screen.experiment_item.connectClick(lambda : print("Experiment item clicked"))
        self.central_stacked_widget.addWidget(self.welcome_screen)
  
        # Index 1: Loading screen
        self.loading_screen = LoadingScreen()
        self.central_stacked_widget.addWidget(self.loading_screen)
        
        # Index 2: Orbit Designer screen
        self.orbit_designer_screen = OrbitDesigner()
        self.central_stacked_widget.addWidget(self.orbit_designer_screen)
        
        self.central_stacked_widget.setCurrentIndex(0)

    def init_menu_bar(self):
        """Configures the menu bar at the top of the screen."""
        menu_bar = self.menuBar()
       
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


        experiment_menu = menu_bar.addMenu("Experimnets")

        create_new_experiment_action = QAction("&Create new Experiment", self)
        load_experment_from_file = QAction("&Load Experiment from File", self)

        experiment_menu.addAction(create_new_experiment_action)
        experiment_menu.addAction(load_experment_from_file)

        
    def close_application(self):
        if self._is_switching:
            return
        reply = QMessageBox.question(self, "Exit Application", "You are exiting the application. Are you sure?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.close()

    def _run_safe_transition(self, heavy_action=None):
        """Safely transitions to another screen, masking UI freezes."""
        if self._is_switching:
            return
        self._is_switching = True
        
        self.central_stacked_widget.setCurrentIndex(1)
        

        QTimer.singleShot(150, lambda: self._complete_transition(heavy_action))

    def _complete_transition(self, heavy_action):
        try:
            if heavy_action:
                heavy_action()
            # OrbitDesigner index
            self.central_stacked_widget.setCurrentIndex(2)
        finally:
            self._is_switching = False

    def show_welcome_screen(self):
        """Switches to welcome screen view."""
        if self._is_switching:
            return
            
        if self.central_stacked_widget.currentIndex() == 2:
            reply = QMessageBox.question(self, "Returning to Welcome Screen", "You are returning to the welcome screen. Any unsaved changes will be lost.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.orbit_designer_screen.reset_designer()
            else:
                return
        
        self.central_stacked_widget.setCurrentIndex(0)

    def show_orbit_designer(self):
        """Switches to orbit designer view using the transition effect."""
        if self._is_switching:
            return

        if self.central_stacked_widget.currentIndex() == 2:
            reply = QMessageBox.question(self, "Orbit Designer", "You are returning to the orbit designer. Any unsaved changes will be lost.", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.orbit_designer_screen.reset_designer()
            else:
                return
        
        self._run_safe_transition(heavy_action=None)

    def load_predefined_orbit(self):
        """ Loads a predefined orbit from the ORBITS_DATA and passes it to the orbit designer screen. """
        if self._is_switching:
            return

        dialog = PredefinedOrbitDialog(ORBITS_DATA, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            orbit_data = dialog.get_selected_orbit_data()
            
            if orbit_data:
                elements = orbit_data["elements"]
                
                def action():
                    self.orbit_designer_screen.load_predefined_orbit(elements)

                self._run_safe_transition(heavy_action=action)

    def load_orbit(self):
        """Opens a file dialog to load orbit data from a JSON file and passes it to the orbit designer screen."""
        if self._is_switching:
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Orbit Data",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if file_path:
            def action():
                self.orbit_designer_screen.load_orbit_from_file(file_path)

            self._run_safe_transition(heavy_action=action)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())