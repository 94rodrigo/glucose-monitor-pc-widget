"""Ponto de entrada e controlador: polling, bandeja, alertas, IA e diálogos."""
from __future__ import annotations

import argparse
import copy
import logging
import os
import signal
import sys
from PySide6.QtCore import QCoreApplication, QLibraryInfo, QObject, Qt, QTimer, QTranslator
from PySide6.QtGui import QAction, QActionGroup, QGuiApplication
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from glucowidget import APP_ID, APP_NAME
from glucowidget import metrics as metrics_mod
from glucowidget.ai.prompt import build_user_prompt, system_prompt
from glucowidget.ai.providers import PROVIDERS, analyze
from glucowidget.autostart import set_autostart
from glucowidget.config import LIBRE_PASSWORD, Settings, ai_key_name, get_secret
from glucowidget.i18n import get_language, set_language, tr
from glucowidget.libre.models import GlucoseData
from glucowidget.sources import DemoSource, LibreSource, SetupRequired, classify_error
from glucowidget.status import Level
from glucowidget.ui.async_utils import run_async
from glucowidget.ui.components import level_color
from glucowidget.ui.dialogs import AnalysisDialog, OnboardingDialog, SettingsDialog
from glucowidget.ui.theme import dialog_qss, load_fonts, palette_for
from glucowidget.ui.tray import app_icon, value_icon
from glucowidget.ui.widget import GlucoseWidget, age_text
from glucowidget.units import format_value

log = logging.getLogger(__name__)

ACCOUNT_FIELDS = ("email", "region", "patient_id", "api_version")
MAX_BACKOFF_SECONDS = 600


