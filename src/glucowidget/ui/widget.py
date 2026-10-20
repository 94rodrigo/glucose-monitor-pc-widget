"""Janela flutuante com a glicemia atual."""
from __future__ import annotations

from datetime import datetime, timezone

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRectF,
    Qt,
    QTimer,
    QVariantAnimation,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QFontMetrics, QGuiApplication, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from glucowidget.config import Settings
from glucowidget.libre.models import GlucoseData
from glucowidget.status import Level, reading_level
from glucowidget.ui import icons
from glucowidget.ui.components import (
    IconButton,
    Skeleton,
    Spinner,
    StatusPill,
    TrendIcon,
    level_color,
)
from glucowidget.ui.sparkline import Sparkline
from glucowidget.ui.theme import DARK, Palette, rgba, ui_font, with_alpha
from glucowidget.units import format_delta, format_value

SHADOW_MARGIN = 16


def age_text(minutes: float) -> str:
    m = int(max(0, minutes))
    if m < 1:
        return "agora"
    if m < 60:
        return f"há {m} min"
    h, rest = divmod(m, 60)
    return f"há {h} h {rest:02d}" if rest else f"há {h} h"


class Card(QWidget):
    """Superfície "glass": fundo translúcido, borda sutil e brilho no topo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.palette_: Palette = DARK
        self.radius = 16.0
        self.accent: QColor | None = None

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        pal = self.palette_
        p.setPen(QPen(pal.border, 1))
        p.setBrush(pal.card)
        p.drawRoundedRect(rect, self.radius, self.radius)
        sheen = QLinearGradient(0, rect.top(), 0, rect.top() + rect.height() * 0.5)
        sheen.setColorAt(0, QColor(255, 255, 255, 14 if pal.name == "dark" else 40))
        sheen.setColorAt(1, QColor(255, 255, 255, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(sheen)
        p.drawRoundedRect(rect, self.radius, self.radius)
        if self.accent is not None:  # filete de cor do estado na borda esquerda
            p.setBrush(self.accent)
            bar = QRectF(rect.left() + 1.5, rect.top() + self.radius, 3, rect.height() - 2 * self.radius)
            p.drawRoundedRect(bar, 1.5, 1.5)
        p.end()


class GlucoseWidget(QWidget):
    request_settings = Signal()
    request_analysis = Signal()
    request_refresh = Signal()
    request_hide = Signal()
    compact_toggled = Signal(bool)
    moved = Signal(int, int)

    PAGE_READING, PAGE_MESSAGE, PAGE_SKELETON = range(3)

    def __init__(self, settings: Settings, palette: Palette):
        super().__init__(None)
        self.settings = settings
        self.pal = palette
        self.data: GlucoseData | None = None
        self.offline = False
        self.ai_enabled = False
        self._shown_value: float | None = None
        self._menu: QMenu | None = None
        self._message_action = None
        self._hovered = False
        self._drag_offset: QPoint | None = None

        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("GlucoWidget")
        self._apply_flags()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(SHADOW_MARGIN, SHADOW_MARGIN - 4, SHADOW_MARGIN, SHADOW_MARGIN + 4)
        self.card = Card()
        outer.addWidget(self.card)
        self.shadow = QGraphicsDropShadowEffect(self.card)
        self.shadow.setOffset(0, 6)
        self.card.setGraphicsEffect(self.shadow)

        self.root = QVBoxLayout(self.card)

        # -- cabeçalho: estado + ações (aparecem no hover) --------------------
        self.header = QWidget()
        hl = QHBoxLayout(self.header)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)
        self.pill = StatusPill()
        self.busy = Spinner(12)
        self.busy.hide()
        hl.addWidget(self.pill)
        hl.addWidget(self.busy)
        hl.addStretch(1)
        self.actions = QWidget()
        al = QHBoxLayout(self.actions)
        al.setContentsMargins(0, 0, 0, 0)
        al.setSpacing(2)
        self.btn_ai = IconButton("sparkles", "Analisar com IA")
        self.btn_refresh = IconButton("refresh", "Atualizar agora")
        self.btn_settings = IconButton("settings", "Configurações")
        self.btn_compact = IconButton("minimize", "Modo compacto (duplo clique)")
        self.btn_close = IconButton("close", "Ocultar (continua na bandeja)")
        for b in (self.btn_ai, self.btn_refresh, self.btn_settings, self.btn_compact, self.btn_close):
            al.addWidget(b)
        self.btn_ai.clicked.connect(self.request_analysis)
        self.btn_refresh.clicked.connect(self.request_refresh)
        self.btn_settings.clicked.connect(self.request_settings)
        self.btn_compact.clicked.connect(self.toggle_compact)
        self.btn_close.clicked.connect(self.request_hide)
        hl.addWidget(self.actions)
        self.actions_fx = QGraphicsOpacityEffect(self.actions)
        self.actions_fx.setOpacity(0.0)
        self.actions.setGraphicsEffect(self.actions_fx)
        self.actions_anim = QPropertyAnimation(self.actions_fx, b"opacity", self)
        self.actions_anim.setDuration(160)
        self.actions_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.root.addWidget(self.header)

        # -- páginas ----------------------------------------------------------
        self.stack = QStackedWidget()
        self.root.addWidget(self.stack, 1)

        reading = QWidget()
        rl = QVBoxLayout(reading)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        value_row = QHBoxLayout()
        value_row.setSpacing(6)
        self.value_label = QLabel("—")
        self.unit_label = QLabel()
        self.trend = TrendIcon()
        value_row.addWidget(self.value_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignBottom)
        value_row.addStretch(1)
        value_row.addWidget(self.trend, 0, Qt.AlignmentFlag.AlignVCenter)
        rl.addLayout(value_row)
        self.sub_label = QLabel()
        rl.addWidget(self.sub_label)
        self.spark = Sparkline()
        rl.addWidget(self.spark, 1)
        self.stack.addWidget(reading)

        message = QWidget()
        ml = QVBoxLayout(message)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(6)
        top = QHBoxLayout()
        self.msg_icon = QLabel()
        self.msg_title = QLabel()
        self.msg_title.setWordWrap(True)
        top.addWidget(self.msg_icon, 0, Qt.AlignmentFlag.AlignTop)
        top.addWidget(self.msg_title, 1)
        ml.addLayout(top)
        self.msg_body = QLabel()
        self.msg_body.setWordWrap(True)
        ml.addWidget(self.msg_body)
        ml.addStretch(1)
        self.msg_button = QPushButton()
        self.msg_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.msg_button.clicked.connect(self._on_message_button)
        ml.addWidget(self.msg_button, 0, Qt.AlignmentFlag.AlignLeft)
        self.stack.addWidget(message)

        self.skeleton = Skeleton()
        self.stack.addWidget(self.skeleton)

        self.num_anim = QVariantAnimation(self)
        self.num_anim.setDuration(600)
        self.num_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.num_anim.valueChanged.connect(self._on_num_anim)

        self.age_timer = QTimer(self)
        self.age_timer.timeout.connect(self._render)
        self.age_timer.start(20_000)

        self._save_pos_timer = QTimer(self)
        self._save_pos_timer.setSingleShot(True)
        self._save_pos_timer.timeout.connect(lambda: self.moved.emit(self.x(), self.y()))

        self.apply_style(settings, palette)
        self.stack.setCurrentIndex(self.PAGE_SKELETON)
        self._restore_position()

    # -- janela ------------------------------------------------------------------
    def _apply_flags(self) -> None:
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        if self.settings.always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        flags |= Qt.WindowType.Tool if self.settings.hide_from_taskbar else Qt.WindowType.Window
        visible = self.isVisible()
        self.setWindowFlags(flags)
        if visible:
            self.show()

    def _restore_position(self) -> None:
        self.adjustSize()
        screen = QGuiApplication.primaryScreen().availableGeometry()
        x, y = self.settings.pos_x, self.settings.pos_y
        on_screen = x is not None and y is not None and any(
            s.availableGeometry().intersects(self.geometry().translated(x - self.x(), y - self.y()))
            for s in QGuiApplication.screens()
        )
        if not on_screen:
            x = screen.right() - self.width() - 12
            y = screen.top() + 12
        self.move(x, y)

    def set_menu(self, menu: QMenu) -> None:
        self._menu = menu

    # -- estilo ------------------------------------------------------------------
    def apply_style(self, settings: Settings, palette: Palette) -> None:
        flags_changed = (
            settings.always_on_top != self.settings.always_on_top
            or settings.hide_from_taskbar != self.settings.hide_from_taskbar
        )
        self.settings, self.pal = settings, palette
        if flags_changed:
            self._apply_flags()
        s = settings.scale
        pal = palette
        compact = settings.compact and self.stack.currentIndex() == self.PAGE_READING

        self.setWindowOpacity(settings.opacity)
        self.card.palette_ = pal
        self.card.radius = (14 if compact else 18) * s
        self.shadow.setBlurRadius(28)
        self.shadow.setColor(QColor(0, 0, 0, 110 if pal.name == "dark" else 45))

        pad_h, pad_v = (14 * s, 8 * s) if compact else (18 * s, 14 * s)
        self.root.setContentsMargins(round(pad_h), round(pad_v), round(pad_h), round(pad_v))
        self.root.setSpacing(round(6 * s))

        hover_bg = with_alpha(pal.text, 22)
        for b in (self.btn_ai, self.btn_refresh, self.btn_settings, self.btn_compact, self.btn_close):
            b.configure(pal.text_muted, hover_bg, round(24 * s))
        self.btn_compact.icon_name = "maximize" if settings.compact else "minimize"
        self.btn_compact.setToolTip("Expandir (duplo clique)" if settings.compact else "Modo compacto (duplo clique)")
        self.btn_ai.setVisible(self.ai_enabled)
        self.busy.set_color(pal.text_subtle)

        self.value_label.setFont(ui_font((30 if compact else 46) * s, QFont.Weight.DemiBold, tabular=True))
        self.unit_label.setFont(ui_font((11 if compact else 13) * s, QFont.Weight.Medium))
        # alinha a linha de base da unidade com a do número
        baseline_pad = QFontMetrics(self.value_label.font()).descent() - QFontMetrics(self.unit_label.font()).descent()
        self.unit_label.setStyleSheet(f"color: {rgba(pal.text_subtle)}; padding-bottom: {max(0, baseline_pad)}px;")
        self.unit_label.setText(settings.unit)
        tsize = round((26 if compact else 36) * s)
        self.trend.setFixedSize(tsize, tsize)
        self.trend.animate = not settings.reduce_motion
        self.sub_label.setFont(ui_font(12 * s))
        self.sub_label.setStyleSheet(f"color: {rgba(pal.text_muted)};")

        self.msg_title.setFont(ui_font(14 * s, QFont.Weight.DemiBold))
        self.msg_title.setStyleSheet(f"color: {rgba(pal.text)};")
        self.msg_body.setFont(ui_font(12 * s))
        self.msg_body.setStyleSheet(f"color: {rgba(pal.text_muted)};")
        self.msg_button.setFont(ui_font(12 * s, QFont.Weight.DemiBold))
        self.msg_button.setStyleSheet(
            f"QPushButton {{ background: {rgba(pal.accent)}; color: {rgba(pal.accent_text)}; border: none;"
            f" border-radius: {round(8 * s)}px; padding: {round(6 * s)}px {round(14 * s)}px; }}"
            f"QPushButton:hover {{ background: {rgba(pal.accent.lighter(112))}; }}"
        )
        self.skeleton.set_color(with_alpha(pal.text, 26))

        self.header.setVisible(not compact)
        self.sub_label.setVisible(not compact)
        self.spark.setVisible(not compact)
        self.skeleton.compact = settings.compact

        if compact:
            self.card.setFixedSize(round(178 * s), round(64 * s))
        elif self.stack.currentIndex() == self.PAGE_MESSAGE:
            self.card.setFixedSize(round(290 * s), round(160 * s))
        else:
            self.card.setFixedSize(round(290 * s), round(196 * s))
        self.adjustSize()
        self._render()

    # -- conteúdo ------------------------------------------------------------------
    def set_ai_enabled(self, enabled: bool) -> None:
        self.ai_enabled = enabled
        self.btn_ai.setVisible(enabled)

    def set_updating(self, busy: bool) -> None:
        if busy and not self.settings.compact:
            self.busy.start()
        else:
            self.busy.stop()

    def show_loading(self) -> None:
        if self.data is None:
            self._set_page(self.PAGE_SKELETON)

    def show_data(self, data: GlucoseData, offline: bool = False) -> None:
        self.data = data
        self.offline = offline
        self._set_page(self.PAGE_READING)
        current = data.current
        if current and not offline:
            old = self._shown_value
            new = current.value_mgdl
            if old is not None and old != new and not self.settings.reduce_motion and self.isVisible():
                self.num_anim.stop()
                self.num_anim.setStartValue(float(old))
                self.num_anim.setEndValue(float(new))
                self.num_anim.start()
            self._shown_value = new
        self._render()

    def show_offline(self) -> None:
        """Mantém a última leitura, sinalizando a falta de conexão."""
        if self.data is None:
            self.show_message(
                "wifi_off", "Sem conexão",
                "Não foi possível falar com o LibreLinkUp. Tentando novamente…",
                "Tentar agora", self.request_refresh.emit,
            )
        else:
            self.offline = True
            self._render()

    def show_message(self, icon_name: str, title: str, body: str, button: str = "", action=None) -> None:
        self._message_action = action
        self.msg_icon.setPixmap(icons.pixmap(icon_name, self.pal.accent if icon_name != "alert" else self.pal.high,
                                             round(22 * self.settings.scale)))
        self.msg_title.setText(title)
        self.msg_body.setText(body)
        self.msg_button.setText(button)
        self.msg_button.setVisible(bool(button))
        self.pill.set_state("", self.pal.stale, self.pal.text)
        self.card.accent = None
        self._set_page(self.PAGE_MESSAGE)

    def _on_message_button(self):
        if self._message_action:
            self._message_action()

    def _set_page(self, page: int) -> None:
        if self.stack.currentIndex() != page:
            self.stack.setCurrentIndex(page)
            self.apply_style(self.settings, self.pal)

    def _on_num_anim(self, value) -> None:
        self.value_label.setText(format_value(float(value), self.settings.unit))

    def current_level(self) -> Level:
        return reading_level(self.data.current if self.data else None, self.settings)

    def _render(self) -> None:
        if self.stack.currentIndex() != self.PAGE_READING or not self.data:
            return
        st, pal = self.settings, self.pal
        current = self.data.current
        level = reading_level(current, st)
        color = level_color(level, pal)
        if current is None:
            self.value_label.setText("—")
            self.sub_label.setText("Sem leituras recentes")
            return

        if self.num_anim.state() != QVariantAnimation.State.Running:
            self.value_label.setText(format_value(current.value_mgdl, st.unit))
        self.value_label.setStyleSheet(f"color: {rgba(color)};")
        self.trend.set_trend(current.trend if level != Level.STALE else current.trend, color)
        self.card.accent = color
        self.pill.set_state(level.label, color, pal.text, 11 * st.scale)

        age = current.age_minutes()
        parts = [age_text(age)]
        delta = self.data.delta_mgdl
        if delta is not None and level != Level.STALE:
            parts.append(f"{format_delta(delta, st.unit)} {st.unit}")
        if self.offline:
            parts.insert(0, "Sem conexão")
        self.sub_label.setText("  ·  ".join(parts))

        self.spark.set_data(self.data.history, st.chart_hours, st.target_low, st.target_high,
                            st.unit, pal, stale=level == Level.STALE)
        tip = f"{format_value(current.value_mgdl, st.unit)} {st.unit} · {level.label} · {current.trend.label} · {age_text(age)}"
        self.card.setToolTip(tip if st.compact else "")
        self.card.update()

    # -- interação ------------------------------------------------------------------
    def toggle_compact(self) -> None:
        self.settings.compact = not self.settings.compact
        self.apply_style(self.settings, self.pal)
        self.compact_toggled.emit(self.settings.compact)

    def _fade_actions(self, visible: bool) -> None:
        target = 1.0 if visible else 0.0
        if self.settings.reduce_motion:
            self.actions_fx.setOpacity(target)
            return
        self.actions_anim.stop()
        self.actions_anim.setStartValue(self.actions_fx.opacity())
        self.actions_anim.setEndValue(target)
        self.actions_anim.start()

    def enterEvent(self, e):
        self._hovered = True
        self._fade_actions(True)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._hovered = False
        self._fade_actions(False)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            handle = self.windowHandle()
            if handle is not None and handle.startSystemMove():
                self._drag_offset = None
            else:
                self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None and e.buttons() & Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag_offset = None
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton and self.stack.currentIndex() == self.PAGE_READING:
            self.toggle_compact()

    def moveEvent(self, e):
        self._save_pos_timer.start(500)
        super().moveEvent(e)

    def contextMenuEvent(self, e):
        if self._menu:
            self._menu.popup(e.globalPos())
