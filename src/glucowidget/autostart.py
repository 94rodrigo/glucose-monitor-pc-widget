"""Iniciar com o sistema (Windows: registro Run; Linux: ~/.config/autostart)."""
from __future__ import annotations

import logging
import os
import shlex
import sys
from pathlib import Path

from glucowidget import APP_ID, APP_NAME

log = logging.getLogger(__name__)


def launch_command() -> list[str]:
    if getattr(sys, "frozen", False):  # executável PyInstaller
        return [sys.executable]
    exe = sys.executable
    if sys.platform == "win32" and exe.lower().endswith("python.exe"):
        exe = exe[:-10] + "pythonw.exe"  # sem console
    return [exe, "-m", "glucowidget"]


def _desktop_file() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "autostart" / f"{APP_ID}.desktop"


def set_autostart(enabled: bool) -> None:
    try:
        if sys.platform == "win32":
            import winreg

            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run",
                                 0, winreg.KEY_SET_VALUE)
            with key:
                if enabled:
                    cmd = " ".join(f'"{c}"' if " " in c else c for c in launch_command())
                    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, cmd)
                else:
                    try:
                        winreg.DeleteValue(key, APP_NAME)
                    except FileNotFoundError:
                        pass
        elif sys.platform.startswith("linux"):
            path = _desktop_file()
            if enabled:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    "[Desktop Entry]\nType=Application\n"
                    f"Name={APP_NAME}\nComment=Real-time FreeStyle Libre glucose\n"
                    f"Exec={shlex.join(launch_command())}\n"
                    "X-GNOME-Autostart-enabled=true\nTerminal=false\n",
                    encoding="utf-8",
                )
            elif path.exists():
                path.unlink()
    except OSError as exc:
        log.warning("Could not configure autostart: %s", exc)
