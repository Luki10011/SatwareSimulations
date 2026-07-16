from PyQt6.QtWidgets import (QWidget, 
                            QVBoxLayout, 
                            QLabel, 
                            QProgressBar)
from PyQt6.QtCore import Qt


class LoadingScreen(QWidget):
    """Loading screen for masking rendering's delay and 3D's initializaton"""
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.label = QLabel("Loading 3D Orbit Graphics Context...")
        self.label.setStyleSheet("""
            color: #ffffff; 
            font-size: 13pt; 
            font-family: 'Segoe UI', sans-serif;
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Animowany pasek postępu (tryb marquee)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) 
        self.progress_bar.setFixedWidth(320)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                background-color: rgba(255, 255, 255, 0.05);
                height: 4px;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 4px;
            }
        """)
        
        layout.addWidget(self.label)
        layout.addSpacing(20)
        layout.addWidget(self.progress_bar, alignment=Qt.AlignmentFlag.AlignCenter)

