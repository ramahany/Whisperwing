"""Shared look & feel: purple/black theme, global stylesheet, dark title bars."""

import ctypes
import sys

STYLESHEET = """
* {
    font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
    font-size: 13px;
    color: #e9e4f5;
}
QWidget { background-color: transparent; }
#settingsWindow { background-color: #17121f; }

QToolTip {
    background-color: #241b38;
    color: #e9e4f5;
    border: 1px solid #372a4f;
    padding: 4px 8px;
    border-radius: 6px;
}

#sideNav {
    background-color: #120d1a;
    border: none;
    border-right: 1px solid #241b38;
    padding-top: 14px;
    outline: none;
}
#sideNav::item {
    padding: 10px 18px;
    margin: 2px 10px;
    border-radius: 8px;
    color: #9b8fb8;
}
#sideNav::item:hover { background-color: #1d1531; color: #e9e4f5; }
#sideNav::item:selected { background-color: #2a1f45; color: #ffffff; font-weight: 600; }

#pageTitle { font-size: 20px; font-weight: 600; color: #ffffff; }
#pageSubtitle { color: #9b8fb8; }
#fieldLabel { color: #c9bfe0; }

QFrame#card {
    background-color: #1d1630;
    border: 1px solid #2a2138;
    border-radius: 12px;
}

QComboBox, QLineEdit {
    background-color: #1f1830;
    border: 1px solid #372a4f;
    border-radius: 8px;
    padding: 7px 12px;
    selection-background-color: #7c3aed;
}
QComboBox:hover, QLineEdit:hover { border-color: #55407a; }
QComboBox:focus, QLineEdit:focus { border-color: #a855f7; }
QLineEdit:read-only { color: #b3a6cf; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #9b8fb8;
    margin-right: 12px;
}
QComboBox QAbstractItemView {
    background-color: #1f1830;
    border: 1px solid #372a4f;
    border-radius: 8px;
    padding: 4px;
    outline: none;
    selection-background-color: #34255a;
    selection-color: #ffffff;
}
QComboBox QAbstractItemView::item { min-height: 26px; padding: 4px 8px; }

QCheckBox { spacing: 10px; }
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 6px;
    border: 1px solid #4a3a68;
    background-color: #1f1830;
}
QCheckBox::indicator:hover { border-color: #a855f7; }
QCheckBox::indicator:checked { background-color: #8b5cf6; border-color: #8b5cf6; }

QSlider { background: transparent; }
QSlider::groove:horizontal { height: 6px; background: #2a2138; border-radius: 3px; }
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #7c3aed, stop:1 #c084fc);
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 18px;
    height: 18px;
    margin: -6px 0;
    border-radius: 9px;
    background: #f3ecff;
}
QSlider::handle:horizontal:hover { background: #ffffff; }

QPushButton {
    background-color: #241b38;
    border: 1px solid #3d2f5c;
    border-radius: 9px;
    padding: 8px 18px;
    color: #e9e4f5;
}
QPushButton:hover { background-color: #2e2247; border-color: #55407a; }
QPushButton:pressed { background-color: #1d1531; }
QPushButton:disabled { color: #6b5f85; border-color: #2a2138; }

QPushButton#primaryButton {
    background-color: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #7c3aed, stop:1 #a855f7);
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 9px 22px;
}
QPushButton#primaryButton:hover {
    background-color: qlineargradient(x1:0 y1:0 x2:1 y2:0, stop:0 #8b5cf6, stop:1 #b871fb);
}
QPushButton#primaryButton:pressed { background-color: #6d28d9; }

QMenu {
    background-color: #1f1830;
    border: 1px solid #372a4f;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 7px 24px 7px 14px; border-radius: 6px; }
QMenu::item:selected { background-color: #34255a; color: #ffffff; }
QMenu::separator { height: 1px; background: #2a2138; margin: 5px 8px; }
"""


def apply_dark_title_bar(widget) -> None:
    """Ask Windows to draw the native title bar in dark mode (best effort)."""
    if sys.platform != "win32":
        return
    try:
        hwnd = int(widget.winId())
        for attribute in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (19 = older builds)
            result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, attribute, ctypes.byref(ctypes.c_int(1)), ctypes.sizeof(ctypes.c_int)
            )
            if result == 0:
                break
    except Exception:  # noqa: BLE001 - purely cosmetic
        pass