class Controller(QObject):
    def __init__(self, settings: Settings, demo: str | None = None, persist: bool = True):
        super().__init__()
        set_language(settings.language)
        self._qt_translator: QTranslator | None = None
        self._install_qt_translator()
        self.settings = settings
        self.demo = demo
        self.persist = persist
        self.palette = palette_for(settings.theme)
        self.source = None
        self.data: GlucoseData | None = None
        self.fetching = False
        self.failures = 0
        self.last_level: Level | None = None
        self.analysis_dialog: AnalysisDialog | None = None
        self.settings_dialog: SettingsDialog | None = None
        self.last_analysis: str | None = None
        self.analysis_running = False

        self.widget = GlucoseWidget(settings, self.palette)
        self.widget.request_refresh.connect(self.refresh_now)
        self.widget.request_settings.connect(lambda: self.open_settings())
        self.widget.request_analysis.connect(self.open_analysis)
        self.widget.request_hide.connect(self.hide_widget)
        self.widget.compact_toggled.connect(lambda _: (self.save(), self._sync_menu()))
        self.widget.moved.connect(self._on_moved)

        self.menu = self._build_menu()
        self.widget.set_menu(self.menu)
        self.tray = None
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(app_icon(), self)
            self.tray.setContextMenu(self.menu)
            self.tray.setToolTip(APP_NAME)
            self.tray.activated.connect(self._on_tray_activated)
            self.tray.messageClicked.connect(self._on_tray_message)
            self.tray.show()
        else:
            self.widget.close_means_quit = True
            self.widget.retranslate()

        self.poll_timer = QTimer(self)
        self.poll_timer.setSingleShot(True)
        self.poll_timer.timeout.connect(self.fetch)
        self.ai_timer = QTimer(self)
        self.ai_timer.timeout.connect(lambda: self.run_analysis(auto=True))

        hints = QGuiApplication.styleHints()
        if hasattr(hints, "colorSchemeChanged"):
            hints.colorSchemeChanged.connect(lambda *_: self._retheme())

        self._apply_theme_to_menu()
        self.widget.set_ai_enabled(settings.ai_enabled)
        self._configure_ai_timer()
        self.widget.show()

        if not settings.onboarded and not demo:
            self._show_setup_message()
            QTimer.singleShot(300, self.open_onboarding)
        else:
            self.rebuild_source()

    # -- persistência ---------------------------------------------------------------
    def save(self) -> None:
        if self.persist:
            self.settings.save()

    def _on_moved(self, x: int, y: int) -> None:
        self.settings.pos_x, self.settings.pos_y = x, y
        self.save()

    # -- menu / bandeja ------------------------------------------------------------
    def _build_menu(self) -> QMenu:
        menu = QMenu()
        self.act_header = QAction(APP_NAME, menu)
        self.act_header.setEnabled(False)
        menu.addAction(self.act_header)
        menu.addSeparator()
        self.act_toggle = QAction(tr("Hide widget"), menu)
        self.act_toggle.triggered.connect(self.toggle_widget)
        menu.addAction(self.act_toggle)
        act_refresh = QAction(tr("Refresh now"), menu)
        act_refresh.triggered.connect(self.refresh_now)
        menu.addAction(act_refresh)
        self.act_ai = QAction(tr("Analyze with AI…"), menu)
        self.act_ai.triggered.connect(self.open_analysis)
        menu.addAction(self.act_ai)
        menu.addSeparator()
        self.act_compact = QAction(tr("Compact mode"), menu, checkable=True)
        self.act_compact.triggered.connect(lambda: self.widget.toggle_compact())
        menu.addAction(self.act_compact)
        self.act_on_top = QAction(tr("Always on top"), menu, checkable=True)
        self.act_on_top.triggered.connect(self._toggle_on_top)
        menu.addAction(self.act_on_top)
        unit_menu = menu.addMenu(tr("Unit"))
        self.unit_group = QActionGroup(menu)
        for unit in ("mg/dL", "mmol/L"):
            a = QAction(unit, unit_menu, checkable=True)
            a.triggered.connect(lambda _=False, u=unit: self._set_unit(u))
            self.unit_group.addAction(a)
            unit_menu.addAction(a)
        menu.addSeparator()
        act_settings = QAction(tr("Settings…"), menu)
        act_settings.triggered.connect(lambda: self.open_settings())
        menu.addAction(act_settings)
        menu.addSeparator()
        act_quit = QAction(tr("Quit"), menu)
        act_quit.triggered.connect(QApplication.quit)
        menu.addAction(act_quit)
        menu.aboutToShow.connect(self._sync_menu)
        self._sync_menu()
        return menu

    def _sync_menu(self) -> None:
        self.act_toggle.setText(tr("Hide widget") if self.widget.isVisible() else tr("Show widget"))
        self.act_compact.setChecked(self.settings.compact)
        self.act_on_top.setChecked(self.settings.always_on_top)
        self.act_ai.setVisible(self.settings.ai_enabled)
        for a in self.unit_group.actions():
            a.setChecked(a.text() == self.settings.unit)
        if self.data and self.data.current:
            c = self.data.current
            self.act_header.setText(
                f"{format_value(c.value_mgdl, self.settings.unit)} {self.settings.unit} {c.trend.arrow}  ·  "
                f"{age_text(c.age_minutes())}"
            )

    def _install_qt_translator(self) -> None:
        """Traduz os textos nativos do Qt (menu de copiar/colar, botões padrão)."""
        app = QCoreApplication.instance()
        if self._qt_translator is not None:
            app.removeTranslator(self._qt_translator)
            self._qt_translator = None
        if get_language() == "pt":
            translator = QTranslator(self)
            path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
            if translator.load("qtbase_pt_BR", path):
                app.installTranslator(translator)
                self._qt_translator = translator

    def _refresh_menu(self) -> None:
        """Recria o menu (por exemplo, após trocar o idioma)."""
        self.menu = self._build_menu()
        self.widget.set_menu(self.menu)
        if self.tray:
            self.tray.setContextMenu(self.menu)
        self._apply_theme_to_menu()

    def _apply_theme_to_menu(self) -> None:
        self.menu.setStyleSheet(dialog_qss(self.palette))

    def _on_tray_activated(self, reason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.toggle_widget()

    def _on_tray_message(self) -> None:
        if self.last_analysis:
            self._ensure_analysis_dialog()
            self.analysis_dialog.show_result(self.last_analysis)
            self._present(self.analysis_dialog)

    def toggle_widget(self) -> None:
        if self.widget.isVisible():
            self.hide_widget()
        else:
            self.widget.show()
            self.widget.raise_()

    def hide_widget(self) -> None:
        if self.tray is None:
            QApplication.quit()
            return
        self.widget.hide()

    def _toggle_on_top(self) -> None:
        new = copy.deepcopy(self.settings)
        new.always_on_top = not new.always_on_top
        self.apply_settings(new)

    def _set_unit(self, unit: str) -> None:
        new = copy.deepcopy(self.settings)
        new.unit = unit
        self.apply_settings(new)

    def _update_tray(self) -> None:
        if not self.tray:
            return
        c = self.data.current if self.data else None
        if not c:
            self.tray.setIcon(app_icon())
            self.tray.setToolTip(APP_NAME)
            return
        level = self.widget.current_level()
        text = format_value(c.value_mgdl, self.settings.unit)
        self.tray.setIcon(value_icon(text, level_color(level, self.palette)))
        self.tray.setToolTip(
            f"{APP_NAME}\n{text} {self.settings.unit} {c.trend.arrow} · {level.label}\n{age_text(c.age_minutes())}"
        )

    # -- tema ----------------------------------------------------------------------
    def _retheme(self) -> None:
        self.palette = palette_for(self.settings.theme)
        self.widget.apply_style(self.settings, self.palette)
        self._apply_theme_to_menu()
        self._update_tray()

    # -- dados ----------------------------------------------------------------------
    def rebuild_source(self) -> None:
        if self.source:
            self.source.close()
            self.source = None
        self.poll_timer.stop()
        self.failures = 0
        if self.demo:
            self.source = DemoSource(self.demo)
        else:
            try:
                self.source = LibreSource(
                    self.settings.email, get_secret(LIBRE_PASSWORD), self.settings.region,
                    self.settings.patient_id, self.settings.api_version,
                )
            except SetupRequired:
                self._show_setup_message()
                return
        self.widget.show_loading()
        self.fetch()

    def refresh_now(self) -> None:
        if self.source is None:
            self.rebuild_source()
        else:
            self.fetch()

    def fetch(self) -> None:
        if self.fetching or self.source is None:
            return
        self.fetching = True
        self.widget.set_updating(True)
        source = self.source
        run_async(source.fetch, lambda d: self._on_data(source, d), lambda e: self._on_error(source, e))

    def _schedule(self, seconds: float) -> None:
        self.poll_timer.start(int(seconds * 1000))

    def _on_data(self, source, data: GlucoseData) -> None:
        self.fetching = False
        self.widget.set_updating(False)
        if source is not self.source:
            return
        self.failures = 0
        if isinstance(source, LibreSource):
            changed = False
            if source.region and source.region != self.settings.region:
                self.settings.region = source.region
                changed = True
            if source.patient_id and not self.settings.patient_id:
                self.settings.patient_id = source.patient_id
                changed = True
            if changed:
                self.save()
        self.data = data
        self.widget.show_data(data)
        self._update_tray()
        self._notify_if_needed()
        self._schedule(self.settings.poll_seconds)

    def _on_error(self, source, exc: Exception) -> None:
        self.fetching = False
        self.widget.set_updating(False)
        if source is not self.source:
            return
        kind = classify_error(exc)
        log.info("Falha ao buscar dados (%s): %s", kind, exc)
        if kind == "network":
            self.failures += 1
            self.widget.show_offline()
            delay = min(MAX_BACKOFF_SECONDS, self.settings.poll_seconds * 2 ** min(self.failures, 5))
            self._schedule(delay)
            return
        if kind == "auth":
            # não insiste para não bloquear a conta; aguarda o usuário revisar
            self.widget.show_message("lock", tr("Couldn't sign in"), str(exc), tr("Review account"),
                                     lambda: self.open_settings("Account"))
        elif kind == "terms":
            self.widget.show_message("alert", tr("Action needed in LibreLinkUp"), str(exc), tr("Try again"),
                                     self.refresh_now)
            self._schedule(MAX_BACKOFF_SECONDS)
        elif kind == "nopatient":
            self.widget.show_message("user_plus", tr("No patient connected"), str(exc), tr("Try again"),
                                     self.refresh_now)
            self._schedule(MAX_BACKOFF_SECONDS)
        else:
            self.widget.show_message("alert", tr("Something went wrong"), str(exc) or exc.__class__.__name__,
                                     tr("Try again"), self.refresh_now)
            self._schedule(MAX_BACKOFF_SECONDS)
        self.data = None
        self._update_tray()

    def _show_setup_message(self) -> None:
        self.widget.show_message(
            "user_plus", tr("Connect your account"),
            tr("Sign in with your LibreLinkUp email and password to see your glucose here."),
            tr("Set up"), self.open_onboarding if not self.settings.onboarded else lambda: self.open_settings("Account"),
        )

    # -- alertas ---------------------------------------------------------------------
    def _notify_if_needed(self) -> None:
        level = self.widget.current_level()
        previous, self.last_level = self.last_level, level
        st = self.settings
        if not (self.tray and st.notify_enabled and level.is_alert) or level == previous:
            return
        if st.notify_urgent_only and not level.is_urgent:
            return
        if previous is None and not level.is_urgent:
            return  # evita alerta ao abrir o app, exceto se urgente
        c = self.data.current
        icon = (QSystemTrayIcon.MessageIcon.Critical if level.is_urgent else QSystemTrayIcon.MessageIcon.Warning)
        self.tray.showMessage(
            tr("Glucose {level}: {value} {unit}", level=level.label.lower(),
               value=format_value(c.value_mgdl, st.unit), unit=st.unit),
            tr("Trend: {trend}. Confirm on your official reader or app.", trend=c.trend.label),
            icon, 15000,
        )

    # -- diálogos ---------------------------------------------------------------------
    @staticmethod
    def _present(dialog) -> None:
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def open_onboarding(self) -> None:
        dlg = OnboardingDialog(self.settings, self.palette)
        dlg.setWindowIcon(app_icon())
        dlg.finished_setup.connect(self._on_onboarded)
        dlg.language_changed.connect(self._on_onboarding_language)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self._present(dlg)

    def _on_onboarding_language(self, code: str) -> None:
        self.settings.language = code
        set_language(code)
        self._install_qt_translator()
        self.save()
        self._refresh_menu()
        self.widget.apply_style(self.settings, self.palette)
        self._show_setup_message()
        QTimer.singleShot(0, self.open_onboarding)

    def _on_onboarded(self, new: Settings, demo: bool) -> None:
        if demo:
            self.demo = "normal"
            self.rebuild_source()
            return
        self.apply_settings(new, force_reconnect=True)

    def open_settings(self, page: str = "") -> None:
        if self.settings_dialog and self.settings_dialog.isVisible():
            self._present(self.settings_dialog)
            return
        dlg = SettingsDialog(self.settings, self.palette, page)
        dlg.setWindowIcon(app_icon())
        password_before = get_secret(LIBRE_PASSWORD)

        def on_saved(new: Settings) -> None:
            reconnect = self.data is None or get_secret(LIBRE_PASSWORD) != password_before
            self.apply_settings(new, force_reconnect=reconnect)

        dlg.saved.connect(on_saved)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.settings_dialog = dlg
        self._present(dlg)

    def apply_settings(self, new: Settings, force_reconnect: bool = False) -> None:
        old = self.settings
        account_changed = force_reconnect or any(getattr(old, f) != getattr(new, f) for f in ACCOUNT_FIELDS)
        new.onboarded = True if (new.email or old.onboarded) else new.onboarded
        new.pos_x, new.pos_y = self.widget.x(), self.widget.y()
        language_changed = new.language != old.language
        if language_changed:
            set_language(new.language)
        self.settings = new
        self.save()
        if new.autostart != old.autostart:
            set_autostart(new.autostart)
        self.palette = palette_for(new.theme)
        self.widget.set_ai_enabled(new.ai_enabled)
        self.widget.apply_style(new, self.palette)
        if language_changed:
            self._install_qt_translator()
            self._refresh_menu()
        self._apply_theme_to_menu()
        self._configure_ai_timer()
        if self.analysis_dialog:
            self.analysis_dialog.close()
            self.analysis_dialog = None
        if account_changed:
            if new.email:
                self.demo = None
            self.rebuild_source()
        elif new.poll_seconds != old.poll_seconds and self.source:
            self._schedule(new.poll_seconds)
        if language_changed and not account_changed and self.widget.stack.currentIndex() == self.widget.PAGE_MESSAGE:
            self.rebuild_source()
        self._update_tray()
        self._sync_menu()

    # -- IA -----------------------------------------------------------------------------
    def _configure_ai_timer(self) -> None:
        self.ai_timer.stop()
        if self.settings.ai_enabled and self.settings.ai_auto_minutes > 0:
            self.ai_timer.start(self.settings.ai_auto_minutes * 60_000)

    def _ensure_analysis_dialog(self) -> None:
        if self.analysis_dialog is None:
            self.analysis_dialog = AnalysisDialog(self.palette)
            self.analysis_dialog.setWindowIcon(app_icon())
            self.analysis_dialog.rerun.connect(lambda: self.run_analysis(auto=False))

    def open_analysis(self) -> None:
        if not self.settings.ai_enabled:
            self.open_settings("AI")
            return
        self._ensure_analysis_dialog()
        self._present(self.analysis_dialog)
        self.run_analysis(auto=False)

    def run_analysis(self, auto: bool = False) -> None:
        st = self.settings
        info = PROVIDERS.get(st.ai_provider)
        if not info or self.analysis_running:
            return
        dialog = None if auto else self.analysis_dialog
        if not self.data or not self.data.history:
            if dialog:
                dialog.show_error(tr("There are no readings to analyze yet."))
            return
        window = metrics_mod.window(self.data.history, st.ai_hours)
        m = metrics_mod.compute(window, st.target_low, st.target_high)
        model = st.ai_model or info.default_model
        user_prompt = build_user_prompt(self.data, st.unit, st.target_low, st.target_high, st.ai_hours)
        key = get_secret(ai_key_name(st.ai_provider))
        system = system_prompt()
        if dialog:
            dialog.set_context(m, st.unit, st.ai_hours, info.name, model)
            dialog.show_loading()
        self.analysis_running = True

        def work():
            return analyze(st.ai_provider, key, model, system, user_prompt, base_url=st.ai_base_url)

        def done(text: str):
            self.analysis_running = False
            self.last_analysis = text
            if self.analysis_dialog:
                self.analysis_dialog.set_context(m, st.unit, st.ai_hours, info.name, model)
                self.analysis_dialog.show_result(text)
            if auto and self.tray and not (self.analysis_dialog and self.analysis_dialog.isVisible()):
                self.tray.showMessage(tr("New analysis available"), tr("Click to see the analysis of your readings."),
                                      QSystemTrayIcon.MessageIcon.Information, 10000)

        def fail(exc: Exception):
            self.analysis_running = False
            log.info("AI analysis failed: %s", exc)
            if self.analysis_dialog and not auto:
                self.analysis_dialog.show_error(str(exc))

        run_async(work, done, fail)


def _setup_platform_env() -> None:
    # No Wayland, janelas não podem se manter "sempre no topo" nem se posicionar;
    # XWayland (xcb) resolve, com fallback para wayland se o xcb não estiver disponível.
    if (sys.platform.startswith("linux") and os.environ.get("XDG_SESSION_TYPE") == "wayland"
            and "QT_QPA_PLATFORM" not in os.environ):
        os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"


def main() -> None:
    parser = argparse.ArgumentParser(prog=APP_ID, description="FreeStyle Libre glucose on your desktop.")
    parser.add_argument("--demo", nargs="?", const="normal", choices=DemoSource.SCENARIOS,
                        help="use demo data (no account needed)")
    parser.add_argument("--onboarding", action="store_true", help="show the setup assistant again")
    parser.add_argument("--debug", action="store_true", help="verbose logging")
    parser.add_argument("--screenshot", metavar="PNG", help=argparse.SUPPRESS)  # captura para revisão de design
    parser.add_argument("--theme", choices=("system", "dark", "light"), help=argparse.SUPPRESS)
    parser.add_argument("--lang", choices=("en", "pt"), help=argparse.SUPPRESS)
    parser.add_argument("--selftest", metavar="REPORT", help=argparse.SUPPRESS)  # verificação do build
    parser.add_argument("--compact", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    # executável "windowed" (PyInstaller) não tem stdout/stderr: evita falhas ao imprimir/logar
    for stream in ("stdout", "stderr"):
        if getattr(sys, stream) is None:
            setattr(sys, stream, open(os.devnull, "w"))

    if args.selftest:
        from glucowidget.selftest import run

        sys.exit(run(args.selftest))

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    _setup_platform_env()
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setDesktopFileName(APP_ID)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())
    load_fonts()

    settings = Settings.load()
    persist = not args.screenshot
    if args.onboarding:
        settings.onboarded = False
    if args.screenshot:
        settings = Settings(onboarded=True, pos_x=40, pos_y=40)
        settings.theme = args.theme or "dark"
        settings.language = args.lang or "en"
        settings.compact = args.compact
    controller = Controller(settings, demo=args.demo, persist=persist)

    if args.screenshot:
        def snap():
            controller.widget.grab().save(args.screenshot)
            app.quit()
        QTimer.singleShot(1800, snap)

    app.aboutToQuit.connect(lambda: controller.save())

    # Ctrl+C / SIGTERM: o Python só trata sinais quando executa bytecode, então um timer
    # ocioso devolve o controle ao interpretador para o encerramento ser imediato.
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: app.quit())
    wake = QTimer()
    wake.start(200)
    wake.timeout.connect(lambda: None)

    sys.exit(app.exec())
