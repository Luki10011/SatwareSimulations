import ctypes
import sys
from PyQt6.QtWidgets import QMessageBox

def apply_dark_title_bar(window) -> None:
    """
    Wymusza ciemny motyw dla natywnego paska tytułowego Windows 10 / 11.
    """
    if sys.platform != "win32":
        return

    try:
        # Pobieramy uchwyt okna (HWND)
        hwnd = int(window.winId())
        
        # 1 = włącz ciemny motyw
        value = ctypes.c_int(1)
        
        # Atrybut dla Windows 11 oraz nowszych kompilacji Windows 10 (2004+)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        
        res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 
            DWMWA_USE_IMMERSIVE_DARK_MODE, 
            ctypes.byref(value), 
            ctypes.sizeof(value)
        )
        
        # Fallback dla starszych wersji Windows 10
        if res != 0:
            DWMWA_USE_IMMERSIVE_DARK_MODE_OLD = 19
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 
                DWMWA_USE_IMMERSIVE_DARK_MODE_OLD, 
                ctypes.byref(value), 
                ctypes.sizeof(value)
            )
            
    except Exception as e:
        print(f"Nie udało się ustawić ciemnego paska tytułowego: {e}")


def show_dark_message_box(
    parent, 
    title: str, 
    text: str, 
    icon=QMessageBox.Icon.Information, 
    buttons=QMessageBox.StandardButton.Ok
) -> int:

    msg_box = QMessageBox(parent)
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    msg_box.setIcon(icon)
    msg_box.setStandardButtons(buttons)
    
    # Aplikujemy ciemny pasek przed pokazaniem okna
    apply_dark_title_bar(msg_box)
    msg_box.setStyleSheet(
        """
        QDialog, QMessageBox {
            background-color: #202020; /* Solidne, ciemne tło zapobiegające przezroczystości */
            color: #ffffff;
            font-family: "Segoe UI", sans-serif;
        }

        /* Wymuszenie białego koloru tekstu dla wszystkich etykiet wewnątrz okien popup */
        QDialog QLabel, QMessageBox QLabel {
            color: #ffffff;
            font-size: 10pt;
        }

        /* Stylizacja przycisków systemowych (OK, Cancel, Close) wewnątrz dialogów */
        QDialog QPushButton, QMessageBox QPushButton {
            min-width: 80px;
            background-color: rgba(255, 255, 255, 0.06);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 4px;
            padding: 5px 16px;
            font-size: 9.5pt;
        }

        QDialog QPushButton:hover, QMessageBox QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.1);
            border: 1px solid rgba(255, 255, 255, 0.2);
        }

        QDialog QPushButton:focus, QMessageBox QPushButton:focus {
            border: 2px solid #4d7aff; /* Niebieska obwódka aktywnego przycisku (np. domyślnego OK) */
            padding: 4px 15px; /* Kompensacja grubości ramki */
        }
        """
    )
    
    return msg_box.exec()