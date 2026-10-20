"""Componentes visuais reutilizáveis."""
from __future__ import annotations

import math

from PySide6.QtCore import (
    Property,
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractButton,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from glucowidget.i18n import tr
from glucowidget.libre.models import Trend
from glucowidget.status import Level
from glucowidget.ui import icons
from glucowidget.ui.theme import Palette, ui_font, with_alpha


def level_color(level: Level, p: Palette) -> QColor:
    return {
        Level.URGENT_LOW: p.low,
        Level.LOW: p.low,
        Level.IN_RANGE: p.in_range,
        Level.HIGH: p.high,
        Level.URGENT_HIGH: p.high,
    }.get(level, p.stale)


class TrendIcon(QWidget):
    """Seta de tendência vetorial dentro de um círculo tingido."""

    _ANGLES = {Trend.FALLING_FAST: 90, Trend.FALLING: 45, Trend.STABLE: 0,
               Trend.RISING: -45, Trend.RISING_FAST: -90}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trend = Trend.UNKNOWN
        self._color = QColor("#888")
        self._angle = 0.0
        self._anim = QPropertyAnimation(self, b"angle", self)
        self._anim.setDuration(450)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animate = True
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def get_angle(self) -> float:
        return self._angle

    def set_angle(self, value: float) -> None:
        self._angle = value
        self.update()

    angle = Property(float, get_angle, set_angle)

    def set_trend(self, trend: Trend, color: QColor) -> None:
        self._color = QColor(color)
        target = float(self._ANGLES.get(trend, 0))
        changed = trend != self._trend
        self._trend = trend
        self.setToolTip(tr("Trend: {trend}", trend=trend.label))
        if changed and self.animate and self.isVisible():
            self._anim.stop()
            self._anim.setStartValue(self._angle)
            self._anim.setEndValue(target)
            self._anim.start()
        else:
            self._angle = target
        self.update()

    def paintEvent(self, _):
        if self._trend == Trend.UNKNOWN:
            return
        s = min(self.width(), self.height())
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.width() / 2, self.height() / 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(with_alpha(self._color, 38))
        p.drawEllipse(QPointF(0, 0), s / 2, s / 2)

        p.rotate(self._angle)
        pen = QPen(self._color, max(2.0, s * 0.085), Qt.PenStyle.SolidLine,
                   Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        r = s * 0.24
        head = s * 0.14
        fast = self._trend in (Trend.RISING_FAST, Trend.FALLING_FAST)
        p.drawLine(QPointF(-r if not fast else -r * 0.6, 0), QPointF(r, 0))
        path = QPainterPath(QPointF(r - head, -head))
        path.lineTo(QPointF(r, 0))
        path.lineTo(QPointF(r - head, head))
        p.drawPath(path)
        if fast:
            off = head * 1.3
            path2 = QPainterPath(QPointF(r - head - off, -head))
            path2.lineTo(QPointF(r - off, 0))
            path2.lineTo(QPointF(r - head - off, head))
            p.drawPath(path2)
        p.end()


class StatusPill(QWidget):
    """Pílula com ponto colorido + rótulo — o estado nunca depende só da cor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._color = QColor("#888")
        self._text_color = QColor("#fff")
        self._font = ui_font(11, QFont.Weight.DemiBold)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

    def set_state(self, text: str, color: QColor, text_color: QColor, px: float = 11) -> None:
        self._text, self._color, self._text_color = text, QColor(color), QColor(text_color)
        self._font = ui_font(px, QFont.Weight.DemiBold)
        self.updateGeometry()
        self.update()

    def sizeHint(self) -> QSize:
        from PySide6.QtGui import QFontMetrics

        fm = QFontMetrics(self._font)
        h = fm.height() + 8
        return QSize(fm.horizontalAdvance(self._text) + h + 10, h)

    def paintEvent(self, _):
        if not self._text:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(with_alpha(self._color, 36))
        p.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)
        d = rect.height() * 0.36
        cx = rect.left() + rect.height() / 2 + 1
        p.setBrush(self._color)
        p.drawEllipse(QPointF(cx, rect.center().y()), d / 2, d / 2)
        p.setPen(self._text_color)
        p.setFont(self._font)
        text_rect = rect.adjusted(rect.height() * 0.5 + d, 0, -8, 0)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._text)
        p.end()


class IconButton(QAbstractButton):
    """Botão de ícone circular e discreto, com hover."""

    def __init__(self, icon_name: str, tooltip: str, parent=None):
        super().__init__(parent)
        self.icon_name = icon_name
        self.setToolTip(tooltip)
        self.setAccessibleName(tooltip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color = QColor("#999")
        self._hover_bg = QColor(255, 255, 255, 20)
        self._hover = False
        self._size = 24
        self._opacity = 1.0
        self.setFixedSize(self._size, self._size)

    def set_opacity(self, value: float) -> None:
        """Opacidade desenhada no próprio botão (QGraphicsOpacityEffect aninhado em outro efeito
        deixa de renderizar o conteúdo quando chega a 1.0). Invisível = não captura cliques."""
        self._opacity = max(0.0, min(1.0, value))
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, self._opacity < 0.05)
        self.update()

    def set_label(self, text: str) -> None:
        self.setToolTip(text)
        self.setAccessibleName(text)

    def configure(self, color: QColor, hover_bg: QColor, size: int) -> None:
        self._color, self._hover_bg, self._size = QColor(color), QColor(hover_bg), size
        self.setFixedSize(size, size)
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hover = False
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, _):
        if self._opacity <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setOpacity(self._opacity)
        if self._hover or self.isDown():
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(self._hover_bg)
            p.drawEllipse(QRectF(self.rect()))
        ico = round(self._size * 0.6)
        pm = icons.pixmap(self.icon_name, self._color, ico, max(2.0, self.devicePixelRatioF()))
        off = (self._size - ico) / 2
        p.drawPixmap(QRectF(off, off, ico, ico), pm, QRectF(pm.rect()))
        p.end()


class Spinner(QWidget):
    def __init__(self, size: int = 28, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0
        self._color = QColor("#7c83ff")
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)

    def set_color(self, c: QColor) -> None:
        self._color = QColor(c)

    def start(self):
        self._timer.start(16)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _tick(self):
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = max(2.5, self.width() / 10)
        r = QRectF(self.rect()).adjusted(w, w, -w, -w)
        p.setPen(QPen(with_alpha(self._color, 45), w))
        p.drawEllipse(r)
        p.setPen(QPen(self._color, w, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        p.drawArc(r, -self._angle * 16, 100 * 16)
        p.end()


class Skeleton(QWidget):
    """Placeholder pulsante enquanto a primeira leitura carrega."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._phase = 0.0
        self._color = QColor(255, 255, 255, 30)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self.compact = False

    def set_color(self, c: QColor):
        self._color = QColor(c)

    def showEvent(self, e):
        self._timer.start(33)
        super().showEvent(e)

    def hideEvent(self, e):
        self._timer.stop()
        super().hideEvent(e)

    def _tick(self):
        self._phase = (self._phase + 0.04) % (2 * math.pi)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = QColor(self._color)
        c.setAlphaF(self._color.alphaF() * (0.55 + 0.45 * (0.5 + 0.5 * math.sin(self._phase))))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        w, h = self.width(), self.height()
        if self.compact:
            p.drawRoundedRect(QRectF(0, h * 0.2, w * 0.6, h * 0.6), 8, 8)
            p.drawEllipse(QRectF(w - h * 0.6, h * 0.2, h * 0.6, h * 0.6))
        else:
            p.drawRoundedRect(QRectF(0, 0, w * 0.32, h * 0.1), 6, 6)
            p.drawRoundedRect(QRectF(0, h * 0.17, w * 0.55, h * 0.28), 10, 10)
            p.drawRoundedRect(QRectF(0, h * 0.52, w * 0.4, h * 0.08), 5, 5)
            p.drawRoundedRect(QRectF(0, h * 0.68, w, h * 0.32), 10, 10)
        p.end()


class SegmentedControl(QWidget):
    changed = Signal(str)

    def __init__(self, options: list[tuple[str, str]], parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._buttons: dict[str, QPushButton] = {}
        for i, (value, label) in enumerate(options):
            b = QPushButton(label)
            b.setObjectName("segment")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setProperty("first", i == 0)
            b.setProperty("last", i == len(options) - 1)
            b.clicked.connect(lambda _=False, v=value: self.changed.emit(v))
            self._group.addButton(b)
            layout.addWidget(b)
            self._buttons[value] = b
        layout.addStretch(1)

    def value(self) -> str:
        for v, b in self._buttons.items():
            if b.isChecked():
                return v
        return next(iter(self._buttons))

    def set_value(self, value: str) -> None:
        if value in self._buttons:
            self._buttons[value].setChecked(True)


def card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


def separator() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    return f


class Toggle(QCheckBox):
    """Switch on/off com knob animado (estado visível pela posição, não só pela cor)."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.toggled.connect(self._animate)
        self.track_on = QColor("#6366f1")
        self.track_off = QColor(128, 128, 128, 90)

    def get_knob(self) -> float:
        return self._pos

    def set_knob(self, v: float) -> None:
        self._pos = v
        self.update()

    knob = Property(float, get_knob, set_knob)

    def setChecked(self, checked: bool) -> None:  # noqa: N802 - API Qt
        super().setChecked(checked)
        self._anim.stop()
        self._pos = 1.0 if checked else 0.0
        self.update()

    def _animate(self, checked: bool) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if checked else 0.0)
        self._anim.start()

    def sizeHint(self) -> QSize:
        fm = self.fontMetrics()
        return QSize(40 + 10 + fm.horizontalAdvance(self.text()) + 4, max(24, fm.height() + 6))

    def hitButton(self, pos) -> bool:
        return self.rect().contains(pos)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        h = 20.0
        track = QRectF(0, (self.height() - h) / 2, 36, h)
        on = QColor(self.track_on)
        off = QColor(self.track_off)
        t = self._pos
        color = QColor(
            round(off.red() + (on.red() - off.red()) * t),
            round(off.green() + (on.green() - off.green()) * t),
            round(off.blue() + (on.blue() - off.blue()) * t),
            round(off.alpha() + (on.alpha() - off.alpha()) * t),
        )
        if not self.isEnabled():
            color.setAlpha(color.alpha() // 2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(track, h / 2, h / 2)
        r = h / 2 - 3
        cx = track.left() + 3 + r + (track.width() - 2 * (3 + r)) * t
        p.setBrush(QColor(255, 255, 255, 255 if self.isEnabled() else 160))
        p.drawEllipse(QPointF(cx, track.center().y()), r, r)
        p.setPen(self.palette().color(self.foregroundRole()))
        p.drawText(QRectF(track.right() + 10, 0, self.width() - track.right() - 10, self.height()),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self.text())
        p.end()
