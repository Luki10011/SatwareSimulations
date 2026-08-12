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
    
    return msg_box.exec()