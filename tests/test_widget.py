import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from glucowidget.config import Settings
from glucowidget.ui.theme import DARK
from glucowidget.ui.widget import GlucoseWidget


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def _button_pixels(widget):
    """Imagem da área dos botões do cabeçalho."""
    img = widget.grab().toImage()
    top_left = widget.actions.mapTo(widget, QPoint(0, 0))
    return img.copy(top_left.x(), top_left.y(), widget.actions.width(), widget.actions.height())


def test_action_icons_are_visible_when_fully_faded_in(qapp):
    """Regressão: com QGraphicsOpacityEffect aninhado, os ícones sumiam ao chegar em opacidade 1.0."""
    w = GlucoseWidget(Settings(onboarded=True), DARK)
    w.show_message("user_plus", "Title", "Body", "Button", None)
    w.show()
    qapp.processEvents()

    w._set_actions_opacity(0.0)
    hidden = _button_pixels(w)
    for opacity in (0.5, 1.0):
        w._set_actions_opacity(opacity)
        shown = _button_pixels(w)
        assert shown != hidden, f"ícones não aparecem com opacidade {opacity}"
    w.close()


def test_invisible_buttons_let_clicks_through(qapp):
    w = GlucoseWidget(Settings(onboarded=True), DARK)
    w._set_actions_opacity(0.0)
    assert w.btn_settings.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    w._set_actions_opacity(1.0)
    assert not w.btn_settings.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
