"""Barra de título própria para os diálogos.

No Wayland (GNOME) o Qt desenha a decoração no lado do cliente e os botões de minimizar e
maximizar não respondem, embora o compositor aceite os pedidos feitos pelo app. Nesse caso os
diálogos ficam sem moldura e usam esta barra, cujos botões chamam showMinimized/showMaximized.
Em Windows, macOS e X11 a barra nativa continua sendo usada.
"""
from __future__ import annotations

import os

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QFont, QGuiApplication
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QSizeGrip, QVBoxLayout, QWidget

from glucowidget.i18n import tr
from glucowidget.ui import icons
from glucowidget.ui.components import IconButton, separator
from glucowidget.ui.theme import Palette, rgba, ui_font, with_alpha

HEIGHT = 40
ENV_OVERRIDE = "GLUCOWIDGET_CUSTOM_TITLEBAR"  # "1" força, "0" desativa (útil em testes)


def use_custom_titlebar() -> bool:
    forced = os.environ.get(ENV_OVERRIDE)
    if forced is not None:
        return forced == "1"
    return QGuiApplication.platformName().startswith("wayland")


def window_flags() -> Qt.WindowType:
    """Janela sem moldura (a barra própria faz o papel da decoração)."""
    W = Qt.WindowType
    return W.Window | W.FramelessWindowHint | W.WindowMinMaxButtonsHint | W.WindowCloseButtonHint


def native_window_flags() -> Qt.WindowType:
    """Janela normal com a moldura do sistema.

    Não usar o tipo ``Qt.Dialog``: no X11 o Qt o marca como transitório do grupo do app e o GNOME
    então desabilita minimizar/maximizar e mantém a janela acima de tudo quando o widget principal
    é "sempre no topo".
    """
    W = Qt.WindowType
    return (W.Window | W.WindowTitleHint | W.WindowSystemMenuHint | W.WindowMinMaxButtonsHint
            | W.WindowCloseButtonHint)


class TitleBar(QWidget):
    def __init__(self, dialog: QDialog, palette: Palette):
        super().__init__(dialog)
        self.dialog = dialog
        self.setObjectName("titlebar")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setFixedHeight(HEIGHT)
        self.setStyleSheet(f"QWidget#titlebar {{ background: {rgba(palette.surface)}; }}")

        h = QHBoxLayout(self)
        h.setContentsMargins(14, 0, 8, 0)
        h.setSpacing(4)
        logo = QLabel()
        logo.setPixmap(icons.pixmap("drop", palette.accent, 16))
        logo.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.title = QLabel(dialog.windowTitle())
        self.title.setFont(ui_font(13, QFont.Weight.DemiBold))
        self.title.setStyleSheet(f"color: {rgba(palette.text_muted)}; background: transparent; padding-left: 6px;")
        self.title.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        dialog.windowTitleChanged.connect(self.title.setText)
        h.addWidget(logo)
        h.addWidget(self.title, 1)

        hover = with_alpha(palette.text, 26)
        self.btn_min = IconButton("win_min", tr("Minimize"))
        self.btn_max = IconButton("win_max", tr("Maximize"))
        self.btn_close = IconButton("close", tr("Close"))
        for b in (self.btn_min, self.btn_max, self.btn_close):
            b.configure(palette.text_muted, hover, 30)
            h.addWidget(b)
        self.btn_min.clicked.connect(dialog.showMinimized)
        self.btn_max.clicked.connect(self.toggle_maximized)
        self.btn_close.clicked.connect(dialog.close)
        dialog.installEventFilter(self)

    def toggle_maximized(self) -> None:
        if self.dialog.isMaximized():
            self.dialog.showNormal()
        else:
            self.dialog.showMaximized()

    def _refresh(self) -> None:
        maximized = self.dialog.isMaximized()
        self.btn_max.icon_name = "win_restore" if maximized else "win_max"
        self.btn_max.set_label(tr("Restore") if maximized else tr("Maximize"))
        self.btn_max.update()

    def eventFilter(self, obj, event) -> bool:
        # durante o encerramento o objeto Python pode já ter perdido seus atributos
        dialog = getattr(self, "dialog", None)
        if dialog is not None and obj is dialog and event.type() == QEvent.Type.WindowStateChange:
            self._refresh()
        return False

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            handle = self.dialog.windowHandle()
            if handle is not None:
                handle.startSystemMove()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximized()
            e.accept()


class _GripPlacer(QObject):
    """Mantém o puxador de redimensionamento no canto inferior direito."""

    def __init__(self, dialog: QDialog, grip: QSizeGrip):
        super().__init__(dialog)
        self.dialog, self.grip = dialog, grip
        dialog.installEventFilter(self)
        self._place()

    def _place(self) -> None:
        g, d = self.grip, self.dialog
        g.move(d.width() - g.width(), d.height() - g.height())
        g.setVisible(not d.isMaximized())
        g.raise_()

    def eventFilter(self, obj, event) -> bool:
        dialog = getattr(self, "dialog", None)
        if dialog is not None and obj is dialog and event.type() in (
                QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.WindowStateChange):
            self._place()
        return False


def install_titlebar(dialog: QDialog, palette: Palette, layout: QVBoxLayout) -> None:
    """Adiciona a barra (e o puxador de redimensionar) se a moldura nativa não for confiável."""
    if not use_custom_titlebar():
        return
    layout.addWidget(TitleBar(dialog, palette))
    layout.addWidget(separator())
    grip = QSizeGrip(dialog)
    grip.setFixedSize(16, 16)
    _GripPlacer(dialog, grip)
