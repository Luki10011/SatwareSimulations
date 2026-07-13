from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
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


class MainScreenWelcome(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.upper_widget = HeaderImageWidget("assets\\graphics\\space_background.jpg")
        
        upper_layout = QVBoxLayout(self.upper_widget)
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

        subtitle = QLabel("Aplikacja wspierająca projektowanie i analizę orbit satelitarnych.\n"
                          "Praca Magisterska")
        subtitle.setFont(QFont("Arial", 14))
        subtitle.setStyleSheet("""
            background: transparent; 
            color: #f0f0f0; 
            line-height: 150%;
        """)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        upper_layout.addWidget(title)
        upper_layout.addWidget(subtitle)

        lower_widget = QWidget()
        lower_widget.setStyleSheet("background-color: #1e1e1e;")
        
        lower_layout = QVBoxLayout(lower_widget)
        lower_layout.setContentsMargins(20, 60, 20, 80)
        lower_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.start_btn = QPushButton("Piwko")
        self.start_btn.setFixedSize(240, 50)

        
        lower_layout.addWidget(self.start_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addWidget(self.upper_widget, stretch=55)
        main_layout.addWidget(lower_widget, stretch=45)