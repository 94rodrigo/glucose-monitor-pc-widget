import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from glucowidget.config import Settings
from glucowidget.ui.dialogs import AnalysisDialog, OnboardingDialog, SettingsDialog
from glucowidget.ui.theme import DARK


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("make", [
    lambda: SettingsDialog(Settings(), DARK),
    lambda: OnboardingDialog(Settings(), DARK),
    lambda: AnalysisDialog(DARK),
])
def test_dialogs_can_minimize_and_maximize(qapp, make):
    dialog = make()
    assert dialog.windowFlags() & Qt.WindowType.WindowMinimizeButtonHint
    assert dialog.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    dialog.show()
    dialog.showMinimized()
    assert dialog.isMinimized()
    dialog.showMaximized()
    assert dialog.isMaximized()
    dialog.close()


@pytest.mark.parametrize("make", [
    lambda: SettingsDialog(Settings(), DARK),
    lambda: OnboardingDialog(Settings(), DARK),
    lambda: AnalysisDialog(DARK),
])
def test_custom_titlebar_buttons_work(qapp, monkeypatch, make):
    from glucowidget.ui.titlebar import TitleBar

    monkeypatch.setenv("GLUCOWIDGET_CUSTOM_TITLEBAR", "1")
    dialog = make()
    assert dialog.windowFlags() & Qt.WindowType.FramelessWindowHint
    bar = dialog.findChild(TitleBar)
    assert bar is not None and bar.title.text() == dialog.windowTitle()
    dialog.show()
    bar.btn_max.click()
    assert dialog.isMaximized() and bar.btn_max.icon_name == "win_restore"
    bar.btn_max.click()
    assert not dialog.isMaximized() and bar.btn_max.icon_name == "win_max"
    bar.btn_min.click()
    assert dialog.isMinimized()
    dialog.close()


def test_native_titlebar_when_disabled(qapp, monkeypatch):
    from glucowidget.ui.titlebar import TitleBar

    monkeypatch.setenv("GLUCOWIDGET_CUSTOM_TITLEBAR", "0")
    dialog = SettingsDialog(Settings(), DARK)
    assert dialog.findChild(TitleBar) is None
    assert not dialog.windowFlags() & Qt.WindowType.FramelessWindowHint


@pytest.mark.parametrize("custom", ["0", "1"])
def test_dialogs_are_normal_windows_not_dialog_type(qapp, monkeypatch, custom):
    # Qt.Dialog faz o GNOME/X11 tratar a janela como transitória: sem minimizar/maximizar e sempre por cima
    monkeypatch.setenv("GLUCOWIDGET_CUSTOM_TITLEBAR", custom)
    for dialog in (SettingsDialog(Settings(), DARK), OnboardingDialog(Settings(), DARK), AnalysisDialog(DARK)):
        assert dialog.windowType() == Qt.WindowType.Window
        assert dialog.parent() is None
