"""Diálogos: configurações, onboarding e análise de IA."""
from __future__ import annotations

import copy

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from glucowidget import APP_NAME
from glucowidget.config import Settings
from glucowidget.metrics import Metrics
from glucowidget.ui import icons
from glucowidget.ui.components import Spinner, card
from glucowidget.ui.pages import (
    AboutPage,
    AccountPage,
    AIPage,
    AlertsPage,
    AppearancePage,
    RangePage,
    StepDots,
)
from glucowidget.ui.theme import Palette, dialog_qss, rgba, with_alpha
from glucowidget.units import format_value


def scrollable(widget: QWidget) -> QScrollArea:
    area = QScrollArea()
    area.setWidget(widget)
    area.setWidgetResizable(True)
    area.setFrameShape(QFrame.Shape.NoFrame)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    return area


def footer_bar(palette: Palette) -> tuple[QWidget, QHBoxLayout]:
    bar = QWidget()
    bar.setStyleSheet(f"QWidget#footer {{ border-top: 1px solid {rgba(palette.border)}; }}")
    bar.setObjectName("footer")
    h = QHBoxLayout(bar)
    h.setContentsMargins(20, 12, 20, 12)
    h.setSpacing(8)
    return bar, h


class SettingsDialog(QDialog):
    saved = Signal(object)  # Settings

    NAV = [("Conta", "user_plus", AccountPage), ("Glicemia", "drop", RangePage),
           ("Aparência", "settings", AppearancePage), ("Alertas", "alert", AlertsPage),
           ("IA", "sparkles", AIPage), ("Sobre", "check", AboutPage)]

    def __init__(self, settings: Settings, palette: Palette, start_page: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Configurações — {APP_NAME}")
        self.setStyleSheet(dialog_qss(palette))
        self.resize(820, 600)
        self.settings = copy.deepcopy(settings)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)
        root.addLayout(body, 1)

        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(190)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(12, 20, 12, 12)
        brand = QLabel(APP_NAME)
        brand.setObjectName("h2")
        brand.setContentsMargins(10, 0, 0, 12)
        sl.addWidget(brand)
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(16, 16))
        sl.addWidget(self.nav, 1)
        body.addWidget(sidebar)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.pages = []
        for label, icon_name, cls in self.NAV:
            page = cls(palette)
            page.load(self.settings)
            self.pages.append(page)
            self.stack.addWidget(scrollable(page))
            item = QListWidgetItem(icons.icon(icon_name, palette.text_muted), label)
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        start = next((i for i, (label, *_ ) in enumerate(self.NAV) if label == start_page), 0)
        self.nav.setCurrentRow(start)

        bar, h = footer_bar(palette)
        self.error = QLabel()
        self.error.setObjectName("err")
        h.addWidget(self.error, 1)
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        save = QPushButton("Salvar")
        save.setObjectName("primary")
        save.setDefault(True)
        save.clicked.connect(self._save)
        h.addWidget(cancel)
        h.addWidget(save)
        root.addWidget(bar)

    def _save(self):
        new = copy.deepcopy(self.settings)
        for i, page in enumerate(self.pages):
            errors = page.apply(new)
            if errors:
                self.nav.setCurrentRow(i)
                self.error.setText(errors[0])
                return
        self.error.clear()
        self.saved.emit(new)
        self.accept()


