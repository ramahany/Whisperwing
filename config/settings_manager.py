"""Settings persistence for the dictation assistant.

Settings live in config/settings.json next to the application and are merged
over DEFAULTS, so new keys appear automatically after an update.
"""

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULTS = {
    "hotkey": "ctrl+alt+space",
    "language": "auto",          # "auto" | "en" | "ar"
    "model": "small",            # faster-whisper model size
    "mascot_scale": 1.0,         # 0.5 - 2.0
    "always_on_top": True,
    "launch_on_startup": False,
    "mascot_x": None,            # last mascot position (internal)
    "mascot_y": None,
}

_BOOL_KEYS = {"always_on_top", "launch_on_startup"}
_FLOAT_KEYS = {"mascot_scale", "mascot_x", "mascot_y"}


def app_dir() -> Path:
    """Directory the app lives in (exe folder when frozen)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_dir() -> Path:
    """Bundled-resource directory (PyInstaller payload when frozen)."""
    meipass = getattr(sys, "_MEIPASS", None)
    if getattr(sys, "frozen", False) and meipass:
        return Path(meipass)
    return app_dir()


def find_asset(*parts: str) -> Path | None:
    """Locate a bundled asset, checking the frozen payload and the app dir."""
    for base in (resource_dir(), app_dir()):
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate
    return None


class SettingsManager:
    """Loads, mutates and atomically saves the JSON settings file."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else app_dir() / "config" / "settings.json"
        self._data = dict(DEFAULTS)
        self.load()

    def load(self) -> None:
        if not self.path.exists():
            self.save()
            return
        try:
            stored = json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            log.warning("Could not read settings (%s); using defaults", exc)
            return
        if isinstance(stored, dict):
            for key in DEFAULTS:
                if key in stored:
                    self._data[key] = self._coerce(key, stored[key])

    @staticmethod
    def _coerce(key: str, value):
        try:
            if key in _BOOL_KEYS:
                return bool(value)
            if key in _FLOAT_KEYS:
                return None if value is None else float(value)
        except (TypeError, ValueError):
            return DEFAULTS[key]
        return value

    def get(self, key: str, fallback=None):
        return self._data.get(key, DEFAULTS.get(key, fallback))

    def set(self, key: str, value) -> None:
        self._data[key] = self._coerce(key, value) if key in DEFAULTS else value

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            log.error("Could not save settings: %s", exc)
