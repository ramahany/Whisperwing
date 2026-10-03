"""Whisperwing — a floating local dictation companion.

Entry point: wires settings, the mascot UI and the speech / typing / hotkey /
tray services together. See README.md for setup and usage.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import keyboard
from PySide6.QtCore import QObject, QProcess
from PySide6.QtWidgets import QApplication

from config.settings_manager import SettingsManager, app_dir
from services.hotkey_service import HotkeyService
from services.speech_service import SpeechService
from services.startup_service import set_launch_on_startup
from services.tray_service import TrayService, make_app_icon
from services.typing_service import TypingService
from ui.mascot_window import MascotState, MascotWindow
from ui.settings_window import SettingsWindow
from ui.style import STYLESHEET, apply_dark_title_bar

log = logging.getLogger(__name__)


def setup_logging() -> None:
    # the one-time model download spams INFO-level HTTP logs; keep them quiet
    logging.getLogger("httpx").setLevel(logging.WARNING)
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    logs_dir = app_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
    file_handler = RotatingFileHandler(
        logs_dir / "whisperwing.log",
        maxBytes=512 * 1024,
        backupCount=2,
        encoding="utf-8",
    )
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(file_handler)
    root.addHandler(console)


class ApplicationController(QObject):
    """Owns every service and routes signals between them."""

    def __init__(self, qt_app: QApplication):
        super().__init__()
        self._app = qt_app
        self._settings = SettingsManager()
        self._mascot = MascotWindow(self._settings)
        self._speech = SpeechService(self._settings, self)
        self._typing = TypingService(self)
        self._hotkeys = HotkeyService(self)
        self._tray = TrayService(self)
        self._settings_window: SettingsWindow | None = None
        self._busy = False  # transcription or text injection in flight
        self._connect()

    def _connect(self) -> None:
        self._hotkeys.activated.connect(self.toggle_dictation)
        self._mascot.clicked.connect(self.toggle_dictation)
        self._mascot.settings_requested.connect(self.show_settings)
        self._mascot.hide_requested.connect(self._mascot.hide)
        self._mascot.exit_requested.connect(self.shutdown)

        self._speech.recording_started.connect(self._on_recording_started)
        self._speech.recording_stopped.connect(self._on_recording_stopped)
        self._speech.transcription_finished.connect(self._on_transcription)
        self._speech.transcription_error.connect(self._on_error)
        self._speech.model_status.connect(self._on_model_status)
        self._typing.typing_finished.connect(self._on_typing_finished)

        self._tray.show_mascot_requested.connect(self._mascot.show)
        self._tray.hide_mascot_requested.connect(self._mascot.hide)
        self._tray.toggle_mascot_requested.connect(
            lambda: self._mascot.setVisible(not self._mascot.isVisible())
        )
        self._tray.settings_requested.connect(self.show_settings)
        self._tray.restart_requested.connect(self.restart)
        self._tray.exit_requested.connect(self.shutdown)

    def start(self) -> None:
        self._mascot.show()
        try:
            self._hotkeys.register(str(self._settings.get("hotkey")))
        except ValueError as exc:
            log.error("Could not register hotkey: %s", exc)
            self._tray.notify("Whisperwing", f"Hotkey problem: {exc}")
        self._speech.preload_model()
        log.info("Whisperwing started")

    # --------------------------------------------------------- dictation

    def toggle_dictation(self) -> None:
        if self._speech.is_recording:
            self._speech.stop_recording()
            return
        if self._busy:
            log.debug("Busy; ignoring activation")
            return
        self._speech.start_recording()  # emits transcription_error on failure

    def _on_recording_started(self) -> None:
        self._busy = False
        if self._mascot.isVisible():
            self._mascot.set_state(MascotState.LISTENING)
        else:
            self._tray.notify(
                "Whisperwing",
                "Listening… press the hotkey again or click the mascot to stop.",
            )

    def _on_recording_stopped(self) -> None:
        self._busy = True
        self._mascot.set_state(MascotState.TYPING)

    def _on_transcription(self, text: str) -> None:
        text = text.strip()
        if not text:
            self._busy = False
            self._mascot.set_state(MascotState.IDLE)
            self._tray.notify("Whisperwing", "No speech detected.")
            return
        self._typing.insert_text(text)

    def _on_typing_finished(self) -> None:
        self._busy = False
        self._mascot.set_state(MascotState.IDLE)

    def _on_error(self, message: str) -> None:
        self._busy = False
        self._mascot.set_state(MascotState.IDLE)
        self._tray.notify("Whisperwing", message)

    def _on_model_status(self, message: str) -> None:
        log.info("Speech model: %s", message)

    # ---------------------------------------------------------- settings

    def show_settings(self) -> None:
        if self._settings_window is None:
            self._settings_window = SettingsWindow(self._settings)
            self._settings_window.settings_saved.connect(self._apply_settings)
            self._settings_window.scale_preview.connect(self._mascot.apply_scale)
            self._settings_window.closed.connect(self._revert_scale_preview)
        self._settings_window.show()
        self._settings_window.raise_()
        self._settings_window.activateWindow()
        apply_dark_title_bar(self._settings_window)

    def _revert_scale_preview(self) -> None:
        self._mascot.apply_scale(float(self._settings.get("mascot_scale")))

    def _apply_settings(self, values: dict) -> None:
        window = self._settings_window
        error: str | None = None

        hotkey = str(values.get("hotkey", "")).strip().lower()
        if hotkey:
            try:
                self._hotkeys.register(hotkey)
                self._settings.set("hotkey", hotkey)
            except ValueError as exc:
                error = f"Shortcut not saved: {exc}"

        launch_on_startup = bool(values["launch_on_startup"])
        self._settings.set("launch_on_startup", launch_on_startup)
        if not set_launch_on_startup(launch_on_startup):
            error = error or "Could not update the startup entry (settings still saved)."

        self._settings.set("always_on_top", values["always_on_top"])
        self._mascot.apply_always_on_top(bool(values["always_on_top"]))
        self._settings.set("model", values["model"])
        self._settings.set("language", values["language"])
        self._settings.set("mascot_scale", float(values["mascot_scale"]))
        self._mascot.apply_scale(float(values["mascot_scale"]))
        self._settings.save()
        log.info("Settings updated: %s", values)

        if error:
            window.show_status(error, error=True)
        else:
            window.show_status("Settings saved ✓")

    # ------------------------------------------------------- app control

    def restart(self) -> None:
        log.info("Restarting application")
        if getattr(sys, "frozen", False):
            QProcess.startDetached(sys.executable, [], str(app_dir()))
        else:
            script = os.path.abspath(sys.argv[0])
            QProcess.startDetached(sys.executable, [script], str(app_dir()))
        self.shutdown()

    def shutdown(self) -> None:
        log.info("Shutting down")
        self._speech.shutdown()
        self._settings.save()
        try:
            keyboard.unhook_all()
        except Exception:  # noqa: BLE001
            pass
        self._app.quit()


def main() -> None:
    setup_logging()
    log.info("Starting Whisperwing (python %s)", sys.version.split()[0])

    app = QApplication(sys.argv)
    app.setApplicationName("Whisperwing")
    app.setQuitOnLastWindowClosed(False)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(make_app_icon())

    controller = ApplicationController(app)
    controller.start()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