class OnboardingDialog(QDialog):
    finished_setup = Signal(object, bool)  # Settings, demo

    def __init__(self, settings: Settings, palette: Palette, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Bem-vindo ao {APP_NAME}")
        self.setStyleSheet(dialog_qss(palette))
        self.resize(640, 620)
        self.settings = copy.deepcopy(settings)
        self.pal = palette

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(28, 24, 28, 0)
        hl.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(icons.pixmap("drop", palette.accent, 28))
        self.step_label = QLabel()
        self.step_label.setObjectName("subtle")
        self.dots = StepDots(3, palette)
        top = QHBoxLayout()
        top.addWidget(logo)
        top.addStretch(1)
        top.addWidget(self.step_label)
        top.addSpacing(10)
        top.addWidget(self.dots)
        hl.addLayout(top)
        root.addWidget(head)

        self.stack = QStackedWidget()
        self.pages = [AccountPage(palette), RangePage(palette), AIPage(palette)]
        for p in self.pages:
            p.load(self.settings)
            self.stack.addWidget(scrollable(p))
        root.addWidget(self.stack, 1)

        bar, h = footer_bar(palette)
        self.demo_btn = QPushButton("Explorar em modo demonstração")
        self.demo_btn.setObjectName("ghost")
        self.demo_btn.clicked.connect(self._demo)
        self.error = QLabel()
        self.error.setObjectName("err")
        self.back_btn = QPushButton("Voltar")
        self.back_btn.clicked.connect(lambda: self._go(self.stack.currentIndex() - 1))
        self.skip_btn = QPushButton("Pular")
        self.skip_btn.setObjectName("ghost")
        self.skip_btn.clicked.connect(self._finish)
        self.next_btn = QPushButton("Continuar")
        self.next_btn.setObjectName("primary")
        self.next_btn.setDefault(True)
        self.next_btn.clicked.connect(self._next)
        h.addWidget(self.demo_btn)
        h.addWidget(self.error, 1)
        h.addWidget(self.back_btn)
        h.addWidget(self.skip_btn)
        h.addWidget(self.next_btn)
        root.addWidget(bar)
        self._go(0)

    def _go(self, i: int):
        i = max(0, min(len(self.pages) - 1, i))
        self.stack.setCurrentIndex(i)
        self.dots.set_index(i)
        self.step_label.setText(f"Etapa {i + 1} de {len(self.pages)}")
        self.back_btn.setVisible(i > 0)
        self.demo_btn.setVisible(i == 0)
        self.skip_btn.setVisible(i == len(self.pages) - 1)
        self.next_btn.setText("Concluir" if i == len(self.pages) - 1 else "Continuar")
        self.error.clear()

    def _next(self):
        i = self.stack.currentIndex()
        page = self.pages[i]
        if i == 0:
            errors = page.validate()
            if errors:
                self.error.setText(errors[0])
                return
        errors = page.apply(self.settings)
        if errors:
            self.error.setText(errors[0])
            return
        if i == len(self.pages) - 1:
            self._finish()
        else:
            self._go(i + 1)

    def _finish(self, *_):
        self.settings.onboarded = True
        self.finished_setup.emit(self.settings, False)
        self.accept()

    def _demo(self):
        self.finished_setup.emit(self.settings, True)
        self.accept()


class MetricChip(QFrame):
    def __init__(self, label: str, value: str, palette: Palette, hint: str = ""):
        super().__init__()
        self.setObjectName("card")
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 10, 14, 10)
        v.setSpacing(2)
        lab = QLabel(label.upper())
        lab.setStyleSheet(f"color: {rgba(palette.text_subtle)}; font-size: 10px; font-weight: 600; letter-spacing: 1px;")
        val = QLabel(value)
        val.setStyleSheet("font-size: 18px; font-weight: 600;")
        v.addWidget(lab)
        v.addWidget(val)
        if hint:
            self.setToolTip(hint)


