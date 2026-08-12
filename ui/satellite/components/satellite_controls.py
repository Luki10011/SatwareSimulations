from typing import Any, Dict, List
from PyQt6.QtCore import QLocale, Qt, pyqtSignal
from PyQt6.QtGui import QDoubleValidator, QIntValidator
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTabBar,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QMessageBox,
)

from core.physics.dataclasses.satellite_configuration import (
    MASS_MIN,
    MASS_MAX,
    DIM_MIN,
    DIM_MAX,
    COIL_TURNS_MIN,
    COIL_TURNS_MAX,
    COIL_AREA_MIN,
    COIL_AREA_MAX,
    MAX_CURRENT_MIN,
    MAX_CURRENT_MAX,
    calculate_box_inertia_tensor,
    calculate_total_inertia_tensor,
    calculate_reaction_wheel_local_inertia,
    reaction_wheel_axes,
    validate_satellite_configuration_data,
)
import numpy as np
from utils.ui.ui_utils import show_dark_message_box


class SatelliteControls(QWidget):
    configurationChanged = pyqtSignal(dict, bool)  # emits current configuration data and whether to mark errors
    saveRequested = pyqtSignal()
    loadRequested = pyqtSignal()
    resetRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pristine = True
        self._silent_update = True
        self._build_ui()
        self._set_defaults()
        self._refresh_summary()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        self.header_label = QLabel("Satellite Configuration Editor")
        self.header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px;"
        )
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        main_layout.addWidget(self.header_label)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.tab_widget.setObjectName("satelliteTabWidget")
        main_layout.addWidget(self.tab_widget)

        self._mechanical_tab = QWidget(self)
        self._mechanical_tab.setObjectName("mechanical_tab")
        self._reaction_tab = QWidget(self)
        self._reaction_tab.setObjectName("reaction_tab")
        self._summary_tab = QWidget(self)
        self._summary_tab.setObjectName("summary_tab")

        self.tab_widget.addTab(self._mechanical_tab, "Mechanical / EM")
        self.tab_widget.addTab(self._reaction_tab, "Reaction Wheels")
        self.tab_widget.addTab(self._summary_tab, "Summary")

        self._build_mechanical_tab()
        self._build_summary_tab()
        self._build_reaction_tab()
        self._connect_edit_signals()

        button_row = QHBoxLayout()
        button_row.setSpacing(6)
        self.btn_save = QPushButton("Save")
        self.btn_reset = QPushButton("Reset")
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_reset)
        main_layout.addLayout(button_row)

        self.btn_save.clicked.connect(self._emit_save_request)
        self.btn_reset.clicked.connect(self._emit_reset_request)

        self.btn_save.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_reset.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._emit_change(mark_errors=False)  

    def _build_mechanical_tab(self) -> None:
        form_layout = QFormLayout(self._mechanical_tab)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)
        form_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.us_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

        mass_val = QDoubleValidator(0.0, 100.0, 3, self)
        mass_val.setLocale(self.us_locale)
        mass_val.setNotation(QDoubleValidator.Notation.StandardNotation)

        dim_val = QDoubleValidator(0.0, 10.0, 3, self)
        dim_val.setLocale(self.us_locale)
        dim_val.setNotation(QDoubleValidator.Notation.StandardNotation)

        inertia_val = QDoubleValidator(0.0, 10.0, 6, self)
        inertia_val.setLocale(self.us_locale)
        inertia_val.setNotation(QDoubleValidator.Notation.ScientificNotation)

        turns_val = QIntValidator(0, 10000, self)

        area_val = QDoubleValidator(0.0, 100.0, 4, self)
        area_val.setLocale(self.us_locale)

        current_val = QDoubleValidator(0.0, 100.0, 2, self)
        current_val.setLocale(self.us_locale)

        self.mechanical_header_label = QLabel("Mechanical Properties")
        self.mechanical_header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px;"
        )
        form_layout.addRow(self.mechanical_header_label)

        self.input_mass = self._create_line_edit(mass_val)
        form_layout.addRow("Mass [kg]:", self.input_mass)

        self.input_dimensions = [self._create_line_edit(dim_val) for _ in range(3)]
        dimensions_container = self._create_horizontal_inputs(self.input_dimensions)
        form_layout.addRow("Dimensions [m]:", dimensions_container)

        inertia_label = QLabel("Inertia tensor J [kg·m²]:")
        self.input_inertia_tensor = [self._create_line_edit(inertia_val) for _ in range(9)]
        inertia_container = self._create_grid_inputs(self.input_inertia_tensor, 3)
        form_layout.addRow(inertia_label)
        form_layout.addRow(inertia_container)

        self.btn_calculate_inertia_tensor = QPushButton("Calculate J")
        self.btn_calculate_inertia_tensor.clicked.connect(self._calculate_inertia_tensor)
        form_layout.addRow(self.btn_calculate_inertia_tensor)

        self.electromagnetic_header_label = QLabel("Electromagnetic Properties")
        self.electromagnetic_header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px; margin-top: 10px;"
        )
        form_layout.addRow(self.electromagnetic_header_label)

        self.input_coil_turns = self._create_line_edit(turns_val)
        self.input_coil_area = self._create_line_edit(area_val)
        self.input_max_current = self._create_line_edit(current_val)
        form_layout.addRow("Coil turns:", self.input_coil_turns)
        form_layout.addRow("Coil area [m²]:", self.input_coil_area)
        form_layout.addRow("Max current [A]:", self.input_max_current)

    def _build_reaction_tab(self) -> None:
        if hasattr(self, "btn_reset"):
            self.btn_reset.setEnabled(True)
        
        form_layout = QFormLayout(self._reaction_tab)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)

        double_validator = QDoubleValidator(self)
        double_validator.setLocale(
            QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)
        )
        double_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self.input_reaction_configuration = QComboBox(self)
        self.input_reaction_configuration.addItems(["principal", "pyramid"])
        self.input_reaction_configuration.currentTextChanged.connect(self._update_reaction_configuration_ui)
        form_layout.addRow("Configuration:", self.input_reaction_configuration)

        self.input_wheel_count = self._create_line_edit(QIntValidator(self))
        self.input_wheel_count.setEnabled(False)
        form_layout.addRow("Wheel count:", self.input_wheel_count)

        self.input_wheel_mass = self._create_line_edit(double_validator)
        self.input_wheel_radius = self._create_line_edit(double_validator)
        self.input_wheel_height = self._create_line_edit(double_validator)
        self.input_wheel_max_speed = self._create_line_edit(double_validator)
        form_layout.addRow("Wheel mass [kg]:", self.input_wheel_mass)
        form_layout.addRow("Wheel radius [m]:", self.input_wheel_radius)
        form_layout.addRow("Wheel height [m]:", self.input_wheel_height)
        form_layout.addRow("Max speed [rpm]:", self.input_wheel_max_speed)

        wheel_inertia_val = QDoubleValidator(0.0, 10.0, 6, self)
        wheel_inertia_val.setLocale(self.us_locale)
        wheel_inertia_val.setNotation(QDoubleValidator.Notation.ScientificNotation)
        
        inertia_label = QLabel("Wheel inertia tensor J<sub>R</sub> [kg·m²]:")
        self.wheel_inertia_tensor = [self._create_line_edit(wheel_inertia_val, parent=self._reaction_tab) for _ in range(9)]
        wheel_own_inertia_container = self._create_grid_inputs(self.wheel_inertia_tensor, 3, parent=self._reaction_tab)
        wheel_own_inertia_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        for index in range(9):
            self.wheel_inertia_tensor[index].setText("")
            self.wheel_inertia_tensor[index].setReadOnly(True)
            self.wheel_inertia_tensor[index].setStyleSheet("background-color: #2b2b2b; color: #a9b7c6; border: 1px solid #3c3f41;")
       
        form_layout.addRow(inertia_label)
        form_layout.addRow(wheel_own_inertia_container)

        btn_calculte_wheel_inertia = QPushButton()

        calculate_inertia_label = QLabel("Calculate J<sub>R</sub>")
        calculate_inertia_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        calculate_inertia_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents
        )

        layout = QHBoxLayout(btn_calculte_wheel_inertia)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(calculate_inertia_label)

        btn_calculte_wheel_inertia.clicked.connect(self._calculate_wheel_inertia)

        form_layout.addRow(btn_calculte_wheel_inertia)

        self._update_reaction_configuration_ui(self.input_reaction_configuration.currentText())

    def _calculate_wheel_inertia(self):
        errors = self.validate_inputs()
        has_mass_error = "wheel_mass" in errors
        has_dim_error = any(k in errors for k in ("wheel_radius", "wheel_height"))

        if has_mass_error or has_dim_error:
            show_dark_message_box(
                self,
                "Invalid parameters",
                "Please correct highlighted fields before calculating inertia.",
                icon=QMessageBox.Icon.Warning
            )
            size_errors = {k: v for k, v in errors.items() if k in ("wheel_mass", "wheel_radius", "wheel_height")}
            self.mark_errors(size_errors, replace_all=False)
            return

        r_mass = float(self.input_wheel_mass.text() or 0.0)
        r_height = float(self.input_wheel_height.text() or 0.0)
        r_radius = float(self.input_wheel_radius.text() or 0.0)
        calculated_inertia_tensor = calculate_reaction_wheel_local_inertia(
            r_mass,
            r_radius,
            r_height
        )
        flat_values = [
            calculated_inertia_tensor[0, 0], calculated_inertia_tensor[0, 1], calculated_inertia_tensor[0, 2],
            calculated_inertia_tensor[1, 0], calculated_inertia_tensor[1, 1], calculated_inertia_tensor[1, 2],
            calculated_inertia_tensor[2, 0], calculated_inertia_tensor[2, 1], calculated_inertia_tensor[2, 2],
        ]

        for index, value in enumerate(flat_values):
            self.wheel_inertia_tensor[index].setText(f"{value:.6}")

    def _build_summary_tab(self) -> None:
                
        layout = QVBoxLayout(self._summary_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        self.summary_browser = QTextBrowser(self)
        self.summary_browser.setObjectName("satelliteSummaryBrowser")
        self.summary_browser.setReadOnly(True)

        self.summary_browser.setOpenExternalLinks(True)
        
        layout.addWidget(self.summary_browser)

    def _create_line_edit(self, validator, parent = None) -> QLineEdit:
        line_edit = QLineEdit(self if parent is None else parent)
        line_edit.setValidator(validator)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return line_edit

    def _create_horizontal_inputs(self, inputs: List[QLineEdit], parent = None) -> QWidget:
        container = QWidget(self if parent is None else parent)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for input_field in inputs:
            layout.addWidget(input_field, stretch=1)
        return container

    def _create_grid_inputs(self, inputs: List[QLineEdit], columns: int, parent = None) -> QWidget:
        container = QWidget(self if parent is None else parent)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for row_start in range(0, len(inputs), columns):
            row_inputs = inputs[row_start:row_start + columns]
            row_widget = QWidget(self if parent is None else parent)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(6)
            for widget in row_inputs:
                row_layout.addWidget(widget, stretch=1)
            layout.addWidget(row_widget)
        return container

    def _connect_edit_signals(self) -> None:
        for field in [
            self.input_mass,
            *self.input_dimensions,
            *self.input_inertia_tensor,
            self.input_coil_turns,
            self.input_coil_area,
            self.input_max_current,
            self.input_wheel_count,
            self.input_wheel_mass,
            self.input_wheel_radius,
            self.input_wheel_height,
            self.input_wheel_max_speed,
        ]:
            field.textChanged.connect(self._on_field_text_changed)
            field.editingFinished.connect(self._on_field_finished)
           
        self.input_reaction_configuration.currentTextChanged.connect(self._on_field_text_changed)
        self.input_reaction_configuration.currentTextChanged.connect(self._on_field_finished)

    def _on_field_text_changed(self) -> None:
        """Called on text change: clears error on currently edited field and propagates change."""
        sender = self.sender()
        if sender and isinstance(sender, QWidget):
            self._clear_widget_errors(sender)
        self._refresh_summary()
        self._emit_change(mark_errors=False)

    def _emit_change(self, mark_errors: bool = False) -> None:
        # if self._silent_update:
        #     return
        self._pristine = False
        should_mark = bool(mark_errors) if isinstance(mark_errors, bool) else False
        self.configurationChanged.emit(self.get_configuration_data(), should_mark)

    def _emit_save_request(self) -> None:
        self.saveRequested.emit()

    def _emit_load_request(self) -> None:
        self.loadRequested.emit()

    def _emit_reset_request(self) -> None:
        self.resetRequested.emit()

    def _update_reaction_configuration_ui(self, value: str) -> None:
        expected = 3 if value.lower() == "principal" else 4
        self.input_wheel_count.setText(str(expected))
        self.input_wheel_count.setEnabled(False)
        self._refresh_summary()

    def _calculate_inertia_tensor(self) -> None:
        errors = self.validate_inputs()
        has_mass_error = "mass" in errors
        has_dim_error = any(k in errors for k in ("dimensions", "dim_a", "dim_b", "dim_h"))

        # Odśwież widok 3D tylko, gdy masa i wymiary są poprawne
        if has_mass_error or has_dim_error:
            show_dark_message_box(
                self,
                "Invalid parameters",
                "Please correct highlighted fields before calculating inertia.",
                icon=QMessageBox.Icon.Warning
            )
            size_errors = {k: v for k, v in errors.items() if k in ("mass", "dimensions", "dim_a", "dim_b", "dim_h")}
            self.mark_errors(size_errors, replace_all=False)
            return

        dimensions = self._read_dimensions()
        if dimensions is None:
            show_dark_message_box(
                self,
                "Invalid parameters",
                "Dimensions are required and must be valid positive numbers.",
                icon=QMessageBox.Icon.Warning
            )
            return
        a, b, h = dimensions
        mass = self._to_float(self.input_mass.text())
        box_tensor = calculate_box_inertia_tensor(mass, a, b, h)

        flat_values = [
            box_tensor[0, 0], box_tensor[0, 1], box_tensor[0, 2],
            box_tensor[1, 0], box_tensor[1, 1], box_tensor[1, 2],
            box_tensor[2, 0], box_tensor[2, 1], box_tensor[2, 2],
        ]

        for index, value in enumerate(flat_values):
            self.input_inertia_tensor[index].setText(f"{value:.6f}")

        self._refresh_summary()

    def _set_defaults(self) -> None:
        self._silent_update = True
        self.input_mass.setText("")
        self.input_dimensions[0].setText("")
        self.input_dimensions[1].setText("")
        self.input_dimensions[2].setText("")
        for idx in range(9):
            self.input_inertia_tensor[idx].setText("")
        self.input_coil_turns.setText("")
        self.input_coil_area.setText("")
        self.input_max_current.setText("")
        self.input_reaction_configuration.setCurrentText("principal")
        self.input_wheel_count.setText("3")
        self.input_wheel_mass.setText("")
        self.input_wheel_radius.setText("")
        self.input_wheel_height.setText("")
        self.input_wheel_max_speed.setText("")
        self._silent_update = False

    def _to_float(self, text: str, default: float = 0.0) -> float:
        try:
            return float(text)
        except (TypeError, ValueError):
            return default

    def _to_int(self, text: str, default: int = 0) -> int:
        try:
            return int(float(text))
        except (TypeError, ValueError):
            return default

    def _read_dimensions(self) -> List[float] | None:
        values = []
        for field in self.input_dimensions:
            try:
                value = float(field.text())
            except ValueError:
                return None
            if value <= 0:
                return None
            values.append(value)
        return values

    def get_configuration_data(self) -> dict:
        dimensions = self._read_dimensions()
        satellite_inertia_rows = []
        reaction_wheel_inertia_rows = []
        for row_index in range(0, 9, 3):
            satellite_inertia_rows.append([
                self._to_float(self.input_inertia_tensor[row_index + col_index].text())
                for col_index in range(3)
            ])
        for row_index in range(0, 9, 3):
            reaction_wheel_inertia_rows.append([
                self._to_float(self.wheel_inertia_tensor[row_index + col_index].text())
                for col_index in range(3)
            ])
        return {
            "mechanical": {
                "mass": self._to_float(self.input_mass.text()),
                "dimensions": dimensions if dimensions is not None else [],
                "inertia_tensor": satellite_inertia_rows,
            },
            "electromagnetic": {
                "coil_turns": self._to_int(self.input_coil_turns.text()),
                "coil_area": self._to_float(self.input_coil_area.text()),
                "max_current": self._to_float(self.input_max_current.text()),
            },
            "reaction_wheels": {
                "configuration": self.input_reaction_configuration.currentText().strip().lower(),
                "wheel_count": self._to_int(self.input_wheel_count.text()),
                "wheel_mass": self._to_float(self.input_wheel_mass.text()),
                "wheel_radius": self._to_float(self.input_wheel_radius.text()),
                "wheel_height": self._to_float(self.input_wheel_height.text()),
                "wheel_max_speed": self._to_float(self.input_wheel_max_speed.text()),
                "inertia_tensor": reaction_wheel_inertia_rows,
            },
        }

    def set_configuration_data(self, data: dict) -> None:
        mechanical = data.get("mechanical", {})
        electromagnetic = data.get("electromagnetic", {})
        reaction_wheels = data.get("reaction_wheels", {})

        self._silent_update = True
        self.input_mass.setText("" if mechanical.get("mass") in (None, "None") else str(mechanical.get("mass", "")))

        dimensions = mechanical.get("dimensions") or []
        for index in range(3):
            if index < len(dimensions):
                self.input_dimensions[index].setText(str(dimensions[index]))
            else:
                self.input_dimensions[index].setText("")

        inertia_tensor = mechanical.get("inertia_tensor", [])
        flat_values = []
        if isinstance(inertia_tensor, (list, tuple)):
            for row in inertia_tensor:
                if isinstance(row, (list, tuple)):
                    flat_values.extend([f"{value:10.8f}" for value in row[:3]])
        for index in range(9):
            self.input_inertia_tensor[index].setText(flat_values[index] if index < len(flat_values) else "")

        self.input_coil_turns.setText("" if electromagnetic.get("coil_turns") in (None, "None") else str(electromagnetic.get("coil_turns", "")))
        self.input_coil_area.setText("" if electromagnetic.get("coil_area") in (None, "None") else str(electromagnetic.get("coil_area", "")))
        self.input_max_current.setText("" if electromagnetic.get("max_current") in (None, "None") else str(electromagnetic.get("max_current", "")))

        configuration = str(reaction_wheels.get("configuration", "principal")).lower()
        self.input_reaction_configuration.setCurrentText(configuration)
        self.input_wheel_count.setText("" if reaction_wheels.get("wheel_count") in (None, "None") else str(reaction_wheels.get("wheel_count", 3)))
        self.input_wheel_mass.setText("" if reaction_wheels.get("wheel_mass") in (None, "None") else str(reaction_wheels.get("wheel_mass", "")))
        self.input_wheel_radius.setText("" if reaction_wheels.get("wheel_radius") in (None, "None") else str(reaction_wheels.get("wheel_radius", "")))
        self.input_wheel_height.setText("" if reaction_wheels.get("wheel_height") in (None, "None") else str(reaction_wheels.get("wheel_height", "")))
        self.input_wheel_max_speed.setText("" if reaction_wheels.get("wheel_max_speed") in (None, "None") else str(reaction_wheels.get("wheel_max_speed", "")))

        wheel_inertia_tensor = reaction_wheels.get("inertia_tensor", [])
        flat_wheel_values = []
        if isinstance(wheel_inertia_tensor, (list, tuple)):
            for row in wheel_inertia_tensor:
                if isinstance(row, (list, tuple)):
                    flat_wheel_values.extend([f"{value:10.8f}" for value in row[:3]])

        for index in range(9):
            self.wheel_inertia_tensor[index].setText(flat_wheel_values[index] if index < len(flat_wheel_values) else "")


        self._silent_update = False
        self._pristine = False
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        if not hasattr(self, "summary_browser"):
            return

        data = self.get_configuration_data()
        mechanical_tensor = data["mechanical"]["inertia_tensor"]
        reaction_wheels = data["reaction_wheels"]

        try:
            wheel_axes = reaction_wheel_axes(
                reaction_wheels.get("configuration", "principal"),
                int(reaction_wheels.get("wheel_count", 3)),
            )
            total_tensor = calculate_total_inertia_tensor(
                mechanical_tensor=np.array(mechanical_tensor, dtype=float),
                wheel_mass=reaction_wheels["wheel_mass"],
                wheel_radius=reaction_wheels["wheel_radius"],
                wheel_height=reaction_wheels["wheel_height"],
                wheel_axes=wheel_axes,
            )
        except Exception:
            total_tensor = np.array(mechanical_tensor, dtype=float)

        def fmt(val, fmtstr="{:.3f}"):
            try:
                return fmtstr.format(float(val))
            except Exception:
                return "0.000"

        dims = data["mechanical"].get("dimensions", [])
        dim_a = fmt(dims[0]) if isinstance(dims, (list, tuple)) and len(dims) > 0 else "0.000"
        dim_b = fmt(dims[1]) if isinstance(dims, (list, tuple)) and len(dims) > 1 else "0.000"
        dim_h = fmt(dims[2]) if isinstance(dims, (list, tuple)) and len(dims) > 2 else "0.000"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
        <style>
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 13px;
                color: #e0e0e0;
                background-color: #1e1e1e;
                margin: 5px;
            }}
            h2 {{
                color: #ffffff;
                border-bottom: 1px solid #0288d1;
                padding-bottom: 4px;
                margin-top: 14px;
                margin-bottom: 8px;
                font-size: 14px;
            }}
            .summary-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 10px;
            }}
            .summary-table td {{
                padding: 4px 8px;
                border-bottom: 1px solid #2a2a2a;
            }}
            .summary-table td.label {{
                font-weight: bold;
                color: #b0bec5;
                width: 45%;
            }}
            .summary-table td.value {{
                color: #ffffff;
            }}
            .tensor-table {{
                border-collapse: collapse;
                margin-top: 6px;
                margin-bottom: 10px;
            }}
            .tensor-table td {{
                border: 1px solid #3f3f3f;
                padding: 5px 10px;
                text-align: right;
                font-family: 'Consolas', 'Courier New', monospace;
                background-color: #252526;
                color: #ffffff;
            }}
            .badge {{
                background-color: #0288d1;
                color: #ffffff;
                padding: 2px 6px;
                border-radius: 3px;
                font-size: 11px;
                font-weight: bold;
            }}
        </style>
        </head>
        <body>
            <h2> Satellite Mechanical Properties</h2>
            <table class="summary-table">
                <tr>
                    <td class="label">Total Mass:</td>
                    <td class="value">{fmt(data['mechanical']['mass'])} kg</td>
                </tr>
                <tr>
                    <td class="label">Dimensions (a x b x h):</td>
                    <td class="value">{dim_a} x {dim_b} x {dim_h} m</td>
                </tr>
            </table>

            <h2> Electromagnetic Coils</h2>
            <table class="summary-table">
                <tr>
                    <td class="label">Turns Count:</td>
                    <td class="value">{data['electromagnetic']['coil_turns']}</td>
                </tr>
                <tr>
                    <td class="label">Coil Area:</td>
                    <td class="value">{fmt(data['electromagnetic']['coil_area'])} m²</td>
                </tr>
                <tr>
                    <td class="label">Max Current:</td>
                    <td class="value">{fmt(data['electromagnetic']['max_current'])} A</td>
                </tr>
            </table>

            <h2> Reaction Wheels Subsystem</h2>
            <table class="summary-table">
                <tr>
                    <td class="label">Configuration:</td>
                    <td class="value">
                        {str(reaction_wheels.get('configuration', 'n/a')).upper()} 
                        ({reaction_wheels.get('wheel_count', 'n/a')} wheels)
                    </td>
                </tr>
                <tr>
                    <td class="label">Single Wheel Mass:</td>
                    <td class="value">{fmt(reaction_wheels.get('wheel_mass'))} kg</td>
                </tr>
                <tr>
                    <td class="label">Wheel Dimensions (r, h):</td>
                    <td class="value">{fmt(reaction_wheels.get('wheel_radius'))} m, {fmt(reaction_wheels.get('wheel_height'))} m</td>
                </tr>
            </table>

            <h2> Total Inertia Tensor [kg·m²]</h2>
            <p style="color: #888; font-size: 11px; margin-top: 2px;">Includes body inertia and reaction wheels Steiner correction offset:</p>
            <table class="tensor-table">
                <tr>
                    <td>{fmt(total_tensor[0, 0], '{:.6f}')}</td>
                    <td>{fmt(total_tensor[0, 1], '{:.6f}')}</td>
                    <td>{fmt(total_tensor[0, 2], '{:.6f}')}</td>
                </tr>
                <tr>
                    <td>{fmt(total_tensor[1, 0], '{:.6f}')}</td>
                    <td>{fmt(total_tensor[1, 1], '{:.6f}')}</td>
                    <td>{fmt(total_tensor[1, 2], '{:.6f}')}</td>
                </tr>
                <tr>
                    <td>{fmt(total_tensor[2, 0], '{:.6f}')}</td>
                    <td>{fmt(total_tensor[2, 1], '{:.6f}')}</td>
                    <td>{fmt(total_tensor[2, 2], '{:.6f}')}</td>
                </tr>
            </table>
        </body>
        </html>
        """

        self.summary_browser.setHtml(html_content)

    def validate_inputs(self) -> Dict[str, str]:
        return validate_satellite_configuration_data(self.get_configuration_data())

    def _on_field_finished(self) -> None:
        """Called when a field loses focus (editingFinished) — validate only the current field."""
        if self._silent_update:
            return
        sender = self.sender()
        if sender is None or not isinstance(sender, QWidget):
            return

        if isinstance(sender, QLineEdit) and not sender.text().strip():
            self._clear_widget_errors(sender)
            self._emit_change(mark_errors=False)
            return

        all_errors = self.validate_inputs()
        current_keys = self._get_error_keys_for_widget(sender)
        current_errors = {
            key: msg for key, msg in all_errors.items() if key in current_keys
        }

        self._clear_widget_errors(sender)
        if current_errors:
            self.mark_errors(current_errors, replace_all=False)

        self._emit_change(mark_errors=False)

    def _get_field_map(self) -> Dict[str, Any]:
        """Maps Qt widgets to their corresponding configuration keys for error marking."""
        return {
            "mass": self.input_mass,
            "dim_a": self.input_dimensions[0] if len(self.input_dimensions) > 0 else None,
            "dim_b": self.input_dimensions[1] if len(self.input_dimensions) > 1 else None,
            "dim_h": self.input_dimensions[2] if len(self.input_dimensions) > 2 else None,
            "dimensions": self.input_dimensions,
            "inertia_tensor": self.input_inertia_tensor,
            "coil_turns": self.input_coil_turns,
            "coil_area": self.input_coil_area,
            "max_current": self.input_max_current,
            "wheel_count": self.input_wheel_count,
            "wheel_mass": self.input_wheel_mass,
            "wheel_radius": self.input_wheel_radius,
            "wheel_height": self.input_wheel_height,
            "wheel_max_speed": self.input_wheel_max_speed,
        }

    def _get_error_keys_for_widget(self, widget: QWidget) -> List[str]:
        """Return validator error keys associated with the provided widget."""
        if widget == self.input_mass:
            return ["mass"]
        if widget in self.input_dimensions:
            index = self.input_dimensions.index(widget)
            return ["dim_a", "dim_b", "dim_h"][index:index+1] + ["dimensions"]
        if widget in self.input_inertia_tensor:
            return ["inertia_tensor"]
        if widget == self.input_coil_turns:
            return ["coil_turns"]
        if widget == self.input_coil_area:
            return ["coil_area"]
        if widget == self.input_max_current:
            return ["max_current"]
        if widget == self.input_wheel_count:
            return ["wheel_count"]
        if widget == self.input_wheel_mass:
            return ["wheel_mass"]
        if widget == self.input_wheel_radius:
            return ["wheel_radius"]
        if widget == self.input_wheel_height:
            return ["wheel_height"]
        if widget == self.input_wheel_max_speed:
            return ["wheel_max_speed"]
        if widget == self.input_reaction_configuration:
            return ["wheel_configuration", "wheel_count"]
        return []

    def clear_errors(self) -> None:
        """Resets the error state of all input fields, removing any error highlights and tooltips."""
        field_map = self._get_field_map()
        for target in field_map.values():
            widgets = target if isinstance(target, (list, tuple)) else [target]
            for widget in widgets:
                self._reset_widget_style(widget)

    def _clear_widget_errors(self, widget: QWidget) -> None:
        """Clear errors for the provided widget or grouping (dimensions / inertia tensor)."""
        if widget is None:
            return

        # Jeśli edytujemy pole wymiarów lub tensora bezwładności, czyścimy całą grupę
        if widget in self.input_dimensions:
            targets = self.input_dimensions
        elif hasattr(self, "input_inertia_tensor") and widget in self.input_inertia_tensor:
            targets = self.input_inertia_tensor
        else:
            targets = [widget]

        for target_widget in targets:
            self._reset_widget_style(target_widget)

    def _reset_widget_style(self, widget: QWidget) -> None:
        """Helper to reset styling and tooltips on a widget."""
        if widget and widget.property("hasError"):
            widget.setProperty("hasError", False)
            widget.setToolTip("")
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def mark_errors(self, errors: Dict[str, str], replace_all: bool = True) -> None:
        """Marks only the fields that contain errors."""
        if replace_all:
            self.clear_errors()

        if not errors:
            return

        field_map = self._get_field_map()

        for error_key, error_msg in errors.items():
            target = field_map.get(error_key)
            if not target:
                continue

            widgets = target if isinstance(target, (list, tuple)) else [target]

            for widget in widgets:
                if widget:
                    widget.setProperty("hasError", True)
                    widget.setToolTip(error_msg)
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)