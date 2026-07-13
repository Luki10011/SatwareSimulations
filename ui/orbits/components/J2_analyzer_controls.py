import numpy as np
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QWidget,
)
from PyQt6.QtCore import Qt
from core.physics.J2_pertubator import J2Perturbator
from core.physics.dataclasses.orbital_data import OrbitalElements
from core.physics.orbits import Orbit


class J2AnalyzerControlsWidget(QWidget):

    def __init__(self, parent = None):
        super().__init__(parent)
        self.mean_nodal_regression = None
        self.mean_apsidal_precession = None
        self.J2_perturbator = None
        self._build_ui()

    def _build_ui(self) -> None:
        form_layout = QFormLayout(self)
        form_layout.setSpacing(8)
        
        self.header_label = QLabel("Analyse Earth's Oblateness")
        self.header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 15px;"
        )
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.addRow(self.header_label)

        self.info = QLabel()
        self.info.setWordWrap(True)  
        self.info.setText(
            "Earth's oblateness (represented by the J₂ coefficient) creates an asymmetric gravitational field "
            "due to the bulge at the equator. This causes secular (constant) orbital perturbations:<br><br>"
            "• <b>Nodal Regression (Ω):</b> The continuous rotation of the orbital plane around Earth's rotational axis.<br>"
            "• <b>Apsidal Precession (ω):</b> The shift of the perigee point (argument of perigee) within the orbital plane.<br><br>"
            "<i>Note that in case of circular orbits there is no perigee, which leads to no apsidal precession.</i>"
        )
        self.info.setStyleSheet("""
            QLabel {
                color: #b0b3b8;
                font-size: 11px;
                line-height: 15px;
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        form_layout.addRow(self.info)

        self.results_card = QWidget()
        self.results_card.setStyleSheet("""
            QWidget {
                background-color: #1e1e1f;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
            QLabel {
                border: none;
            }
        """)
        
        card_layout = QGridLayout(self.results_card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setHorizontalSpacing(14)
        card_layout.setVerticalSpacing(10)

        lbl_col_param = QLabel("Perturbation Parameter")
        lbl_col_param.setStyleSheet("color: #808080; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        
        lbl_col_sec = QLabel("Rate [°/day]")
        lbl_col_sec.setStyleSheet("color: #808080; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        lbl_col_sec.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        lbl_col_rev = QLabel("Change [°/orbit]")
        lbl_col_rev.setStyleSheet("color: #808080; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        lbl_col_rev.setAlignment(Qt.AlignmentFlag.AlignRight)

        card_layout.addWidget(lbl_col_param, 0, 0)
        card_layout.addWidget(lbl_col_sec, 0, 1)
        card_layout.addWidget(lbl_col_rev, 0, 2)

        value_style = "font-family: 'Consolas', 'Courier New'; font-weight: bold; font-size: 11px;"

        lbl_node = QLabel("Nodal Regression (ΔΩ):")
        lbl_node.setStyleSheet("color: #b0b3b8; font-size: 11px;")
        
        self.val_node_sec = QLabel("—")
        self.val_node_sec.setStyleSheet(value_style + " color: #007acc;")
        self.val_node_sec.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.val_node_rev = QLabel("—")
        self.val_node_rev.setStyleSheet(value_style + " color: #00aaff;")
        self.val_node_rev.setAlignment(Qt.AlignmentFlag.AlignRight)

        card_layout.addWidget(lbl_node, 1, 0)
        card_layout.addWidget(self.val_node_sec, 1, 1)
        card_layout.addWidget(self.val_node_rev, 1, 2)

        lbl_aps = QLabel("Apsidal Precession (Δω):")
        lbl_aps.setStyleSheet("color: #b0b3b8; font-size: 11px;")
        
        self.val_aps_sec = QLabel("—")
        self.val_aps_sec.setStyleSheet(value_style + " color: #da70d6;")
        self.val_aps_sec.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.val_aps_rev = QLabel("—")
        self.val_aps_rev.setStyleSheet(value_style + " color: #ba55d3;")
        self.val_aps_rev.setAlignment(Qt.AlignmentFlag.AlignRight)

        card_layout.addWidget(lbl_aps, 2, 0)
        card_layout.addWidget(self.val_aps_sec, 2, 1)
        card_layout.addWidget(self.val_aps_rev, 2, 2)

        form_layout.addRow(self.results_card)

        self.visualization_label = QLabel("Visualize Orbit's change")
        form_layout.addWidget(self.visualization_label)

        self.visualization_label.setStyleSheet(
            "font-size: 12px; font-weight: bold; color: #ffffff; margin-top: 15px; margin-bottom: 5px;"
        )
        form_layout.addRow(self.visualization_label)

        self.time_mode_combo = QComboBox()
        self.time_mode_combo.addItems(["Orbits", "Days"])
      
        form_layout.addRow("Prediction Mode:", self.time_mode_combo)

        self.time_value_spin = QSpinBox()
        self.time_value_spin.setRange(1, 10000)
        self.time_value_spin.setValue(10)  
        self.time_value_spin.setStyleSheet("""
            QSpinBox {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                
                padding-top: 4px;
                padding-bottom: 4px;
                padding-left: 6px;
                padding-right: 18px; /* Kluczowe: rezerwujemy miejsce na strzałki */
            }
        """)
        form_layout.addRow("Time Horizon:", self.time_value_spin)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(2)  
        btn_layout.setContentsMargins(0, 0, 0, 5)


        self.drift_header = QLabel("Orbital Drift Results")
        self.drift_header.setStyleSheet(
            "font-size: 13px; font-weight: bold; color: #ffffff; margin-top: 15px; margin-bottom: 5px;"
        )
        form_layout.addRow(self.drift_header)

        # Pola tekstowe na wyniki (ustawione jako placeholder "0.00°")
        self.raan_drift_label = QLabel("0.00°")
        self.raan_drift_label.setStyleSheet("color: #00ffcc; font-weight: bold;")
        form_layout.addRow("Δ RAAN (Ω):", self.raan_drift_label)

        self.omega_drift_label = QLabel("0.00°")
        self.omega_drift_label.setStyleSheet("color: #00ffcc; font-weight: bold;")
        form_layout.addRow("Δ Arg. of Perigee (ω):", self.omega_drift_label)
        
        # Separator wizualny przed przyciskiem powrotu
        form_layout.addRow(QLabel(""))

        self.plot_group = QButtonGroup(self)
        self.plot_group.setExclusive(True)
        

        self.btn_propagate = QPushButton("Propagate and  Plot")
        self.time_mode_combo.currentIndexChanged.connect(self._on_mode_changed)

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setEnabled(False)

        buttons = [self.btn_propagate, self.btn_clear]
        for idx, btn in enumerate(buttons):
            btn.setCheckable(True)
            btn.setFixedHeight(32)  # Stała, wygodna wysokość zakładki
            self.plot_group.addButton(btn, idx)
            btn_layout.addWidget(btn)

        form_layout.addRow(btn_layout)

    
    def update_perturbator(self, orbit: Orbit):
        """

        """
        self.J2_perturbator = J2Perturbator(orbit)
        
        raw_nodal_rad_s = self.J2_perturbator.mean_nodal_regression
        raw_apsidal_rad_s = self.J2_perturbator.mean_apsidal_precession
        
        period_seconds = 2 * np.pi / self.J2_perturbator.n

        if raw_nodal_rad_s is not None:
            nodal_deg_s = np.degrees(raw_nodal_rad_s)
            nodal_deg_rev = nodal_deg_s * period_seconds
            
            self.val_node_sec.setText(f"{nodal_deg_s * 24 * 3600:.6f}°/day")
            self.val_node_rev.setText(f"{nodal_deg_rev:.5f}°/orbit")
        else:
            self.val_node_sec.setText("0.000000°/day")
            self.val_node_rev.setText("0.00000°/orbit")

        if raw_apsidal_rad_s is not None:
            if orbit.orbitalElements.eccentricity < 1e-4:
                self.val_aps_sec.setText("0.000000°/day")
                self.val_aps_rev.setText("0.00000°/orbit")
            else:
                apsidal_deg_s = np.degrees(raw_apsidal_rad_s)
                apsidal_deg_rev = apsidal_deg_s * period_seconds
                
                self.val_aps_sec.setText(f"{apsidal_deg_s * 24 * 3600 :.6f}°/day")
                self.val_aps_rev.setText(f"{apsidal_deg_rev:.5f}°/orbit")
        else:
            self.val_aps_sec.setText("0.000000°/day")
            self.val_aps_rev.setText("0.00000°/orbit")


    def _on_mode_changed(self, index: int) -> None:
        """Dynamicznie dostosowuje zakresy spinboxa w zależności od wybranego trybu."""
        if self.time_mode_combo.currentText() == "Orbits":
            self.time_value_spin.setRange(1, 1000)
            self.time_value_spin.setValue(10)
        else:  
            self.time_value_spin.setRange(1, 365)
            self.time_value_spin.setValue(7)

    def _on_propagate_clicked(self) -> None:
        """Metoda pośrednicząca, która zbierze dane z UI i przekaże je wyżej."""
        mode = self.time_mode_combo.currentText()
        value = self.time_value_spin.value()
        
        # Tutaj wyemitujesz sygnał lub wywołasz metodę z OrbitDesignera, 
        # przekazując konfigurację do obliczeń matematycznych.
        print(f"Propagating for {value} {mode}...")
    
    def reset(self):
        self.time_mode_combo.setCurrentText("Orbits")
        self.time_value_spin.setRange(1, 10000)
        self.time_value_spin.setValue(10)

    def update_drift_display(self, delta_raan_deg: float, delta_omega_deg: float) -> None:
        """Aktualizuje etykiety w UI o wyliczone przesunięcie w stopniach."""
        # Formatowanie z jawnym znakiem plus/minus (+/-) dla czytelności dryftu
        self.raan_drift_label.setText(f"{delta_raan_deg:+.2f}°")
        self.omega_drift_label.setText(f"{delta_omega_deg:+.2f}°")