class AnalysisDialog(QDialog):
    rerun = Signal()

    def __init__(self, palette: Palette, parent=None):
        super().__init__(parent)
        self.pal = palette
        self.setWindowTitle(f"Análise com IA — {APP_NAME}")
        self.setStyleSheet(dialog_qss(palette))
        self.resize(640, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(24, 22, 24, 12)
        hl.setSpacing(12)
        title_row = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.pixmap("sparkles", palette.accent, 22))
        self.title = QLabel("Análise das suas leituras")
        self.title.setObjectName("h1")
        title_row.addWidget(ico)
        title_row.addWidget(self.title, 1)
        hl.addLayout(title_row)
        self.subtitle = QLabel()
        self.subtitle.setObjectName("muted")
        hl.addWidget(self.subtitle)
        self.chips = QHBoxLayout()
        self.chips.setSpacing(8)
        hl.addLayout(self.chips)
        root.addWidget(head)

        self.body = QStackedWidget()
        loading = QWidget()
        ll = QVBoxLayout(loading)
        ll.addStretch(1)
        self.spinner = Spinner(36)
        self.spinner.set_color(palette.accent)
        ll.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignHCenter)
        wait = QLabel("Analisando suas leituras…")
        wait.setObjectName("muted")
        ll.addWidget(wait, 0, Qt.AlignmentFlag.AlignHCenter)
        ll.addStretch(2)
        self.body.addWidget(loading)

        content = card()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(18, 12, 18, 12)
        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(True)
        cl.addWidget(self.text)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(24, 0, 24, 0)
        wl.addWidget(content)
        self.body.addWidget(wrap)

        err = QWidget()
        el = QVBoxLayout(err)
        el.setContentsMargins(24, 24, 24, 24)
        el.addStretch(1)
        err_icon = QLabel()
        err_icon.setPixmap(icons.pixmap("alert", palette.high, 32))
        el.addWidget(err_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        self.err_text = QLabel()
        self.err_text.setWordWrap(True)
        self.err_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        el.addWidget(self.err_text)
        el.addStretch(2)
        self.body.addWidget(err)
        root.addWidget(self.body, 1)

        bar, h = footer_bar(palette)
        disclaimer = QLabel("Gerado por IA · não substitui orientação médica")
        disclaimer.setObjectName("subtle")
        h.addWidget(disclaimer, 1)
        self.copy_btn = QPushButton(icons.icon("copy", palette.text_muted), " Copiar")
        self.copy_btn.clicked.connect(self._copy)
        self.again_btn = QPushButton(icons.icon("refresh", palette.accent_text), " Analisar novamente")
        self.again_btn.setObjectName("primary")
        self.again_btn.clicked.connect(self.rerun)
        h.addWidget(self.copy_btn)
        h.addWidget(self.again_btn)
        root.addWidget(bar)

    def set_context(self, metrics: Metrics | None, unit: str, hours: int, provider: str, model: str):
        while self.chips.count():
            item = self.chips.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.subtitle.setText(f"Últimas {hours} h · {provider} · {model}")
        if not metrics:
            return
        chips = [
            ("Média", f"{format_value(metrics.mean, unit)}", f"Média em {unit}"),
            ("No alvo", f"{metrics.tir:.0f}%", "Tempo no alvo (TIR)"),
            ("Variação", f"{metrics.cv:.0f}%", "Coeficiente de variação — ideal ≤ 36%"),
            ("GMI", f"{metrics.gmi:.1f}%", "Indicador de gestão da glicose (estimativa de A1c)"),
        ]
        for label, value, hint in chips:
            self.chips.addWidget(MetricChip(label, value, self.pal, hint), 1)

    def show_loading(self):
        self.again_btn.setEnabled(False)
        self.copy_btn.setEnabled(False)
        self.spinner.start()
        self.body.setCurrentIndex(0)

    def show_result(self, markdown: str):
        self.spinner.stop()
        self.again_btn.setEnabled(True)
        self.copy_btn.setEnabled(True)
        self.text.document().setDefaultStyleSheet(
            f"h1,h2,h3 {{ color: {rgba(self.pal.text)}; }} strong {{ color: {rgba(self.pal.text)}; }}"
            f" a {{ color: {rgba(self.pal.accent)}; }} li {{ margin-bottom: 4px; }}"
            f" code {{ background: {rgba(with_alpha(self.pal.text, 20))}; }}"
        )
        self.text.setMarkdown(markdown)
        self.body.setCurrentIndex(1)

    def show_error(self, message: str):
        self.spinner.stop()
        self.again_btn.setEnabled(True)
        self.copy_btn.setEnabled(False)
        self.err_text.setText(message)
        self.body.setCurrentIndex(2)

    def _copy(self):
        QGuiApplication.clipboard().setText(self.text.toMarkdown())
        self.copy_btn.setText(" Copiado!")
