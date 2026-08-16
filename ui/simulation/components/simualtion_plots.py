from typing import Dict, List, Optional
import pyqtgraph as pg
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class PopOutPlotWindow(QMainWindow):
    """Niezależne okno do wyświetlania wykresu na drugim monitorze."""

    closed = pyqtSignal()

    def __init__(self, title: str, plot_widget: pg.PlotWidget, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"SatwareSimulations - {title}")
        self.resize(800, 500)
        self.setStyleSheet("background-color: #121212;")

        self.setCentralWidget(plot_widget)

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)


class PlotCardWidget(QWidget):
    """Pojedynczy kafelek wykresu z czasem na osi X i wybranym sygnałem na osi Y."""

    remove_requested = pyqtSignal(object)

    Y_AXIS_OPTIONS = {
        "Euler Angles (ϕ, θ, ψ) [deg]": ["roll", "pitch", "yaw"],
        "Angular Velocity (ωx, ωy, ωz) [deg/s]": ["omega_x", "omega_y", "omega_z"],
        "ECI Position (X, Y, Z) [km]": ["pos_x", "pos_y", "pos_z"],
        "ECI Velocity (Vx, Vy, Vz) [km/s]": ["vel_x", "vel_y", "vel_z"],
        "Quaternion (q0, q1, q2, q3)": ["q0", "q1", "q2", "q3"],
    }

    def __init__(self, card_id: int, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.popout_window: Optional[PopOutPlotWindow] = None
        self.is_popped_out = False

        self.setup_ui()

    def setup_ui(self) -> None:
        self.setObjectName("plotCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # 1. PASEK KONTROLNY KARTY (HEADER)
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        header_layout.addWidget(QLabel("Signal (Y):"))
        self.combo_y = QComboBox()
        self.combo_y.addItems(list(self.Y_AXIS_OPTIONS.keys()))
        self.combo_y.currentTextChanged.connect(self._on_y_axis_changed)
        self.combo_y.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.combo_y.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self.combo_y, stretch=1)

        self.btn_popout = QPushButton("Pop-out ↗")
        self.btn_popout.clicked.connect(self._toggle_popout)
        header_layout.addWidget(self.btn_popout)

        self.btn_remove = QPushButton("✕")
        self.btn_remove.setObjectName("btnRemovePlot")
        self.btn_remove.clicked.connect(lambda: self.remove_requested.emit(self))
        header_layout.addWidget(self.btn_remove)

        layout.addLayout(header_layout)

        # 2. WIDGET WYKRESU (PYQTGRAPH)
        self.plot_container = QWidget()
        container_layout = QVBoxLayout(self.plot_container)
        container_layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#121212")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.addLegend(offset=(10, 10))
        self.plot_widget.setFixedHeight(240)

        self.plot_widget.setLabel("bottom", "Time (t) [s]")
        self.plot_widget.setLimits(xMin=0)
        self.plot_widget.setXRange(0, 10, padding=0)

        container_layout.addWidget(self.plot_widget)
        layout.addWidget(self.plot_container)

        self._update_plot_titles()

    def _on_y_axis_changed(self) -> None:
        self.plot_widget.clear()
        self.plot_widget.addLegend(offset=(10, 10))
        self._update_plot_titles()

    def _update_plot_titles(self) -> None:
        y_title = self.combo_y.currentText()
        self.plot_widget.setLabel("left", y_title)
        self.plot_widget.setLabel("bottom", "Time (t) [s]")

    def _toggle_popout(self) -> None:
        if not self.is_popped_out:
            self.plot_container.layout().removeWidget(self.plot_widget)

            # Odblokowanie wysokości dla okna zewnętrznego
            self.plot_widget.setMaximumHeight(16777215)
            self.plot_widget.setMinimumHeight(0)

            self.popout_window = PopOutPlotWindow(
                title=f"Plot #{self.card_id} - {self.combo_y.currentText()}",
                plot_widget=self.plot_widget,
                parent=self,
            )
            self.popout_window.closed.connect(self._on_popout_closed)
            self.popout_window.show()

            self.btn_popout.setText("Dock ↙")
            self.is_popped_out = True
        else:
            self._dock_back()

    def _on_popout_closed(self) -> None:
        if self.is_popped_out:
            self._dock_back()

    def _dock_back(self) -> None:
        if self.popout_window:
            try:
                self.popout_window.closed.disconnect(self._on_popout_closed)
            except (TypeError, RuntimeError):
                pass

            # Wyciągnięcie widgetu z okna przed jego zniszczeniem (zapobiega usuwaniu C++)
            self.popout_window.takeCentralWidget()
            self.popout_window.close()
            self.popout_window = None

        # Przywrócenie stałej wysokości i wpięcie z powrotem do kafelka
        self.plot_widget.setParent(self.plot_container)
        self.plot_widget.setFixedHeight(240)
        self.plot_container.layout().addWidget(self.plot_widget)

        self.btn_popout.setText("Pop-out ↗")
        self.is_popped_out = False



class SimulationPlotsPanel(QWidget):
    """Główna zakładka zarządzająca dynamiczną listą wykresów."""

    MAX_PLOTS = 6  # Limit bezpieczeństwa dla zachowania płynności renderowania

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards: List[PlotCardWidget] = []
        self._card_counter = 0

        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(10)

        info_label = QLabel(
            "Configure real-time telemetry plots. You can dynamically add up to 6 charts, "
            "select specific telemetry signals for both axes, and pop out charts into standalone windows."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #b0bec5; font-size: 12px;")
        main_layout.addWidget(info_label)

        # PASEK AKCJI
        action_bar = QHBoxLayout()
        self.btn_add_plot = QPushButton("+ Add Plot")
        self.btn_add_plot.setStyleSheet("font-weight: bold; padding: 6px 12px;")
        self.btn_add_plot.clicked.connect(self.add_plot_card)

        self.btn_clear_all = QPushButton("Clear All Plots")
        self.btn_clear_all.clicked.connect(self.clear_all_plots)

        self.lbl_plot_count = QLabel(f"Plots: 0 / {self.MAX_PLOTS}")
        self.lbl_plot_count.setStyleSheet("color: #888888; font-weight: bold;")

        action_bar.addWidget(self.btn_add_plot)
        action_bar.addWidget(self.btn_clear_all)
        action_bar.addStretch()
        action_bar.addWidget(self.lbl_plot_count)

        main_layout.addLayout(action_bar)

        # SCROLL AREA NA KAFELKI Z NADAJĄCYMI SIĘ DO QSS OBJECT NAME
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("plotsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        # self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("plotsScrollContent")
        self.cards_layout = QVBoxLayout(self.scroll_content)
        self.cards_layout.setContentsMargins(0, 0, 6, 0)
        self.cards_layout.setSpacing(10)
        self.cards_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        self.add_plot_card()

    def add_plot_card(self) -> None:
        if len(self.cards) >= self.MAX_PLOTS:
            return

        self._card_counter += 1
        card = PlotCardWidget(card_id=self._card_counter, parent=self)
        card.remove_requested.connect(self.remove_plot_card)

        # Wstawienie kafelka przed stretch
        self.cards_layout.insertWidget(len(self.cards), card)
        self.cards.append(card)

        self._update_controls_state()

    def remove_plot_card(self, card: PlotCardWidget) -> None:
        if card in self.cards:
            if card.is_popped_out and card.popout_window:
                card.popout_window.close()

            self.cards_layout.removeWidget(card)
            self.cards.remove(card)
            card.deleteLater()

            self._update_controls_state()

    def clear_all_plots(self) -> None:
        for card in list(self.cards):
            self.remove_plot_card(card)

    def _update_controls_state(self) -> None:
        count = len(self.cards)
        self.lbl_plot_count.setText(f"Plots: {count} / {self.MAX_PLOTS}")
        self.btn_add_plot.setEnabled(count < self.MAX_PLOTS)