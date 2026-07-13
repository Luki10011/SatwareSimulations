from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QComboBox, QLabel, QTextBrowser, QDialogButtonBox
from PyQt6.QtCore import Qt

class PredefinedOrbitDialog(QDialog):
    def __init__(self, orbits_data, parent=None):
        super().__init__(parent)
        self.orbits_data = orbits_data
        self.selected_orbit_name = None
        
        self.setWindowTitle("Select Predefined Orbit")
        self.resize(650, 350)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        combo_label = QLabel("Orbit Type:")
        combo_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        
        self.orbit_combo = QComboBox()
        self.orbit_combo.addItems(self.orbits_data.keys())
        self.orbit_combo.setFixedWidth(220)
        self.orbit_combo.currentIndexChanged.connect(self.update_description)
        
        left_layout.addWidget(combo_label)
        left_layout.addWidget(self.orbit_combo)
        content_layout.addLayout(left_layout, stretch=2)
        
        right_layout = QVBoxLayout()
        
        desc_label = QLabel("Characteristics:")
        desc_label.setStyleSheet("font-weight: bold; font-size: 11pt; color: #ffffff;")
        
        self.description_text = QTextBrowser()
        self.description_text.setStyleSheet("""
            QTextBrowser {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                color: #e0e0e0;
                padding: 10px;
                font-size: 10pt;
            }
        """)
        
        right_layout.addWidget(desc_label)
        right_layout.addWidget(self.description_text)
        content_layout.addLayout(right_layout, stretch=3)
        
        # Dodajemy układ zawartości do głównego okna
        main_layout.addLayout(content_layout)
        
        # --- DOLNA STRONA: PRZYCISKI STANDARDOWE (OK / Anuluj) ---
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        
        main_layout.addWidget(self.button_box)
        
        self.update_description()

    def update_description(self):
        """Aktualizuje pole tekstowe po prawej stronie na podstawie wybranego elementu."""
        current_orbit = self.orbit_combo.currentText()
        if current_orbit in self.orbits_data:
            self.description_text.setHtml(self.orbits_data[current_orbit]["description"])

    def get_selected_orbit_data(self):
        """Zwraca słownik z parametrami wybranej orbity po zatwierdzeniu okna."""
        current_orbit = self.orbit_combo.currentText()
        return self.orbits_data.get(current_orbit, None)