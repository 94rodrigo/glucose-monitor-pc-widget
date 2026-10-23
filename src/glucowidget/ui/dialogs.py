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
from glucowidget.i18n import N_, get_language, tr
from glucowidget.config import Settings
from glucowidget.metrics import Metrics
from glucowidget.ui import icons
from glucowidget.ui.components import SegmentedControl, Spinner, card
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
from glucowidget.ui.titlebar import install_titlebar, native_window_flags, use_custom_titlebar, window_flags
from glucowidget.units import format_value


def enable_min_max(dialog: QDialog) -> None:
    """Faz o diálogo se comportar como uma janela normal (minimizar, maximizar, sem ficar por cima).

    No Wayland a decoração do Qt não responde a esses botões; lá o diálogo fica sem moldura e
    ganha uma barra de título própria (ver ``install_titlebar``).
    """
    dialog.setWindowFlags(window_flags() if use_custom_titlebar() else native_window_flags())


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

    NAV = [(N_("Account"), "user_plus", AccountPage), (N_("Glucose"), "drop", RangePage),
           (N_("Appearance"), "settings", AppearancePage), (N_("Alerts"), "alert", AlertsPage),
           (N_("AI"), "sparkles", AIPage), (N_("About"), "check", AboutPage)]

    def __init__(self, settings: Settings, palette: Palette, start_page: str = "", parent=None):
        super().__init__(parent)
        enable_min_max(self)
        self.setWindowTitle(tr("Settings — {app}", app=APP_NAME))
        self.setStyleSheet(dialog_qss(palette))
        self.resize(820, 600)
        self.settings = copy.deepcopy(settings)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        install_titlebar(self, palette, root)
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
            item = QListWidgetItem(icons.icon(icon_name, palette.text_muted), tr(label))
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        start = next((i for i, (label, *_ ) in enumerate(self.NAV) if label == start_page), 0)
        self.nav.setCurrentRow(start)

        bar, h = footer_bar(palette)
        self.error = QLabel()
        self.error.setObjectName("err")
        h.addWidget(self.error, 1)
        cancel = QPushButton(tr("Cancel"))
        cancel.clicked.connect(self.reject)
        save = QPushButton(tr("Save"))
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
    language_changed = Signal(str)

    def __init__(self, settings: Settings, palette: Palette, parent=None):
        super().__init__(parent)
        enable_min_max(self)
        self.setWindowTitle(tr("Welcome to {app}", app=APP_NAME))
        self.setStyleSheet(dialog_qss(palette))
        self.resize(640, 620)
        self.settings = copy.deepcopy(settings)
        self.pal = palette

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        install_titlebar(self, palette, root)

        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(28, 24, 28, 0)
        hl.setSpacing(6)
        logo = QLabel()
        logo.setPixmap(icons.pixmap("drop", palette.accent, 28))
        self.step_label = QLabel()
        self.step_label.setObjectName("subtle")
        self.dots = StepDots(3, palette)
        self.lang = SegmentedControl([("en", "EN"), ("pt", "PT")])
        self.lang.set_value(get_language())
        self.lang.changed.connect(self._language_chosen)
        top = QHBoxLayout()
        top.addWidget(logo)
        top.addStretch(1)
        top.addWidget(self.lang)
        top.addSpacing(16)
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
        self.demo_btn = QPushButton(tr("Explore in demo mode"))
        self.demo_btn.setObjectName("ghost")
        self.demo_btn.clicked.connect(self._demo)
        self.error = QLabel()
        self.error.setObjectName("err")
        self.back_btn = QPushButton(tr("Back"))
        self.back_btn.clicked.connect(lambda: self._go(self.stack.currentIndex() - 1))
        self.skip_btn = QPushButton(tr("Skip"))
        self.skip_btn.setObjectName("ghost")
        self.skip_btn.clicked.connect(self._finish)
        self.next_btn = QPushButton(tr("Continue"))
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
        self.step_label.setText(tr("Step {i} of {n}", i=i + 1, n=len(self.pages)))
        self.back_btn.setVisible(i > 0)
        self.demo_btn.setVisible(i == 0)
        self.skip_btn.setVisible(i == len(self.pages) - 1)
        self.next_btn.setText(tr("Finish") if i == len(self.pages) - 1 else tr("Continue"))
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

    def _language_chosen(self, code: str):
        self.language_changed.emit(code)
        self.close()

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
        enable_min_max(self)
        self.pal = palette
        self.setWindowTitle(tr("AI analysis — {app}", app=APP_NAME))
        self.setStyleSheet(dialog_qss(palette))
        self.resize(640, 680)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        install_titlebar(self, palette, root)
        head = QWidget()
        hl = QVBoxLayout(head)
        hl.setContentsMargins(24, 22, 24, 12)
        hl.setSpacing(12)
        title_row = QHBoxLayout()
        ico = QLabel()
        ico.setPixmap(icons.pixmap("sparkles", palette.accent, 22))
        self.title = QLabel(tr("Analysis of your readings"))
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
        wait = QLabel(tr("Analyzing your readings…"))
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
        disclaimer = QLabel(tr("Generated by AI · does not replace medical advice"))
        disclaimer.setObjectName("subtle")
        h.addWidget(disclaimer, 1)
        self.copy_btn = QPushButton(icons.icon("copy", palette.text_muted), tr(" Copy"))
        self.copy_btn.clicked.connect(self._copy)
        self.again_btn = QPushButton(icons.icon("refresh", palette.accent_text), tr(" Analyze again"))
        self.again_btn.setObjectName("primary")
        self.again_btn.clicked.connect(self.rerun)
        h.addWidget(self.copy_btn)
        h.addWidget(self.again_btn)
        root.addWidget(bar)

    def set_context(self, metrics: Metrics | None, unit: str, hours: int | str, provider: str, model: str):
        while self.chips.count():
            item = self.chips.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.subtitle.setText(tr("Last {hours} h · {provider} · {model}", hours=hours, provider=provider, model=model))
        if not metrics:
            return
        chips = [
            (tr("Mean"), f"{format_value(metrics.mean, unit)}", tr("Mean in {unit}", unit=unit)),
            (tr("In range"), f"{metrics.tir:.0f}%", tr("Time in range (TIR)")),
            (tr("Variation"), f"{metrics.cv:.0f}%", tr("Coefficient of variation — ideal ≤ 36%")),
            (tr("Min–Max"), f"{format_value(metrics.min, unit)}–{format_value(metrics.max, unit)}",
             tr("Lowest and highest reading")),
        ]
        for label, value, hint in chips:
            self.chips.addWidget(MetricChip(label, value, self.pal, hint), 1)

    def show_loading(self):
        self.copy_btn.setText(tr(" Copy"))
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
        self.copy_btn.setText(tr(" Copied!"))
