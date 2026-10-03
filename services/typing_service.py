"""Types transcribed text into whatever window currently has focus."""

import logging
import threading
import time

import keyboard
from PySide6.QtCore import QObject, Signal

log = logging.getLogger(__name__)

TYPE_DELAY = 0.01  # seconds between keystrokes; small, but keeps apps from dropping input


class TypingService(QObject):
    """Runs keyboard.write() on a worker thread and reports when it is done."""

    typing_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None

    def insert_text(self, text: str) -> None:
        if self._thread and self._thread.is_alive():
            log.warning("Typing already in progress; dropping new text")
            self.typing_finished.emit()
            return
        self._thread = threading.Thread(
            target=self._type_out, args=(text,), name="typing", daemon=True
        )
        self._thread.start()

    def _type_out(self, text: str) -> None:
        try:
            time.sleep(0.05)  # let hotkey modifiers settle before typing
            keyboard.write(text, delay=TYPE_DELAY)
            log.info("Inserted %d characters", len(text))
        except Exception as exc:  # noqa: BLE001 - typing must never kill the app
            log.error("Text insertion failed: %s", exc)
        finally:
            self.typing_finished.emit()
