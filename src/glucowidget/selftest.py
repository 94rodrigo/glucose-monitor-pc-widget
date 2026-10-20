"""Verificação do app instalado/empacotado: ``glucowidget --selftest relatorio.txt``.

Confere o que um executável empacotado costuma perder (plugin SVG do Qt, traduções, ícone,
backend do keyring) e escreve um relatório de texto. Código de saída 0 = tudo certo.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication


def run(report_path: str, check_keyring: bool = True) -> int:
    lines: list[str] = []
    failed = False

    def check(name: str, fn) -> None:
        nonlocal failed
        try:
            lines.append(f"PASS {name}: {fn()}")
        except Exception as exc:  # noqa: BLE001 - qualquer falha entra no relatório
            failed = True
            lines.append(f"FAIL {name}: {exc!r}")

    app = QApplication.instance() or QApplication([])
    lines.append(f"INFO python={sys.version.split()[0]} frozen={getattr(sys, 'frozen', False)} "
                 f"platform={app.platformName()}")

    def svg_icon():
        from glucowidget.ui import icons

        img = icons.pixmap("drop", QColor("#ffffff"), 32).toImage()
        opaque = sum(1 for x in range(img.width()) for y in range(img.height()) if img.pixelColor(x, y).alpha() > 0)
        assert opaque > 50, "ícone SVG renderizou vazio (plugin QtSvg ausente?)"
        return f"{opaque} pixels"

    def app_icon():
        from glucowidget.ui.tray import app_icon_pixmap

        assert not app_icon_pixmap(64).isNull()
        return "ok"

    def translations():
        from glucowidget.i18n import get_language, set_language, tr

        previous = get_language()
        try:
            set_language("pt")
            assert tr("Settings") == "Configurações", "catálogo pt não carregou"
            set_language("en")
            assert tr("Settings") == "Settings"
        finally:
            set_language(previous)
        return "en/pt"

    def settings_roundtrip():
        from glucowidget.config import Settings

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            Settings(email="a@b.com", unit="mmol/L").save(path)
            loaded = Settings.load(path)
        assert loaded.email == "a@b.com" and loaded.unit == "mmol/L"
        return "ok"

    def secrets_roundtrip():
        from glucowidget import config

        name = "selftest_secret"
        config.set_secret(name, "value-123")
        try:
            assert config.get_secret(name) == "value-123"
        finally:
            config.set_secret(name, "")
        return "ok (keyring ou arquivo de reserva)"

    def widget_render():
        from glucowidget.config import Settings
        from glucowidget.ui.theme import DARK, load_fonts
        from glucowidget.ui.widget import GlucoseWidget

        load_fonts()
        w = GlucoseWidget(Settings(onboarded=True), DARK)
        w.show_message("user_plus", "Self-test", "Rendering check", "OK", None)
        w.show()
        app.processEvents()
        img = w.grab()
        w.close()
        assert not img.isNull() and img.width() > 100
        return f"{img.width()}x{img.height()}"

    check("svg-icon", svg_icon)
    check("app-icon", app_icon)
    check("translations", translations)
    check("settings", settings_roundtrip)
    check("secrets", secrets_roundtrip)
    check("widget-render", widget_render)

    if check_keyring:
        try:
            import keyring

            backend = type(keyring.get_keyring()).__name__
            keyring.set_password("glucowidget-selftest", "k", "v")
            ok = keyring.get_password("glucowidget-selftest", "k") == "v"
            keyring.delete_password("glucowidget-selftest", "k")
            lines.append(f"INFO keyring backend={backend} roundtrip={'ok' if ok else 'failed'}")
        except Exception as exc:  # noqa: BLE001 - informativo (pode não haver cofre em CI/headless)
            lines.append(f"INFO keyring unavailable: {exc!r}")

    lines.append("RESULT " + ("FAILED" if failed else "OK"))
    Path(report_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 1 if failed else 0
