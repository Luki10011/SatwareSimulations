import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QGraphicsProxyWidget,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from utils.ui.ui_utils import apply_dark_title_bar

class StandalonePlotWindow(QWidget):
    """Niezależne okno dla wykresu wyciągniętego opcją Pop-out."""

    def __init__(self, card_info: dict, on_close_callback, parent=None):
        super().__init__(parent)
        self.card_info = card_info
        self.on_close_callback = on_close_callback

        signal_name = card_info["combo_y"].currentText()
        self.setWindowTitle(f"Plot #{card_info['id']} - {signal_name}")
        self.resize(700, 450)
        apply_dark_title_bar(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground("#121212")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel("bottom", "Time (t) [s]")
        self.plot_widget.setLabel("left", signal_name)

        layout.addWidget(self.plot_widget)

        self.curves = {}
        self.rebuild_curves()

    def rebuild_curves(self) -> None:
        self.plot_widget.clear()
        self.curves.clear()

        selected_option = self.card_info["combo_y"].currentText()
        signal_keys = SimulationPlotsPanel.Y_AXIS_OPTIONS.get(
            selected_option, []
        )

        for idx, key in enumerate(signal_keys):
            color = SimulationPlotsPanel.CURVE_COLORS[
                idx % len(SimulationPlotsPanel.CURVE_COLORS)
            ]
            pen = pg.mkPen(color=color, width=2)
            curve = self.plot_widget.plot(name=key, pen=pen)
            curve.setSkipFiniteCheck(True)
            self.curves[key] = curve

    def update_telemetry(self, history: dict, max_points: int = 2000) -> None:
        if not history or "time" not in history:
            return
        time_data = history["time"][-max_points:]
        for key, curve in self.curves.items():
            if key in history:
                y_data = history[key][-max_points:]
                curve.setData(time_data, y_data)

    def closeEvent(self, event) -> None:
        self.on_close_callback(self.card_info)
        super().closeEvent(event)


class SimulationPlotsPanel(QWidget):
    """Wysoce wydajny panel wykresów z dopracowanym wyglądem nagłówków i widokiem pustym (Empty State)."""

    MAX_PLOTS = 3

    Y_AXIS_OPTIONS = {
        "Euler Angles (ϕ, θ, ψ) [deg]": ["roll", "pitch", "yaw"],
        "Angular Velocity (ωx, ωy, ωz) [deg/s]": [
            "omega_x",
            "omega_y",
            "omega_z",
        ],
        # "ECI Position (X, Y, Z) [km]": ["pos_x", "pos_y", "pos_z"],
        # "ECI Velocity (Vx, Vy, Vz) [km/s]": ["vel_x", "vel_y", "vel_z"],
        "Quaternion (q0, q1, q2, q3)": ["q0", "q1", "q2", "q3"],
        "Magnetic Field (Bx, By, Bz) [T]" : ["b_body_x", "b_body_y", "b_body_z"],
        "Control Current (Ix, Iy, Iz) [A]" : ["i_ctrl_x", "i_ctrl_y", "i_ctrl_z"],
        "Bdot Torque (tau_x, tau_y, tau_z) [N]" : ["tau_ctrl_x", "tau_ctrl_y", "tau_ctrl_z"],
    }

    CURVE_COLORS = ["#FF5252", "#4CAF50", "#2196F3", "#FFEB3B"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cards = []
        self._card_counter = 0
        self.setup_ui()

    def setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # 1. Pasek informacyjny i akcji
        info_label = QLabel(
            "Configure real-time telemetry plots. Rendered in a single unified GPU scene for maximum fluidity."
        )
        info_label.setStyleSheet("color: #b0bec5; font-size: 12px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        action_bar = QHBoxLayout()
        self.btn_add_plot = QPushButton("+ Add Plot")
        self.btn_add_plot.setStyleSheet(
            "font-weight: bold; padding: 6px 12px;"
        )
        self.btn_add_plot.clicked.connect(self.add_plot_card)

        self.btn_clear_all = QPushButton("Clear All Plots")
        self.btn_clear_all.clicked.connect(self.clear_all_plots)

        self.lbl_plot_count = QLabel(f"Plots: 0 / {self.MAX_PLOTS}")
        self.lbl_plot_count.setStyleSheet(
            "color: #888888; font-weight: bold;"
        )

        action_bar.addWidget(self.btn_add_plot)
        action_bar.addWidget(self.btn_clear_all)
        action_bar.addStretch()
        action_bar.addWidget(self.lbl_plot_count)

        main_layout.addLayout(action_bar)

        # 2. Widok pusty (Empty State) - wyświetlany gdy brak aktywnych wykresów
        self.empty_state = QLabel(
            "No active plots in main panel.\nClick '+ Add Plot' above or restore popped-out windows."
        )
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet("""
            QLabel {
                background-color: #2a2a2a;
                color: #666666;
                font-size: 13px;
                border: 1px dashed #2a2a2a;
                border-radius: 6px;
                padding: 40px;
            }
        """)
        main_layout.addWidget(self.empty_state, stretch=1)

        # 3. Canvas ze sceną wykresów
        self.glw = pg.GraphicsLayoutWidget()
        self.glw.setBackground("#1c1b1b")
        # Wymuszenie zachowania odstępów w siatce układu GraphicsLayoutWidget
        self.glw.ci.layout.setSpacing(12)
        main_layout.addWidget(self.glw, stretch=1)

        # Domyślnie utwórz jeden wykres
        self.add_plot_card()

    def add_plot_card(self) -> None:
        if len(self.cards) >= self.MAX_PLOTS:
            return

        self._card_counter += 1
        card_id = self._card_counter

        # Własny kontener na nagłówek z wymuszonym tłem i ramką
        header_widget = QWidget()
        header_widget.setObjectName("headerWidget")
        header_widget.setAutoFillBackground(True)
        header_widget.setStyleSheet("""
            #headerWidget {
                background-color: #2a2a2a;
                border: 1px solid #333333;
                border-radius: 4px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 11px;
            }
        """)

        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 4, 8, 4)
        header_layout.setSpacing(8)

        lbl_title = QLabel(f"Plot #{card_id} - Y:")
        header_layout.addWidget(lbl_title)

        combo_y = QComboBox()
        combo_y.addItems(list(self.Y_AXIS_OPTIONS.keys()))
        combo_y.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        combo_y.setView(QListView())
        combo_y.setStyleSheet("""
            QComboBox {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #444444;
                border-radius: 3px;
                padding: 3px 6px;
            }
            QComboBox QAbstractItemView {
                background-color: #2a2a2a;
                color: #ffffff;
                selection-background-color: #007acc;
                selection-color: #ffffff;
                border: 1px solid #555555;
                outline: 0px;
            }
        """)
        header_layout.addWidget(combo_y)

        btn_popout = QPushButton("Pop-out ↗")
        btn_popout.setStyleSheet(
            "QPushButton { background-color: #2a2a2a; color: #ccc; border: 1px solid #444; padding: 3px 8px; border-radius: 3px; }"
            "QPushButton:hover { background-color: #3a3a3a; color: #fff; }"
        )
        header_layout.addWidget(btn_popout)

        btn_remove = QPushButton("✕")
        btn_remove.setFixedSize(24, 24)
        btn_remove.setStyleSheet(
            "QPushButton { background-color: #331111; color: #ff6666; border-radius: 3px; font-weight: bold; }"
            "QPushButton:hover { background-color: #551111; }"
        )
        header_layout.addWidget(btn_remove)

        header_proxy = QGraphicsProxyWidget()
        header_proxy.setWidget(header_widget)

        plot_item = pg.PlotItem()
        plot_item.showGrid(x=True, y=True, alpha=0.3)
        plot_item.setLabel("bottom", "Time (t) [s]")
        plot_item.getAxis("left").setWidth(25)
        plot_item.setClipToView(True)
        plot_item.setDownsampling(auto=True, mode="peak")

        card_info = {
            "id": card_id,
            "header_widget": header_widget,
            "header_proxy": header_proxy,
            "combo_y": combo_y,
            "btn_popout": btn_popout,
            "btn_remove": btn_remove,
            "plot_item": plot_item,
            "curves": {},
            "legend": None,
            "is_popped_out": False,
            "popout_window": None,
        }

        combo_y.currentTextChanged.connect(
            lambda: self._on_signal_changed(card_info)
        )
        btn_popout.clicked.connect(lambda: self.toggle_popout(card_info))
        btn_remove.clicked.connect(lambda: self.remove_plot_card(card_info))

        self.cards.append(card_info)
        self._relayout_canvas()
        self._rebuild_curves(card_info)
        self._update_controls_state()

    def toggle_popout(self, card: dict) -> None:
        if not card["is_popped_out"]:
            card["is_popped_out"] = True
            card["btn_popout"].setText("Pop-in ↙")

            win = StandalonePlotWindow(card, self._on_popout_closed)
            card["popout_window"] = win
            win.show()
        else:
            if card["popout_window"]:
                card["popout_window"].close()

        self._relayout_canvas()

    def _on_popout_closed(self, card: dict) -> None:
        card["is_popped_out"] = False
        card["popout_window"] = None
        card["btn_popout"].setText("Pop-out ↗")
        self._relayout_canvas()

    def _on_signal_changed(self, card: dict) -> None:
        self._rebuild_curves(card)
        if card["is_popped_out"] and card["popout_window"]:
            card["popout_window"].rebuild_curves()

    def _relayout_canvas(self) -> None:
        """Przebudowuje siatkę i przełącza widok na Empty State jeśli brak widocznych wykresów."""
        self.glw.ci.clear()
        visible_row = 0

        for card in self.cards:
            if not card["is_popped_out"]:
                self.glw.addItem(
                    card["header_proxy"], row=visible_row * 2, col=0
                )
                self.glw.addItem(
                    card["plot_item"], row=visible_row * 2 + 1, col=0
                )
                visible_row += 1

        # Przełączanie między płótnem GraphicsLayoutWidget a widokiem Empty State
        if visible_row == 0:
            self.glw.hide()
            self.empty_state.show()
        else:
            self.empty_state.hide()
            self.glw.show()

    def _rebuild_curves(self, card: dict) -> None:
        plot_item = card["plot_item"]
        plot_item.clear()
        card["curves"].clear()

        if card["legend"] is not None:
            try:
                plot_item.removeItem(card["legend"])
            except Exception:
                pass
            card["legend"] = None

        card["legend"] = plot_item.addLegend(offset=(10, 10))
        selected_option = card["combo_y"].currentText()
        signal_keys = self.Y_AXIS_OPTIONS.get(selected_option, [])

        for idx, key in enumerate(signal_keys):
            color = self.CURVE_COLORS[idx % len(self.CURVE_COLORS)]
            pen = pg.mkPen(color=color, width=2)
            curve = plot_item.plot(name=key, pen=pen)
            curve.setSkipFiniteCheck(True)
            card["curves"][key] = curve

        # plot_item.setLabel("left", selected_option)

    def remove_plot_card(self, card: dict) -> None:
        if card in self.cards:
            if card["is_popped_out"] and card["popout_window"]:
                card["popout_window"].close()

            self.cards.remove(card)
            card["header_widget"].deleteLater()
            self._relayout_canvas()
            self._update_controls_state()

    def clear_all_plots(self) -> None:
        for card in list(self.cards):
            if card["is_popped_out"] and card["popout_window"]:
                card["popout_window"].close()
            card["header_widget"].deleteLater()
        self.cards.clear()
        self.glw.ci.clear()
        self._relayout_canvas()
        self._update_controls_state()

    def update_telemetry(self, history: dict, max_points: int = 10000) -> None:
        if not history or "time" not in history:
            return

        time_data = history["time"][-max_points:]

        for card in self.cards:
            if card["is_popped_out"] and card["popout_window"]:
                card["popout_window"].update_telemetry(history, max_points)
            elif self.isVisible():
                for key, curve in card["curves"].items():
                    if key in history:
                        y_data = history[key][-max_points:]
                        curve.setData(time_data, y_data)

    def _update_controls_state(self) -> None:
        count = len(self.cards)
        self.lbl_plot_count.setText(f"Plots: {count} / {self.MAX_PLOTS}")
        self.btn_add_plot.setEnabled(count < self.MAX_PLOTS)

    def reset(self):
        self.clear_all_plots()