"""System tray icon, menu and notifications."""

import logging

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import (
    QAction,
    QBrush,
    QColor,
    QIcon,
    QPainter,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from config.settings_manager import find_asset

log = logging.getLogger(__name__)


def make_app_icon() -> QIcon:
    """App icon: bundled PNG when available, else a soft purple orb."""
    for parts in (("assets", "tray_icon.png"), ("images", "idle.png")):
        path = find_asset(*parts)
        if path:
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QRadialGradient(size / 2, size / 2.4, size / 1.5)
    gradient.setColorAt(0.0, QColor("#c084fc"))
    gradient.setColorAt(1.0, QColor("#5b21b6"))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(5, 5, size - 10, size - 10)
    painter.end()
    return QIcon(pixmap)


class TrayService(QObject):
    show_mascot_requested = Signal()
    hide_mascot_requested = Signal()
    toggle_mascot_requested = Signal()
    settings_requested = Signal()
    restart_requested = Signal()
    exit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tray = QSystemTrayIcon(make_app_icon(), self)
        self._tray.setToolTip("Whisperwing — local AI dictation")
        self._tray.activated.connect(self._on_activated)

        menu = QMenu()
        for text, signal in (
            ("Show mascot", self.show_mascot_requested),
            ("Hide mascot", self.hide_mascot_requested),
        ):
            action = QAction(text, menu)
            action.triggered.connect(signal.emit)
            menu.addAction(action)
        menu.addSeparator()
        for text, signal in (
            ("Settings…", self.settings_requested),
            ("Restart", self.restart_requested),
            ("Exit", self.exit_requested),
        ):
            action = QAction(text, menu)
            action.triggered.connect(signal.emit)
            menu.addAction(action)

        self._menu = menu
        self._tray.setContextMenu(menu)
        self._tray.show()

    def _on_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.toggle_mascot_requested.emit()

    def notify(self, title: str, message: str) -> None:
        log.info("Notify: %s — %s", title, message)
        self._tray.showMessage(
            title, message, QSystemTrayIcon.MessageIcon.Information, 3500
        )
