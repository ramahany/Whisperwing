"""Launch-on-startup support via the HKCU Run registry key (Windows only)."""

import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)

try:
    import winreg
except ImportError:  # non-Windows development
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "Whisperwing"


def _command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    launcher = pythonw if pythonw.exists() else python
    script = Path(__file__).resolve().parents[1] / "main.py"
    return f'"{launcher}" "{script}"'


def set_launch_on_startup(enabled: bool) -> bool:
    """Register or remove the startup entry. Returns True on success."""
    if winreg is None:
        log.warning("Startup toggle is only supported on Windows")
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except OSError as exc:
        log.error("Could not update startup entry: %s", exc)
        return False
