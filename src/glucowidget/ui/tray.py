"""Ícones desenhados: ícone do app e ícone da bandeja com o valor atual."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPainterPath, QPixmap

from glucowidget.ui.theme import ui_font

BRAND = QColor("#6366f1")


def app_icon_pixmap(size: int = 256) -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r = QRectF(0, 0, size, size).adjusted(size * 0.04, size * 0.04, -size * 0.04, -size * 0.04)
    from PySide6.QtGui import QLinearGradient

    grad = QLinearGradient(r.topLeft(), r.bottomRight())
    grad.setColorAt(0, QColor("#7c83ff"))
    grad.setColorAt(1, QColor("#4338ca"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(r, size * 0.24, size * 0.24)
    # gota estilizada
    s = size
    drop = QPainterPath()
    drop.moveTo(s * 0.5, s * 0.2)
    drop.cubicTo(s * 0.5, s * 0.2, s * 0.26, s * 0.47, s * 0.26, s * 0.6)
    drop.cubicTo(s * 0.26, s * 0.74, s * 0.37, s * 0.83, s * 0.5, s * 0.83)
    drop.cubicTo(s * 0.63, s * 0.83, s * 0.74, s * 0.74, s * 0.74, s * 0.6)
    drop.cubicTo(s * 0.74, s * 0.47, s * 0.5, s * 0.2, s * 0.5, s * 0.2)
    p.setBrush(QColor(255, 255, 255, 240))
    p.drawPath(drop)
    # pulso dentro da gota
    from PySide6.QtGui import QPen

    p.setPen(QPen(QColor("#4f46e5"), s * 0.045, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                  Qt.PenJoinStyle.RoundJoin))
    pulse = QPainterPath()
    pulse.moveTo(s * 0.33, s * 0.64)
    pulse.lineTo(s * 0.43, s * 0.64)
    pulse.lineTo(s * 0.48, s * 0.53)
    pulse.lineTo(s * 0.54, s * 0.73)
    pulse.lineTo(s * 0.59, s * 0.64)
    pulse.lineTo(s * 0.67, s * 0.64)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(pulse)
    p.end()
    return pm


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(app_icon_pixmap(size))
    return icon


def value_icon(text: str, color: QColor, size: int = 64) -> QIcon:
    """Ícone da bandeja: número em destaque sobre um quadrado arredondado na cor do estado."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(color)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.22, size * 0.22)

    px = size * 0.62
    font = ui_font(px, QFont.Weight.Bold, tabular=True)
    fm = QFontMetrics(font)
    while fm.horizontalAdvance(text) > size * 0.92 and px > 8:
        px -= 1
        font = ui_font(px, QFont.Weight.Bold, tabular=True)
        fm = QFontMetrics(font)
    p.setFont(font)
    lum = 0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()
    p.setPen(QColor("#111827") if lum > 150 else QColor("#ffffff"))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return QIcon(pm)
