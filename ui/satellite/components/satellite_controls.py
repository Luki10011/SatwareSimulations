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
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
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
)


class SatelliteControls(QWidget):
    configurationChanged = pyqtSignal(dict)
    saveRequested = pyqtSignal()
    loadRequested = pyqtSignal()
    resetRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self._set_defaults()
        self._refresh_summary()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        self.header_label = QLabel("Satellite Configuration Editor")
        self.header_label.setObjectName("satelliteHeaderLabel")
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
        self._reaction_tab = QWidget(self)
        self._summary_tab = QWidget(self)

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
        self.btn_load = QPushButton("Load")
        self.btn_reset = QPushButton("Reset")
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_load)
        button_row.addWidget(self.btn_reset)
        main_layout.addLayout(button_row)

        self.btn_save.clicked.connect(self._emit_save_request)
        self.btn_load.clicked.connect(self._emit_load_request)
        self.btn_reset.clicked.connect(self._emit_reset_request)

        self.btn_save.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_load.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.btn_reset.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _build_mechanical_tab(self) -> None:
        form_layout = QFormLayout(self._mechanical_tab)
        form_layout.setContentsMargins(8, 8, 8, 8)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)

        # Standard double validator setup
        us_locale = QLocale(QLocale.Language.English, QLocale.Country.UnitedStates)

        mass_val = QDoubleValidator(MASS_MIN, MASS_MAX, 3, self)
        mass_val.setLocale(us_locale)
        mass_val.setNotation(QDoubleValidator.Notation.StandardNotation)

        dim_val = QDoubleValidator(DIM_MIN, DIM_MAX, 3, self)
        dim_val.setLocale(us_locale)
        dim_val.setNotation(QDoubleValidator.Notation.StandardNotation)

        inertia_val = QDoubleValidator(0.0, 10.0, 6, self)
        inertia_val.setLocale(us_locale)
        inertia_val.setNotation(QDoubleValidator.Notation.StandardNotation)

        turns_val = QIntValidator(COIL_TURNS_MIN, COIL_TURNS_MAX, self)

        area_val = QDoubleValidator(COIL_AREA_MIN, COIL_AREA_MAX, 4, self)
        area_val.setLocale(us_locale)

        current_val = QDoubleValidator(MAX_CURRENT_MIN, MAX_CURRENT_MAX, 2, self)
        current_val.setLocale(us_locale)

        self.mechanical_header_label = QLabel("Mechanical Properties")
        self.mechanical_header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px;"
        )
        form_layout.addRow(self.mechanical_header_label)

        self.input_mass = self._create_line_edit(mass_val)
        form_layout.addRow(f"Mass [kg]:", self.input_mass)

        self.input_dimensions = [self._create_line_edit(dim_val) for _ in range(3)]
        dimensions_container = self._create_horizontal_inputs(self.input_dimensions)
        form_layout.addRow(f"Dimensions [m]:", dimensions_container)

        self.input_inertia_tensor = [self._create_line_edit(inertia_val) for _ in range(9)]
        inertia_container = self._create_grid_inputs(self.input_inertia_tensor, 3)
        form_layout.addRow("Inertia tensor [kg·m²]:", inertia_container)

        self.btn_calculate_inertia_tensor = QPushButton("Calculate J based on size \\& mass")
        self.btn_calculate_inertia_tensor.clicked.connect(self._calculate_inertia_tensor)
        form_layout.addRow("", self.btn_calculate_inertia_tensor)

        self.electromagnetic_header_label = QLabel("Electromagnetic Properties")
        self.electromagnetic_header_label.setStyleSheet(
            "font-size: 14px; font-weight: bold; color: #ffffff; margin-bottom: 6px; margin-top: 10px;"
        )
        form_layout.addRow(self.electromagnetic_header_label)

        self.input_coil_turns = self._create_line_edit(turns_val)
        self.input_coil_area = self._create_line_edit(area_val)
        self.input_max_current = self._create_line_edit(current_val)
        form_layout.addRow(f"Coil turns:", self.input_coil_turns)
        form_layout.addRow(f"Coil area [m²]:", self.input_coil_area)
        form_layout.addRow(f"Max current [A]:", self.input_max_current)

    def _build_reaction_tab(self) -> None:
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
        self.input_wheel_com_offset = [self._create_line_edit(double_validator) for _ in range(3)]
        form_layout.addRow("Wheel mass [kg]:", self.input_wheel_mass)
        form_layout.addRow("Wheel radius [m]:", self.input_wheel_radius)
        form_layout.addRow("Wheel height [m]:", self.input_wheel_height)
        form_layout.addRow("Wheel COM offset [m]:", self._create_horizontal_inputs(self.input_wheel_com_offset))
        form_layout.addRow("Max speed [rpm]:", self.input_wheel_max_speed)

        self._update_reaction_configuration_ui(self.input_reaction_configuration.currentText())

    def _build_summary_tab(self) -> None:
        layout = QVBoxLayout(self._summary_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        self.summary_browser = QTextBrowser(self)
        self.summary_browser.setObjectName("satelliteSummaryBrowser")
        self.summary_browser.setReadOnly(True)
        self.summary_browser.setStyleSheet(
            "background-color: #ffffff;"
            "color: #0f172a;"
            "border: 1px solid #cbd5e1;"
            "border-radius: 6px;"
            "padding: 8px;"
        )
        layout.addWidget(self.summary_browser)

    def _create_line_edit(self, validator) -> QLineEdit:
        line_edit = QLineEdit(self)
        line_edit.setValidator(validator)
        line_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return line_edit

    def _create_horizontal_inputs(self, inputs: List[QLineEdit]) -> QWidget:
        container = QWidget(self)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for input_field in inputs:
            layout.addWidget(input_field, stretch=1)
        return container

    def _create_grid_inputs(self, inputs: List[QLineEdit], columns: int) -> QWidget:
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        for row_start in range(0, len(inputs), columns):
            row_inputs = inputs[row_start:row_start + columns]
            row_widget = QWidget(self)
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
            *self.input_wheel_com_offset,
        ]:
            field.textChanged.connect(self._refresh_summary)
            field.textChanged.connect(self._emit_change)
        self.input_reaction_configuration.currentTextChanged.connect(self._emit_change)

    def _emit_change(self) -> None:
        self.configurationChanged.emit(self.get_configuration_data())

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
        """Calculate solid box inertia tensor accounting for mass m and dimensions (a, b, h)."""
        dimensions = self._read_dimensions()
        try:
            mass = float(self.input_mass.text())
        except ValueError:
            mass = 0.0

        if dimensions is None or mass <= 0.0:
            return

        a, b, h = dimensions
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
        self.input_mass.setText("12.5")
        self.input_dimensions[0].setText("0.30")
        self.input_dimensions[1].setText("0.20")
        self.input_dimensions[2].setText("0.10")
        self.input_inertia_tensor[0].setText("0.020")
        self.input_inertia_tensor[4].setText("0.015")
        self.input_inertia_tensor[8].setText("0.010")
        self.input_coil_turns.setText("120")
        self.input_coil_area.setText("0.04")
        self.input_max_current.setText("2.5")
        self.input_reaction_configuration.setCurrentText("principal")
        self.input_wheel_count.setText("3")
        self.input_wheel_mass.setText("0.25")
        self.input_wheel_radius.setText("0.05")
        self.input_wheel_height.setText("0.02")
        self.input_wheel_com_offset[0].setText("0.003")
        self.input_wheel_com_offset[1].setText("0.002")
        self.input_wheel_com_offset[2].setText("0.001")
        self.input_wheel_max_speed.setText("6000")

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
        inertia_rows = []
        for row_index in range(0, 9, 3):
            inertia_rows.append([
                float(self.input_inertia_tensor[row_index + col_index].text() or 0.0)
                for col_index in range(3)
            ])
        return {
            "mechanical": {
                "mass": float(self.input_mass.text() or 0.0),
                "dimensions": dimensions or [0.3, 0.2, 0.1],
                "inertia_tensor": inertia_rows,
            },
            "electromagnetic": {
                "coil_turns": int(float(self.input_coil_turns.text() or 0)),
                "coil_area": float(self.input_coil_area.text() or 0.0),
                "max_current": float(self.input_max_current.text() or 0.0),
            },
            "reaction_wheels": {
                "configuration": self.input_reaction_configuration.currentText().strip().lower(),
                "wheel_count": int(float(self.input_wheel_count.text() or 0)),
                "wheel_mass": float(self.input_wheel_mass.text() or 0.0),
                "wheel_radius": float(self.input_wheel_radius.text() or 0.0),
                "wheel_height": float(self.input_wheel_height.text() or 0.0),
                "wheel_max_speed": float(self.input_wheel_max_speed.text() or 0.0),
                "com_offset": [float(field.text() or 0.0) for field in self.input_wheel_com_offset],
            },
        }

    def set_configuration_data(self, data: dict) -> None:
        mechanical = data.get("mechanical", {})
        electromagnetic = data.get("electromagnetic", {})
        reaction_wheels = data.get("reaction_wheels", {})

        self.input_mass.setText(str(mechanical.get("mass", "")))
        dimensions = mechanical.get("dimensions", [0.3, 0.2, 0.1])
        for index, value in enumerate(dimensions[:3]):
            self.input_dimensions[index].setText(str(value))

        inertia_tensor = mechanical.get("inertia_tensor", [])
        flat_values = []
        if isinstance(inertia_tensor, (list, tuple)):
            for row in inertia_tensor:
                if isinstance(row, (list, tuple)):
                    flat_values.extend([str(value) for value in row[:3]])
        for index, value in enumerate(flat_values[:9]):
            self.input_inertia_tensor[index].setText(value)
        self.input_coil_turns.setText(str(electromagnetic.get("coil_turns", "")))
        self.input_coil_area.setText(str(electromagnetic.get("coil_area", "")))
        self.input_max_current.setText(str(electromagnetic.get("max_current", "")))

        configuration = str(reaction_wheels.get("configuration", "principal")).lower()
        self.input_reaction_configuration.setCurrentText(configuration)
        self.input_wheel_count.setText(str(reaction_wheels.get("wheel_count", 3)))
        self.input_wheel_mass.setText(str(reaction_wheels.get("wheel_mass", "")))
        self.input_wheel_radius.setText(str(reaction_wheels.get("wheel_radius", "")))
        self.input_wheel_height.setText(str(reaction_wheels.get("wheel_height", "")))
        self.input_wheel_max_speed.setText(str(reaction_wheels.get("wheel_max_speed", "")))
        com_offset = reaction_wheels.get("com_offset", [0.003, 0.002, 0.001])
        for index, value in enumerate(com_offset[:3]):
            self.input_wheel_com_offset[index].setText(str(value))
        self._refresh_summary()

    def _refresh_summary(self) -> None:
        if not hasattr(self, "summary_browser"):
            return

        data = self.get_configuration_data()
        mechanical_tensor = data["mechanical"]["inertia_tensor"]
        reaction_wheels = data["reaction_wheels"]

        try:
            import numpy as np
            from core.physics.dataclasses.satellite_configuration import calculate_total_inertia_tensor

            total_tensor = calculate_total_inertia_tensor(
                mechanical_tensor=np.array(mechanical_tensor, dtype=float),
                mechanical_mass=data["mechanical"]["mass"],
                wheel_mass=reaction_wheels["wheel_mass"],
                wheel_radius=reaction_wheels["wheel_radius"],
                wheel_height=reaction_wheels["wheel_height"],
                wheel_count=reaction_wheels["wheel_count"],
                com_offset=np.array(reaction_wheels.get("com_offset", [0.003, 0.002, 0.001]), dtype=float),
            )
        except Exception:
            import numpy as np
            total_tensor = np.array(mechanical_tensor, dtype=float)

        lines = [
            "Satellite configuration summary",
            "===============================",
            f"Mass: {data['mechanical']['mass']:.3f} kg",
            f"Dimensions: a={data['mechanical']['dimensions'][0]:.3f} m, b={data['mechanical']['dimensions'][1]:.3f} m, h={data['mechanical']['dimensions'][2]:.3f} m",
            f"Coils: turns={data['electromagnetic']['coil_turns']}, area={data['electromagnetic']['coil_area']:.3f} m², Imax={data['electromagnetic']['max_current']:.3f} A",
            f"Reaction wheels: {reaction_wheels['configuration']} ({reaction_wheels['wheel_count']} wheels)",
            f"Wheel geometry: m={reaction_wheels['wheel_mass']:.3f} kg, r={reaction_wheels['wheel_radius']:.3f} m, h={reaction_wheels['wheel_height']:.3f} m",
            "",
            "Total inertia tensor [kg·m²] (Steiner correction):",
            f"Jxx = {total_tensor[0, 0]:.6f}",
            f"Jyy = {total_tensor[1, 1]:.6f}",
            f"Jzz = {total_tensor[2, 2]:.6f}",
            f"Jxy = {total_tensor[0, 1]:.6f}",
            f"Jxz = {total_tensor[0, 2]:.6f}",
            f"Jyz = {total_tensor[1, 2]:.6f}",
        ]
        self.summary_browser.setPlainText("\n".join(lines))

    def validate_inputs(self) -> List[str]:
        from core.physics.dataclasses.satellite_configuration import validate_satellite_configuration_data

        return validate_satellite_configuration_data(self.get_configuration_data())

    def _get_field_map(self) -> Dict[str, Any]:
        """Maps Qt widgets to their corresponding configuration keys for error marking."""
        return {
            "mass": self.input_mass,
            "dim_a": self.input_dimensions[0] if len(self.input_dimensions) > 0 else None,
            "dim_b": self.input_dimensions[1] if len(self.input_dimensions) > 1 else None,
            "dim_h": self.input_dimensions[2] if len(self.input_dimensions) > 2 else None,
            "dimensions": self.input_dimensions, # Cała lista pól wymiarów
            "inertia_tensor": self.input_inertia_tensor, # Cała macierz/lista pól
            "coil_turns": self.input_coil_turns,
            "coil_area": self.input_coil_area,
            "max_current": self.input_max_current,
            "wheel_count": self.input_wheel_count,
            "wheel_mass": self.input_wheel_mass,
            "wheel_radius": self.input_wheel_radius,
            "wheel_height": self.input_wheel_height,
            "wheel_max_speed": self.input_wheel_max_speed,
        }

    def clear_errors(self) -> None:
        """Resets the error state of all input fields, removing any error highlights and tooltips."""
        field_map = self._get_field_map()
        for target in field_map.values():
            widgets = target if isinstance(target, (list, tuple)) else [target]
            for widget in widgets:
                if widget and widget.property("hasError"):
                    widget.setProperty("hasError", False)
                    widget.setToolTip("")
                    widget.style().unpolish(widget)
                    widget.style().polish(widget)

    def mark_errors(self, errors: Dict[str, str]) -> None:
        """Marks only the fields that contain errors."""
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
                    widget.setToolTip(error_msg)  # Dodaje treść błędu w chmurce po najechaniu myszką
                    # widget.style().unpolish(widget)
                    # widget.style().polish(widget)