from typing import List

from PyQt6.QtCore import QLocale, Qt
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class SatelliteControls(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        form_container = QWidget()
        form_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Maximum,
        )

        form_layout = QFormLayout(form_container)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(8)

        form_layout.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )

        form_layout.setFormAlignment(
            Qt.AlignmentFlag.AlignTop
            | Qt.AlignmentFlag.AlignLeft
        )

        self.header_label = QLabel("Define Mechanical Parameters")
        self.header_label.setStyleSheet(
            "font-size: 14px;"
            "font-weight: bold;"
            "color: #ffffff;"
            "margin-bottom: 6px;"
        )
        self.header_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        form_layout.addRow(self.header_label)

        validator = QDoubleValidator(self)
        validator.setLocale(
            QLocale(
                QLocale.Language.English,
                QLocale.Country.UnitedStates,
            )
        )
        validator.setNotation(
            QDoubleValidator.Notation.StandardNotation
        )

        self.input_mass, widget_mass = self._create_input_with_info(
            placeholder_text="",
        )

        self.input_size, widget_size = self._create_input_size(
            placeholder_text="",
        )

        (
            self.input_inertia_tensor,
            widget_inertia_tensor,
        ) = self._create_input_inertia_tensor(
            placeholder_text="",
        )

        self.input_mass.setValidator(validator)

        for input_field in self.input_size:
            input_field.setValidator(validator)

        for input_field in self.input_inertia_tensor:
            input_field.setValidator(validator)

        mass_label = self._create_centered_form_label(
            "Mass of the satellite (m):"
        )

        size_label = self._create_centered_form_label(
            "Satellite dimensions (a, b, h):"
        )

        inertia_tensor_label = self._create_centered_form_label(
            "Inertia tensor (J):"
        )

        form_layout.addRow(
            mass_label,
            widget_mass,
        )

        form_layout.addRow(
            size_label,
            widget_size,
        )


        form_layout.addRow(
            inertia_tensor_label,
            widget_inertia_tensor,
        )

        self.btn_calculate_inertia_tensor = QPushButton("Calculate J based on size")
        self.btn_calculate_inertia_tensor.clicked.connect(self._calculate_inertia_tensor)
        self.btn_calculate_inertia_tensor.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        form_layout.addRow("", self.btn_calculate_inertia_tensor)

        main_layout.addWidget(
            form_container,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        # Keep the form at the top without stretching its rows
        main_layout.addStretch(1)

    def _create_centered_form_label(self, text: str) -> QWidget:
        """
        Creates a label container that vertically centers the label
        without causing the form row to expand.
        """
        container = QWidget()

        container.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        label = QLabel(text)
        label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addStretch(1)

        layout.addWidget(
            label,
            alignment=(
                Qt.AlignmentFlag.AlignLeft
                | Qt.AlignmentFlag.AlignVCenter
            ),
        )

        layout.addStretch(1)

        return container

    def _create_input_size(
        self,
        placeholder_text: str,
        tooltip_html: str = None,
    ) -> tuple[List[QLineEdit], QWidget]:
        """
        Creates a horizontal group of three input fields.
        """
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        size_inputs: List[QLineEdit] = []

        horizontal_layout = QHBoxLayout(container)
        horizontal_layout.setContentsMargins(0, 0, 0, 0)
        horizontal_layout.setSpacing(6)

        for _ in range(3):
            line_edit = QLineEdit()
            line_edit.setPlaceholderText(placeholder_text)

            line_edit.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            horizontal_layout.addWidget(
                line_edit,
                stretch=1,
            )

            size_inputs.append(line_edit)

        if tooltip_html:
            info_icon = QLabel("ⓘ")
            info_icon.setObjectName("InfoIcon")
            info_icon.setToolTip(tooltip_html)

            info_icon.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            info_icon.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )

            horizontal_layout.addWidget(
                info_icon,
                alignment=Qt.AlignmentFlag.AlignVCenter,
            )

        return size_inputs, container

    def _create_input_inertia_tensor(
        self,
        placeholder_text: str,
        tooltip_html: str = None,
    ) -> tuple[List[QLineEdit], QWidget]:
        """
        Creates a compact 3x3 group of input fields.
        """
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        inertia_tensor_inputs: List[QLineEdit] = []

        vertical_layout = QVBoxLayout(container)
        vertical_layout.setContentsMargins(0, 0, 0, 0)
        vertical_layout.setSpacing(6)
        vertical_layout.setSizeConstraint(
            QVBoxLayout.SizeConstraint.SetFixedSize
        )

        for _ in range(3):
            row_container = QWidget()
            row_container.setSizePolicy(
                QSizePolicy.Policy.Expanding,
                QSizePolicy.Policy.Fixed,
            )

            inertia_row_layout = QHBoxLayout(row_container)
            inertia_row_layout.setContentsMargins(0, 0, 0, 0)
            inertia_row_layout.setSpacing(6)

            for _ in range(3):
                line_edit = QLineEdit()
                line_edit.setPlaceholderText(placeholder_text)

                line_edit.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Fixed,
                )

                inertia_row_layout.addWidget(
                    line_edit,
                    stretch=1,
                )

                inertia_tensor_inputs.append(line_edit)

            vertical_layout.addWidget(row_container)

        return inertia_tensor_inputs, container

    def _create_input_with_info(
        self,
        placeholder_text: str,
        tooltip_html: str = None,
    ) -> tuple[QLineEdit, QWidget]:
        """
        Creates a text input field with an optional information icon.

        Returns:
            A tuple containing the QLineEdit and its container QWidget.
        """
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        line_edit = QLineEdit()
        line_edit.setPlaceholderText(placeholder_text)

        line_edit.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        layout.addWidget(
            line_edit,
            stretch=1,
        )

        if tooltip_html:
            info_icon = QLabel("ⓘ")
            info_icon.setObjectName("InfoIcon")
            info_icon.setToolTip(tooltip_html)

            info_icon.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            info_icon.setSizePolicy(
                QSizePolicy.Policy.Fixed,
                QSizePolicy.Policy.Fixed,
            )

            layout.addWidget(
                info_icon,
                alignment=Qt.AlignmentFlag.AlignVCenter,
            )

        return line_edit, container

    def _calculate_inertia_tensor(self) -> None:
        print("Calculating")