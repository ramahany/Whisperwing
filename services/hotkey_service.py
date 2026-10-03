"""Global hotkey registration plus a shortcut recorder for the settings UI."""

import logging
import threading

import keyboard
from PySide6.QtCore import QObject, QTimer, Signal

log = logging.getLogger(__name__)

DEFAULT_HOTKEY = "ctrl+alt+space"

_MODIFIER_ALIASES = {
    "left ctrl": "ctrl",
    "right ctrl": "ctrl",
    "left alt": "alt",
    "right alt": "alt",
    "alt gr": "alt",
    "left shift": "shift",
    "right shift": "shift",
    "left windows": "win",
    "right windows": "win",
}
_MODIFIERS = set(_MODIFIER_ALIASES) | {"ctrl", "alt", "shift", "win"}


def validate_hotkey(combo: str) -> None:
    """Raises ValueError when the combination cannot be parsed."""
    keyboard.parse_hotkey(combo)


def prettify(combo: str) -> str:
    """'ctrl+alt+space' -> 'Ctrl + Alt + Space' for display."""
    parts = [part.strip() for part in combo.split("+") if part.strip()]
    return " + ".join(part.capitalize() for part in parts)


class HotkeyService(QObject):
    """Bridges the global keyboard hook (its own thread) into a Qt signal."""

    activated = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._handle = None
        self._combo: str | None = None

    @property
    def combo(self) -> str | None:
        return self._combo

    def register(self, combo: str) -> None:
        """(Re)registers the global hotkey. Raises ValueError when invalid."""
        combo = combo.strip().lower()
        validate_hotkey(combo)
        self.unregister()
        self._handle = keyboard.add_hotkey(combo, self.activated.emit)
        self._combo = combo
        log.info("Global hotkey registered: %s", combo)

    def unregister(self) -> None:
        if self._handle is not None:
            try:
                keyboard.remove_hotkey(self._handle)
            except (KeyError, ValueError):
                pass
            self._handle = None


class ShortcutRecorder(QObject):
    """Captures the next key combination pressed anywhere on the system."""

    captured = Signal(str)
    cancelled = Signal()
    _stop_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hook = None
        self._modifiers: set[str] = set()
        self._lock = threading.Lock()
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self.cancel)
        # the hook callback runs on the keyboard thread; hop back to the
        # Qt thread before touching the timer or the hook itself
        self._stop_requested.connect(self._stop)

    def start(self) -> None:
        if self._hook is not None:
            return
        with self._lock:
            self._modifiers.clear()
        self._hook = keyboard.hook(self._on_event)
        self._timeout.start(10_000)

    def cancel(self) -> None:
        self._stop()
        self.cancelled.emit()

    def _stop(self) -> None:
        self._timeout.stop()
        if self._hook is not None:
            try:
                keyboard.unhook(self._on_event)
            except (KeyError, ValueError):
                pass
            self._hook = None

    def _on_event(self, event) -> None:
        if self._hook is None:
            return
        name = (event.name or "").lower()
        if not name:
            return
        if name == "esc":
            self._stop_requested.emit()
            self.cancelled.emit()
            return
        with self._lock:
            if name in _MODIFIERS:
                if event.event_type == "down":
                    self._modifiers.add(name)
                elif event.event_type == "up":
                    self._modifiers.discard(name)
                return
            if event.event_type != "down":
                return
            mods = {_MODIFIER_ALIASES.get(mod, mod) for mod in self._modifiers}
        ordered = [mod for mod in ("ctrl", "alt", "shift", "win") if mod in mods]
        combo = "+".join(ordered + [name])
        self._stop_requested.emit()
        if not ordered:
            # require at least one modifier so plain keys never become global triggers
            self.cancelled.emit()
            return
        log.info("Captured shortcut: %s", combo)
        self.captured.emit(combo)
