"""Mini gráfico suave com faixa-alvo, gradiente por nível e tooltip."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QToolTip, QWidget

from glucowidget.libre.models import GlucoseReading
from glucowidget.ui.theme import Palette, with_alpha
from glucowidget.units import format_value


class Sparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.readings: list[GlucoseReading] = []
        self.hours = 3
        self.low = 70.0
        self.high = 180.0
        self.unit = "mg/dL"
        self.palette_: Palette | None = None
        self.stale = False
        self._points: list[tuple[QPointF, GlucoseReading]] = []
        self._hover: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(40)

    def set_data(self, readings, hours, low, high, unit, palette, stale=False):
        self.readings, self.hours, self.low, self.high = readings, hours, low, high
        self.unit, self.palette_, self.stale = unit, palette, stale
        self.update()

    # -- geometria ---------------------------------------------------------
    def _visible(self) -> list[GlucoseReading]:
        if not self.readings:
            return []
        end = max(self.readings[-1].timestamp, datetime.now(timezone.utc))
        start = end - timedelta(hours=self.hours)
        return [r for r in self.readings if r.timestamp >= start]

    def _y_range(self, values: list[float]) -> tuple[float, float]:
        lo = min(min(values), self.low) - 12
        hi = max(max(values), self.high) + 12
        return max(30.0, lo), hi

    @staticmethod
    def _smooth(points: list[QPointF]) -> QPainterPath:
        path = QPainterPath(points[0])
        if len(points) < 3:
            for pt in points[1:]:
                path.lineTo(pt)
            return path
        # Catmull-Rom -> Bézier, tensão moderada
        t = 0.18
        for i in range(len(points) - 1):
            p0 = points[i - 1] if i > 0 else points[i]
            p1, p2 = points[i], points[i + 1]
            p3 = points[i + 2] if i + 2 < len(points) else p2
            c1 = QPointF(p1.x() + (p2.x() - p0.x()) * t, p1.y() + (p2.y() - p0.y()) * t)
            c2 = QPointF(p2.x() - (p3.x() - p1.x()) * t, p2.y() - (p3.y() - p1.y()) * t)
            path.cubicTo(c1, c2, p2)
        return path

    # -- pintura -------------------------------------------------------------
    def paintEvent(self, _):
        pal = self.palette_
        data = self._visible()
        if not pal or len(data) < 2:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dot_r = 3.5
        rect = QRectF(self.rect()).adjusted(2, dot_r + 2, -dot_r - 3, -2)
        values = [r.value_mgdl for r in data]
        y_min, y_max = self._y_range(values)
        end = max(data[-1].timestamp, datetime.now(timezone.utc))
        span = self.hours * 3600

        def ymap(v: float) -> float:
            return rect.bottom() - (v - y_min) / (y_max - y_min) * rect.height()

        def xmap(ts: datetime) -> float:
            return rect.right() - (end - ts).total_seconds() / span * rect.width()

        # faixa-alvo
        band = QRectF(rect.left(), ymap(self.high), rect.width(), ymap(self.low) - ymap(self.high))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(pal.band)
        p.drawRoundedRect(band, 4, 4)
        dash = QPen(with_alpha(pal.in_range, 70), 1, Qt.PenStyle.DashLine)
        dash.setDashPattern([2, 4])
        p.setPen(dash)
        for v in (self.low, self.high):
            p.drawLine(QPointF(rect.left(), ymap(v)), QPointF(rect.right(), ymap(v)))

        pts = [QPointF(xmap(r.timestamp), ymap(r.value_mgdl)) for r in data]
        self._points = list(zip(pts, data))
        path = self._smooth(pts)

        # gradiente vertical: cor muda ao cruzar os limites
        if self.stale:
            grad_line = QLinearGradient(0, rect.top(), 0, rect.bottom())
            grad_line.setColorAt(0, pal.stale)
            grad_line.setColorAt(1, pal.stale)
        else:
            grad_line = QLinearGradient(0, rect.top(), 0, rect.bottom())
            hi_pos = max(0.0, min(1.0, (ymap(self.high) - rect.top()) / rect.height()))
            lo_pos = max(0.0, min(1.0, (ymap(self.low) - rect.top()) / rect.height()))
            grad_line.setColorAt(0, pal.high)
            grad_line.setColorAt(max(0.0, hi_pos - 0.001), pal.high)
            grad_line.setColorAt(hi_pos, pal.in_range)
            grad_line.setColorAt(lo_pos, pal.in_range)
            grad_line.setColorAt(min(1.0, lo_pos + 0.001), pal.low)
            grad_line.setColorAt(1, pal.low)

        # preenchimento suave sob a curva
        fill = QPainterPath(path)
        fill.lineTo(pts[-1].x(), rect.bottom())
        fill.lineTo(pts[0].x(), rect.bottom())
        fill.closeSubpath()
        last_color = pal.stale if self.stale else self._color_for(data[-1].value_mgdl, pal)
        grad_fill = QLinearGradient(0, rect.top(), 0, rect.bottom())
        grad_fill.setColorAt(0, with_alpha(last_color, 46))
        grad_fill.setColorAt(1, with_alpha(last_color, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(grad_fill)
        p.drawPath(fill)

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(grad_line, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)

        # ponto da última leitura com halo
        last = pts[-1]
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(with_alpha(last_color, 60))
        p.drawEllipse(last, dot_r * 2, dot_r * 2)
        p.setBrush(last_color)
        p.drawEllipse(last, dot_r, dot_r)

        # ponto em hover
        if self._hover is not None and self._hover < len(self._points):
            hp, hr = self._points[self._hover]
            p.setPen(QPen(with_alpha(pal.text_muted, 90), 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(hp.x(), rect.top()), QPointF(hp.x(), rect.bottom()))
            p.setPen(QPen(pal.card.lighter(150) if pal.name == "dark" else pal.surface, 2))
            p.setBrush(self._color_for(hr.value_mgdl, pal))
            p.drawEllipse(hp, dot_r + 0.5, dot_r + 0.5)
        p.end()

    def _color_for(self, v: float, pal: Palette) -> QColor:
        if v < self.low:
            return pal.low
        if v > self.high:
            return pal.high
        return pal.in_range

    # -- interação ------------------------------------------------------------
    def mouseMoveEvent(self, e):
        if not self._points:
            return
        x = e.position().x()
        idx = min(range(len(self._points)), key=lambda i: abs(self._points[i][0].x() - x))
        if idx != self._hover:
            self._hover = idx
            r = self._points[idx][1]
            QToolTip.showText(
                e.globalPosition().toPoint(),
                f"<b>{format_value(r.value_mgdl, self.unit)}</b> {self.unit} · {r.timestamp.astimezone():%H:%M}",
                self,
            )
            self.update()
        super().mouseMoveEvent(e)

    def leaveEvent(self, e):
        self._hover = None
        QToolTip.hideText()
        self.update()
        super().leaveEvent(e)
