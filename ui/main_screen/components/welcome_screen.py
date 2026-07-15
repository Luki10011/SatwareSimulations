from PyQt6.QtWidgets import QFormLayout, QHBoxLayout, QSplitter, QStyle, QWidget, QVBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QPainter, QPixmap, QColor

class HeaderImageWidget(QWidget):
    """Widżet górnego panelu, który rysuje zdjęcie i nakłada filtr kontrastowy."""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.background_pixmap = QPixmap(image_path)

    def paintEvent(self, event):
        painter = QPainter(self)
        if not self.background_pixmap.isNull():
            painter.drawPixmap(self.rect(), self.background_pixmap)
            
            painter.fillRect(self.rect(), QColor(0, 0, 0, 90))
        else:
            painter.fillRect(self.rect(), QColor(30, 30, 30))
        super().paintEvent(event)

class QuickAccessItem(QWidget):
    from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QVBoxLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap


class QuickAccessItem(QWidget):

    activated = pyqtSignal()

    def __init__(self, title: str, description: str):
        super().__init__()

        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setStyleSheet("""
            QuickAccessItem {
                background-color: #252526;
                border: 1px solid #3a3a3a;
                border-radius: 8px;
            }

            QuickAccessItem:hover {
                background-color: #2d2d30;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        # Ikona
        icon_label = QLabel()
        icon_label.setFixedSize(32, 32)

        icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)

        icon = self.style().standardIcon(
            QStyle.StandardPixmap.SP_FileIcon
        )

        icon_label.setPixmap(icon.pixmap(32, 32))

        # Prawa część
        text_layout = QVBoxLayout()

        self.title_label = QLabel(
            f'{title}'
        )

        self.title_label.setWordWrap(True)

        self.title_label.setStyleSheet("""
            QLabel {
                color: #4ea3ff;
                font-size: 15px;
                font-weight: 600;
                border: none;
            }
        """)

        self.title_label.setOpenExternalLinks(False)
        

        description_label = QLabel(description)

        description_label.setWordWrap(True)
        description_label.setStyleSheet("""
            QLabel {
                color: #b8b8b8;
                font-size: 10px;
                border: none;
            }
        """)

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(description_label)

        layout.addWidget(icon_label, 0)
        layout.addLayout(text_layout, 1)

    def mousePressEvent(self, event):
        self.activated.emit()
        super().mousePressEvent(event)  

    def connectClick(self, function):
        self.activated.connect(function)


class MainScreenWelcome(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.right_widget = HeaderImageWidget("assets\\graphics\\space_background.jpg")
        
        upper_layout = QVBoxLayout(self.right_widget)
        upper_layout.setContentsMargins(40, 80, 40, 80)
        upper_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("SatWare Simulations")
        title.setFont(QFont("Arial", 48, QFont.Weight.Bold))
        title.setStyleSheet("""
            background: transparent; 
            color: #ffffff; 
            margin-bottom: 12px;
        """)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("An app that supports the design and analysis of CubeSat satellite missions.\n"
                          "Masters thesis")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setStyleSheet("""
            background: transparent; 
            color: #f0f0f0; 
            line-height: 150%;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        upper_layout.addWidget(title)
        upper_layout.addWidget(subtitle)

        left_widget = QSplitter(Qt.Orientation.Vertical)
        left_widget.setHandleWidth(0)

        self.upper_left_container = QWidget()
        self.bottom_left_container = QWidget()

        self._create_quick_access(self.upper_left_container)
        self._create_info_panel(self.bottom_left_container)
        
        left_widget.addWidget(self.upper_left_container)
        left_widget.addWidget(self.bottom_left_container)

        left_widget.setStretchFactor(0, 1)
        left_widget.setStretchFactor(1, 2)

        main_layout.addWidget(left_widget, stretch=35)
        main_layout.addWidget(self.right_widget, stretch=65)

    def _create_quick_access(self, widget):

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Quick Access")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
        """)

        layout.addWidget(title)

        self.orbit_item = QuickAccessItem(
            "Create new Orbit",
            "Create and configure orbital parameters."
        )

        self.satellite_item = QuickAccessItem(
            "Create new Satellite Configuration",
            "Define spacecraft properties and subsystems."
        )

        self.experiment_item = QuickAccessItem(
            "Create new Experiment",
            "Configure simulation scenarios and analyses."
        )

        layout.addWidget(self.orbit_item)
        layout.addWidget(self.satellite_item)
        layout.addWidget(self.experiment_item)

        layout.addStretch()

        
    def _create_info_panel(self, widget):
        
        right_layout = QFormLayout(widget)
        label = QLabel("About the Project")
        label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        label.setStyleSheet(
            "font-size: 24px;"
            "font-weight: bold;"
            "color: #ffffff;" 
            "margin-bottom: 6px;"
        )
        right_layout.addRow(label)

        self.info = QLabel()
        self.info.setWordWrap(True)  
        self.info.setText(
            "Lorem ipsum dolor sit amet consectetur adipiscing elit. Quisque faucibus ex sapien vitae " \
            "pellentesque sem placerat. In id cursus mi pretium tellus duis convallis. Tempus leo eu " \
            "aenean sed diam urna tempor. Pulvinar vivamus fringilla lacus nec metus bibendum egestas. " \
            "Iaculis massa nisl malesuada lacinia integer nunc posuere. Ut hendrerit semper vel class " \
            "aptent taciti sociosqu. Ad litora torquent per conubia nostra inceptos himenaeos." \

            "\n\nLorem ipsum dolor sit amet consectetur adipiscing elit. Quisque faucibus ex sapien vitae " \
            "pellentesque sem placerat. In id cursus mi pretium tellus duis convallis. Tempus leo eu " \
            "aenean sed diam urna tempor. Pulvinar vivamus fringilla lacus nec metus bibendum egestas. " \
            "Iaculis massa nisl malesuada lacinia integer nunc posuere. Ut hendrerit semper vel class " \
            "aptent taciti sociosqu. Ad litora torquent per conubia nostra inceptos himenaeos."
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
        
        right_layout.addRow(self.info)

        btn_user_manual = QPushButton("Show User Manual")
        btn_user_manual.setStyleSheet(
            "margin-top: 10px"
        )

        right_layout.addRow(btn_user_manual)
        
        
        
