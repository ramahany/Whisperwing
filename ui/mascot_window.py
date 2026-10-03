"""Floating, frameless mascot window.

The window never takes keyboard focus, so dictated text keeps flowing into
whatever application the user is working in. Missing state images fall back
to a built-in glowing orb so the app stays usable until PNGs are provided.
"""

import logging
from enum import Enum

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QLabel, QMenu, QWidget

from config.settings_manager import find_asset

log = logging.getLogger(__name__)

BASE_HEIGHT = 180          # mascot height (px) at 100% scale
DRAG_THRESHOLD = 8         # px of movement before a press counts as a drag
HOVER_RETURN_MS = 1600     # awake -> idle delay after the cursor leaves

STATE_IMAGES = {
    "idle": "idle.png",
    "awake": "awake.png",
    "listening": "listening.png",
    "typing": "typing.png",
}

STATE_COLORS = {
    "idle": "#5b21b6",
    "awake": "#8b5cf6",
    "listening": "#ec4899",
    "typing": "#c084fc",
}


class MascotState(Enum):
    IDLE = "idle"
    AWAKE = "awake"
    LISTENING = "listening"
    TYPING = "typing"


class MascotWindow(QWidget):
    clicked = Signal()
    settings_requested = Signal()
    hide_requested = Signal()
    exit_requested = Signal()

    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._scale = max(0.4, min(2.5, float(settings.get("mascot_scale"))))
        self._state = MascotState.IDLE
        self._drag_active = False
        self._press_global = QPoint()
        self._press_offset = QPoint()

        flags = (
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        if bool(settings.get("always_on_top", True)):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setToolTip("Click to dictate — drag to move")

        self._label = QLabel(self)

        self._pixmaps: dict[MascotState, QPixmap | None] = {}
        self._load_pixmaps()

        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.timeout.connect(self._hover_expired)

        self.set_state(MascotState.IDLE)
        self._restore_position()

    # ------------------------------------------------------------ assets

    def _load_pixmaps(self) -> None:
        missing = []
        for state, filename in STATE_IMAGES.items():
            path = find_asset("images", filename)
            pixmap = QPixmap(str(path)) if path else QPixmap()
            if pixmap.isNull():
                missing.append(filename)
                self._pixmaps[MascotState(state)] = None
            else:
                self._pixmaps[MascotState(state)] = pixmap
        if missing:
            log.warning(
                "Missing mascot images: %s — falling back to built-in orb",
                ", ".join(missing),
            )

    def _pixmap_for(self, state: MascotState) -> QPixmap:
        height = max(40, round(BASE_HEIGHT * self._scale))
        source = self._pixmaps.get(state)
        if source is not None:
            return source.scaledToHeight(height, Qt.TransformationMode.SmoothTransformation)
        return self._fallback_pixmap(state, height)

    def _fallback_pixmap(self, state: MascotState, size: int) -> QPixmap:
        """Soft glowing orb used only while the matching PNG is missing."""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        gradient = QRadialGradient(size / 2, size / 2, size / 2)
        gradient.setColorAt(0.0, QColor("#c084fc"))
        gradient.setColorAt(0.55, QColor(STATE_COLORS[state.value]))
        gradient.setColorAt(1.0, QColor(20, 12, 35, 60))
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, size - 4, size - 4)
        painter.setPen(QPen(QColor(255, 255, 255, 90), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(2, 2, size - 4, size - 4)
        painter.setPen(QColor(238, 230, 255, 210))
        font = painter.font()
        font.setPointSize(max(9, size // 16))
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, state.value)
        painter.end()
        return pixmap

    # ------------------------------------------------------------- state

    def set_state(self, state: MascotState) -> None:
        self._state = state
        pixmap = self._pixmap_for(state)
        self._label.setPixmap(pixmap)
        self._label.resize(pixmap.size())
        self.resize(pixmap.size())

    def apply_scale(self, scale: float) -> None:
        self._scale = max(0.4, min(2.5, float(scale)))
        self.set_state(self._state)

    def apply_always_on_top(self, enabled: bool) -> None:
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(enabled))
        if was_visible:
            self.hide()
            self.show()

    # ---------------------------------------------------------- position

    def _restore_position(self) -> None:
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()
        x = self._settings.get("mascot_x")
        y = self._settings.get("mascot_y")
        if x is None or y is None:
            self.move(area.right() - self.width() - 32, area.bottom() - self.height() - 32)
            return
        x = int(max(area.left(), min(x, area.right() - self.width())))
        y = int(max(area.top(), min(y, area.bottom() - self.height())))
        self.move(x, y)

    def _save_position(self) -> None:
        self._settings.set("mascot_x", self.x())
        self._settings.set("mascot_y", self.y())
        self._settings.save()

    # ------------------------------------------------------------ events

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global = event.globalPosition().toPoint()
            self._press_offset = self._press_global - self.frameGeometry().topLeft()
            self._drag_active = False
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and not self._press_global.isNull():
            current = event.globalPosition().toPoint()
            if not self._drag_active and (current - self._press_global).manhattanLength() > DRAG_THRESHOLD:
                self._drag_active = True
            if self._drag_active:
                self.move(current - self._press_offset)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._press_global.isNull():
            if self._drag_active:
                self._save_position()
            else:
                self.clicked.emit()
            self._press_global = QPoint()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self._hover_timer.stop()
        if self._state is MascotState.IDLE:
            self.set_state(MascotState.AWAKE)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        if self._state is MascotState.AWAKE:
            self._hover_timer.start(HOVER_RETURN_MS)
        super().leaveEvent(event)

    def _hover_expired(self) -> None:
        if self._state is MascotState.AWAKE:
            self.set_state(MascotState.IDLE)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        settings_action = menu.addAction("Settings…")
        settings_action.triggered.connect(self.settings_requested.emit)
        hide_action = menu.addAction("Hide mascot")
        hide_action.triggered.connect(self.hide_requested.emit)
        menu.addSeparator()
        exit_action = menu.addAction("Exit")
        exit_action.triggered.connect(self.exit_requested.emit)
        menu.exec(event.globalPos())
