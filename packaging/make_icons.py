"""Gera assets/icon.png e assets/icon.ico a partir do ícone desenhado em código."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from glucowidget.ui.tray import app_icon_pixmap  # noqa: E402

app = QApplication(sys.argv)
out = ROOT / "src" / "glucowidget" / "assets"
out.mkdir(parents=True, exist_ok=True)
app_icon_pixmap(256).save(str(out / "icon.png"))
app_icon_pixmap(256).save(str(out / "icon.ico"))
print("ícones gerados em", out)
