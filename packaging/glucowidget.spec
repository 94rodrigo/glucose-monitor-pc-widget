# PyInstaller: pyinstaller packaging/glucowidget.spec
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules, copy_metadata

ROOT = Path(SPECPATH).parent
ASSETS = ROOT / "src" / "glucowidget" / "assets"
icon = ASSETS / ("icon.ico" if sys.platform == "win32" else "icon.png")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    # keyring descobre os backends (WinVaultKeyring, SecretService...) por entry points/submódulos,
    # que o PyInstaller não enxerga sozinho
    datas=[(str(ASSETS), "glucowidget/assets")] + copy_metadata("keyring"),
    hiddenimports=collect_submodules("keyring.backends") + ["glucowidget.selftest"],
    excludes=["tkinter", "PySide6.QtWebEngineCore", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtMultimedia"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="GlucoWidget",
    console=False,
    icon=str(icon) if icon.exists() else None,
    upx=False,
)
