from __future__ import annotations

from PyQt6.QtCore import Qt, QLocale
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class OrbitControlsWidget(QWidget):
    """Left-side control panel for orbital parameter input and display toggles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        form_layout = QFormLayout(self)
        form_layout.setSpacing(8)

        self.header_label = QLabel("Define Orbital Parameters")
        self.header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px;"
        )
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addRow(self.header_label)

        validator = QDoubleValidator()
        validator.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self.input_a, widget_a = self.create_input_with_info(
            "", 
            "<b>Semi-major axis (a)</b><br>"
            "Defines the size of the orbit (half of the longest orbit diameter).<br>"
            "<span style='color: #a0a0a0;'>Allowed Range:</span> <b>6478.0 — 50000.0 km</b>"
        )

        # 2. Eccentricity (e)
        self.input_e, widget_e = self.create_input_with_info(
            "", 
            "<b>Eccentricity (e)</b><br>"
            "Defines the shape of the orbit (how much it deviates from a perfect circle).<br>"
            "• e = 0: Circular orbit<br>"
            "• 0 &lt; e &lt; 1: Elliptical orbit<br>"
            "<span style='color: #a0a0a0;'>Allowed Range:</span> <b>0.0 — 0.99</b>"
        )

        # 3. Inclination (i)
        self.input_i, widget_i = self.create_input_with_info(
            "", 
            "<b>Inclination (i)</b><br>"
            "The tilt of the orbital plane relative to the Earth's equatorial plane.<br>"
            "<span style='color: #a0a0a0;'>Allowed Range:</span> <b>0.0° — 180.0°</b>"
        )

        # 4. RAAN (Right Ascension of the Ascending Node)
        self.input_RAAN, widget_RAAN = self.create_input_with_info(
            "", 
            "<b>Right Ascension of the Ascending Node (Ω)</b><br>"
            "The orientation angle of the orbital plane relative to the Vernal Equinox (First Point of Aries).<br>"
            "<span style='color: #a0a0a0;'>Allowed Range:</span> <b>0.0° — 359.9°</b>"
        )

        # 5. Argument of Perigee (arg_perigee)
        self.input_arg_perigee, widget_arg_perigee = self.create_input_with_info(
            "", 
            "<b>Argument of Perigee (ω)</b><br>"
            "The orientation angle of the ellipse within its own orbital plane, measured from the ascending node.<br>"
            "<span style='color: #a0a0a0;'>Allowed Range:</span> <b>0.0° — 359.9°</b>"
        )

        # 6. True Anomaly (true_anomaly)
        self.input_true_anomaly, widget_true_anomaly = self.create_input_with_info(
            "", 
            "<b>True Anomaly (ν)</b><br>"
            "Defines the current position of the satellite along its trajectory, measured from perigee.<br>"
            "<span style='color: #a0a0a0;'>Allowed Range:</span> <b>-360.0° — 360.0°</b>"
        )

        for field in (
            self.input_a,
            self.input_e,
            self.input_i,
            self.input_RAAN,
            self.input_arg_perigee,
            self.input_true_anomaly,
        ):
            field.setValidator(validator)

        form_layout.addRow("Semi-major axis (a):", widget_a)
        form_layout.addRow("Eccentricity (e):", widget_e)
        form_layout.addRow("Inclination (i):", widget_i)
        form_layout.addRow("RAAN (Ω):", widget_RAAN)
        form_layout.addRow("Arg. of Perigee (ω):", widget_arg_perigee)
        form_layout.addRow("True Anomaly (ν):", widget_true_anomaly)

        self.generate_button = QPushButton("Generate Orbit")
        form_layout.addRow(self.generate_button)

        self.display_options_label = QLabel("Display Options")
        self.display_options_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px; margin-top: 10px;"
        )
        self.display_options_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addRow(self.display_options_label)

        self.chk_grid = QCheckBox("Show Equatorial Plane")
        self.chk_grid.setChecked(False)

        self.chk_eci = QCheckBox("Show ECI Vectors")
        self.chk_eci.setChecked(False)

        self.chk_earth = QCheckBox("Show Earth")
        self.chk_earth.setChecked(True)

        self.chk_orbit_plane = QCheckBox("Show Orbit Plane")
        self.chk_orbit_plane.setChecked(False)
        self.chk_orbit_plane.setEnabled(False)

        self.chk_orbital_elements = QCheckBox("Show Orbital Elements")
        self.chk_orbital_elements.setChecked(False)
        self.chk_orbital_elements.setEnabled(False)

        form_layout.addRow(self.chk_grid)
        form_layout.addRow(self.chk_eci)
        form_layout.addRow(self.chk_earth)

        self.animation_section = QWidget(self)
        self.animation_layout = QVBoxLayout(self.animation_section)
        self.animation_layout.setContentsMargins(0, 0, 0, 0)

        self.animate_button = QPushButton("Start Animation")
        

        self.clear_button = QPushButton("Clear")
      

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 5)
        self.speed_slider.setValue(3)
        self.speed_slider.setToolTip("Animation speed")

        self.speed_label = QLabel("Speed: 3x")
        self.speed_label.setStyleSheet("color: #ffffff;")
        self.speed_slider.valueChanged.connect(
            lambda value: self.speed_label.setText(f"Speed: {value}x")
        )

        button_row = QHBoxLayout()
        button_row.addWidget(self.animate_button)
        button_row.addWidget(self.clear_button)
        self.animation_layout.addLayout(button_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("Speed"))
        speed_row.addWidget(self.speed_slider)
        speed_row.addWidget(self.speed_label)
        self.animation_layout.addLayout(speed_row)

        self.animation_section.setEnabled(False)
        form_layout.addRow(self.animation_section)

        self.orbit_options_label = QLabel("Orbit Display Options")
        self.orbit_options_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px; margin-top: 10px;"
        )
        self.orbit_options_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addRow(self.orbit_options_label)
        form_layout.addRow(self.chk_orbit_plane)
        form_layout.addRow(self.chk_orbital_elements)
        
        self.save_button = QPushButton("Save Orbit")
        self.save_button.setEnabled(False)

        form_layout.addRow(self.save_button)



    def create_input_with_info(self, placeholder_text: str, tooltip_html: str) -> tuple[QLineEdit, QWidget]:
        """
        Creates a text input field with an attached 'ⓘ' info icon.
        Returns a tuple containing the QLineEdit reference and the container QWidget.
        """
        # Create container and horizontal layout for the field + icon pair
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)  # Small spacing between the input and the icon

        # Create the actual text input
        line_edit = QLineEdit(placeholder_text)
        
        # Create the info icon using the Unicode character ⓘ
        info_icon = QLabel("ⓘ")
        info_icon.setObjectName("InfoIcon")  # Linked to the selector in styles.qss
        info_icon.setToolTip(tooltip_html)   # Set the rich HTML tooltip
        info_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Assemble the layout
        layout.addWidget(line_edit, stretch=1)
        layout.addWidget(info_icon)

        return line_edit, container

    def reset_inputs(self) -> None:
        """Resets all input fields to their default values."""
        self.input_a.setText("")
        self.input_e.setText("")
        self.input_i.setText("")
        self.input_RAAN.setText("")
        self.input_arg_perigee.setText("")
        self.input_true_anomaly.setText("")

        # Reset checkboxes
        self.chk_grid.setChecked(False)
        self.chk_eci.setChecked(False)
        self.chk_earth.setChecked(True)
        self.chk_orbit_plane.setChecked(False)
        self.chk_orbital_elements.setChecked(False)

        # Reset animation controls
        self.animate_button.setText("Start Animation")
        self.speed_slider.setValue(3)

