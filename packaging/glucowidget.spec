# PyInstaller: pyinstaller packaging/glucowidget.spec
import sys
from pathlib import Path

ROOT = Path(SPECPATH).parent
ASSETS = ROOT / "src" / "glucowidget" / "assets"
icon = ASSETS / ("icon.ico" if sys.platform == "win32" else "icon.png")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    datas=[(str(ASSETS), "glucowidget/assets")],
    hiddenimports=["keyring.backends"],
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
