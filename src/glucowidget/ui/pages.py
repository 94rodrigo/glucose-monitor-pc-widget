"""Páginas de configuração, reutilizadas no diálogo de configurações e no onboarding."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from glucowidget import __version__
from glucowidget.i18n import LANGUAGES, N_, decimal, tr
from glucowidget.ai.providers import PROVIDERS
from glucowidget.config import LIBRE_PASSWORD, Settings, ai_key_name, get_secret, set_secret
from glucowidget.libre.client import LibreLinkUpClient
from glucowidget.sources import classify_error
from glucowidget.ui.async_utils import run_async
from glucowidget.ui.components import SegmentedControl, Spinner, Toggle, card
from glucowidget.ui.theme import Palette, ui_font
from glucowidget.units import MGDL, MMOL, convert, to_mgdl

REGIONS = [("", N_("Automatic")), ("us", N_("USA")), ("eu", N_("Europe")), ("eu2", N_("Europe 2")),
           ("de", N_("Germany")), ("fr", N_("France")), ("jp", N_("Japan")), ("ap", N_("Asia-Pacific")),
           ("au", N_("Australia")), ("ae", N_("United Arab Emirates")), ("ca", N_("Canada")),
           ("la", N_("Latin America"))]


class Page(QWidget):
    title = ""
    subtitle = ""

    def __init__(self, palette: Palette, parent=None):
        super().__init__(parent)
        self.pal = palette
        self.setObjectName("page")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(28, 24, 28, 24)
        self.layout_.setSpacing(14)
        h1 = QLabel(tr(self.title))
        h1.setObjectName("h1")
        self.layout_.addWidget(h1)
        if self.subtitle:
            sub = QLabel(tr(self.subtitle))
            sub.setObjectName("muted")
            sub.setWordWrap(True)
            self.layout_.addWidget(sub)
        self.layout_.addSpacing(4)

    def add_card(self, heading: str = "", hint: str = "") -> QFormLayout:
        c = card()
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 16, 18, 16)
        v.setSpacing(10)
        if heading:
            h = QLabel(heading)
            h.setObjectName("h2")
            v.addWidget(h)
        if hint:
            t = QLabel(hint)
            t.setObjectName("subtle")
            t.setWordWrap(True)
            t.setOpenExternalLinks(True)
            v.addWidget(t)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        v.addLayout(form)
        self.layout_.addWidget(c)
        return form

    def finish(self):
        self.layout_.addStretch(1)
        for t in self.findChildren(Toggle):
            t.track_on, t.track_off = self.pal.accent, self.pal.surface_hover.darker(115) if self.pal.name == "light" else self.pal.surface_hover.lighter(140)
        for sp in self.findChildren(QAbstractSpinBox):  # padding do QSS não chega ao QLineEdit interno
            sp.lineEdit().setTextMargins(8, 0, 0, 0)

    def load(self, s: Settings) -> None: ...

    def apply(self, s: Settings) -> list[str]:
        return []


def password_field(placeholder: str = "") -> tuple[QWidget, QLineEdit]:
    box = QWidget()
    h = QHBoxLayout(box)
    h.setContentsMargins(0, 0, 0, 0)
    h.setSpacing(6)
    edit = QLineEdit()
    edit.setEchoMode(QLineEdit.EchoMode.Password)
    edit.setPlaceholderText(placeholder)
    toggle = QPushButton(tr("Show"))
    toggle.setObjectName("ghost")
    toggle.setCheckable(True)
    toggle.setCursor(Qt.CursorShape.PointingHandCursor)

    def flip(on: bool):
        edit.setEchoMode(QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password)
        toggle.setText(tr("Hide") if on else tr("Show"))

    toggle.toggled.connect(flip)
    h.addWidget(edit, 1)
    h.addWidget(toggle)
    return box, edit


def mark_invalid(edit: QWidget, invalid: bool) -> None:
    edit.setProperty("invalid", invalid)
    edit.style().unpolish(edit)
    edit.style().polish(edit)


# ---------------------------------------------------------------------------
class AccountPage(Page):
    title = N_("LibreLinkUp account")
    subtitle = N_("Use a LibreLinkUp (follower) app account. The patient must invite this email "
                  "in the LibreLink app under Share → Connect LibreLinkUp app.")

    def __init__(self, palette, parent=None):
        super().__init__(palette, parent)
        form = self.add_card(tr("Login"), tr("Your password is stored in the system password vault."))
        self.email = QLineEdit()
        self.email.setPlaceholderText(tr("you@email.com"))
        pw_box, self.password = password_field(tr("LibreLinkUp password"))
        form.addRow(tr("Email"), self.email)
        form.addRow(tr("Password"), pw_box)

        row = QHBoxLayout()
        self.test_btn = QPushButton(tr("Test connection"))
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.clicked.connect(self.test_connection)
        self.spinner = Spinner(18)
        self.spinner.set_color(palette.accent)
        self.spinner.hide()
        self.status = QLabel()
        self.status.setWordWrap(True)
        row.addWidget(self.test_btn)
        row.addWidget(self.spinner)
        row.addWidget(self.status, 1)
        form.addRow(row)

        form2 = self.add_card(tr("Patient and refresh"))
        self.patient = QComboBox()
        self.patient.addItem(tr("First patient on the account"), "")
        form2.addRow(tr("Patient"), self.patient)
        self.region = QComboBox()
        for code, name in REGIONS:
            self.region.addItem(tr(name), code)
        form2.addRow(tr("Region"), self.region)
        self.poll = QSpinBox()
        self.poll.setRange(30, 900)
        self.poll.setSingleStep(15)
        self.poll.setSuffix(" s")
        form2.addRow(tr("Refresh every"), self.poll)
        self.version = QLineEdit()
        self.version.setToolTip(tr("App version reported to the API. Increase it if login starts failing after updates."))
        form2.addRow(tr("API version"), self.version)
        self.finish()

    def load(self, s: Settings) -> None:
        self.email.setText(s.email)
        self.password.setText(get_secret(LIBRE_PASSWORD) if s.email else "")
        idx = self.region.findData(s.region)
        self.region.setCurrentIndex(max(0, idx))
        if s.patient_id and self.patient.findData(s.patient_id) < 0:
            self.patient.addItem(tr("Saved patient ({id}…)", id=s.patient_id[:8]), s.patient_id)
        self.patient.setCurrentIndex(max(0, self.patient.findData(s.patient_id)))
        self.poll.setValue(s.poll_seconds)
        self.version.setText(s.api_version)

    def validate(self) -> list[str]:
        errors = []
        ok_email = "@" in self.email.text()
        mark_invalid(self.email, not ok_email)
        if not ok_email:
            errors.append(tr("Enter a valid email."))
        ok_pw = bool(self.password.text())
        mark_invalid(self.password, not ok_pw)
        if not ok_pw:
            errors.append(tr("Enter the password."))
        return errors

    def apply(self, s: Settings) -> list[str]:
        errors = self.validate() if (self.email.text() or self.password.text()) else []
        if errors:
            return errors
        if s.email != self.email.text().strip():
            s.patient_id = ""
        s.email = self.email.text().strip()
        set_secret(LIBRE_PASSWORD, self.password.text())
        s.region = self.region.currentData() or ""
        s.patient_id = self.patient.currentData() or ""
        s.poll_seconds = self.poll.value()
        s.api_version = self.version.text().strip() or "4.16.0"
        return []

    def _set_status(self, text: str, kind: str) -> None:
        self.status.setObjectName(kind)
        self.status.setText(text)
        self.status.style().unpolish(self.status)
        self.status.style().polish(self.status)

    def test_connection(self) -> None:
        if self.validate():
            self._set_status(tr("Fill in email and password."), "err")
            return
        email, pw = self.email.text().strip(), self.password.text()
        region, version = self.region.currentData() or None, self.version.text().strip() or "4.16.0"
        self.test_btn.setEnabled(False)
        self.spinner.start()
        self._set_status(tr("Connecting…"), "muted")

        def work():
            client = LibreLinkUpClient(email, pw, region=region, version=version)
            try:
                patients = client.connections()
                return client.region, patients
            finally:
                client.close()

        def done(result):
            region_found, patients = result
            self.spinner.stop()
            self.test_btn.setEnabled(True)
            if region_found:
                i = self.region.findData(region_found)
                if i >= 0:
                    self.region.setCurrentIndex(i)
            current = self.patient.currentData()
            self.patient.clear()
            for p in patients:
                self.patient.addItem(p.name, p.id)
            if not patients:
                self.patient.addItem(tr("First patient on the account"), "")
                self._set_status(tr("Login OK, but this account is not following any patient yet."), "err")
                return
            self.patient.setCurrentIndex(max(0, self.patient.findData(current)))
            n = len(patients)
            text = tr("✓ Connected · {n} patients found", n=n) if n > 1 else tr("✓ Connected · 1 patient found")
            self._set_status(text, "ok")

        def fail(exc):
            self.spinner.stop()
            self.test_btn.setEnabled(True)
            kind = classify_error(exc)
            msg = str(exc) if kind != "network" else tr("No connection to LibreLinkUp. Check your internet.")
            self._set_status(msg, "err")

        run_async(work, done, fail)


# ---------------------------------------------------------------------------
class RangeBar(QWidget):
    """Prévia visual das faixas configuradas."""

    def __init__(self, palette: Palette, parent=None):
        super().__init__(parent)
        self.pal = palette
        self.values = (54, 70, 180, 250)
        self.unit = MGDL
        self.setMinimumHeight(44)

    def set_values(self, ulow, low, high, uhigh, unit):
        self.values, self.unit = (ulow, low, high, uhigh), unit
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        lo_v, hi_v = 40, 300
        ulow, low, high, uhigh = self.values
        w = self.width()
        bar_y, bar_h = 6, 10

        def x(v):
            return max(0, min(w, (v - lo_v) / (hi_v - lo_v) * w))

        segs = [(lo_v, ulow, self.pal.low, 255), (ulow, low, self.pal.low, 140),
                (low, high, self.pal.in_range, 255), (high, uhigh, self.pal.high, 140),
                (uhigh, hi_v, self.pal.high, 255)]
        p.setPen(Qt.PenStyle.NoPen)
        for a, b, color, alpha in segs:
            c = QColor(color)
            c.setAlpha(alpha)
            p.setBrush(c)
            p.drawRect(QRectF(x(a), bar_y, x(b) - x(a), bar_h))
        p.setFont(ui_font(11))
        p.setPen(self.pal.text_muted)
        for v in self.values:
            label = decimal(f"{convert(v, self.unit):.1f}") if self.unit == MMOL else str(round(v))
            p.drawText(QRectF(x(v) - 30, bar_y + bar_h + 4, 60, 18), Qt.AlignmentFlag.AlignHCenter, label)
        p.end()


class RangePage(Page):
    title = N_("Glucose")
    subtitle = N_("Unit and ranges used for colors, alerts and analyses.")

    def __init__(self, palette, parent=None):
        super().__init__(palette, parent)
        form = self.add_card(tr("Unit"))
        self.unit = SegmentedControl([(MGDL, "mg/dL"), (MMOL, "mmol/L")])
        self.unit.changed.connect(self._unit_changed)
        form.addRow(self.unit)

        form2 = self.add_card(tr("Ranges"), tr("International consensus default: target 70–180 mg/dL; urgent below 54 and above 250."))
        self.spins = {}
        for key, label in (("target_low", N_("Target — minimum")), ("target_high", N_("Target — maximum")),
                           ("urgent_low", N_("Very low below")), ("urgent_high", N_("Very high above"))):
            sp = QDoubleSpinBox()
            sp.valueChanged.connect(self._refresh_bar)
            self.spins[key] = sp
            form2.addRow(tr(label), sp)
        self.bar = RangeBar(palette)
        form2.addRow(self.bar)
        self.stale = QSpinBox()
        self.stale.setRange(5, 120)
        self.stale.setSuffix(" min")
        form2.addRow(tr("Consider outdated after"), self.stale)
        self.error = QLabel()
        self.error.setObjectName("err")
        self.error.hide()
        self.layout_.addWidget(self.error)
        self.finish()
        self._unit = MGDL

    def _configure_spins(self, unit: str):
        for sp in self.spins.values():
            sp.blockSignals(True)
            if unit == MMOL:
                sp.setDecimals(1)
                sp.setRange(1.5, 25.0)
                sp.setSingleStep(0.1)
            else:
                sp.setDecimals(0)
                sp.setRange(30, 450)
                sp.setSingleStep(5)
            sp.setSuffix(f" {unit}")
            sp.blockSignals(False)

    def _values_mgdl(self) -> dict[str, float]:
        return {k: to_mgdl(sp.value(), self._unit) for k, sp in self.spins.items()}

    def _set_values_mgdl(self, values: dict[str, float]):
        for k, v in values.items():
            self.spins[k].blockSignals(True)
            self.spins[k].setValue(round(convert(v, self._unit), 1 if self._unit == MMOL else 0))
            self.spins[k].blockSignals(False)
        self._refresh_bar()

    def _unit_changed(self, unit: str):
        values = self._values_mgdl()
        self._unit = unit
        self._configure_spins(unit)
        self._set_values_mgdl(values)

    def _refresh_bar(self, *_):
        v = self._values_mgdl()
        self.bar.set_values(v["urgent_low"], v["target_low"], v["target_high"], v["urgent_high"], self._unit)

    def load(self, s: Settings) -> None:
        self._unit = s.unit
        self.unit.set_value(s.unit)
        self._configure_spins(s.unit)
        self._set_values_mgdl({k: getattr(s, k) for k in self.spins})
        self.stale.setValue(s.stale_minutes)

    def apply(self, s: Settings) -> list[str]:
        v = self._values_mgdl()
        if not (v["urgent_low"] < v["target_low"] < v["target_high"] < v["urgent_high"]):
            self.error.setText(tr("Ranges must be in order: very low < target min < target max < very high."))
            self.error.show()
            return [tr("Invalid ranges.")]
        self.error.hide()
        s.unit = self._unit
        for k, val in v.items():
            setattr(s, k, round(val, 1))
        s.stale_minutes = self.stale.value()
        return []


# ---------------------------------------------------------------------------
class AppearancePage(Page):
    title = N_("Appearance")
    subtitle = N_("Adjust the widget to your screen and taste.")

    def __init__(self, palette, parent=None):
        super().__init__(palette, parent)
        form0 = self.add_card(tr("Language"))
        self.language = SegmentedControl(list(LANGUAGES))
        form0.addRow(self.language)

        form = self.add_card(tr("Theme and size"))
        self.theme = SegmentedControl([("system", tr("System")), ("dark", tr("Dark")), ("light", tr("Light"))])
        form.addRow(tr("Theme"), self.theme)
        self.scale, scale_row = self._slider(80, 150, 10, "%")
        form.addRow(tr("Size"), scale_row)
        self.opacity, op_row = self._slider(50, 100, 5, "%")
        form.addRow(tr("Opacity"), op_row)
        self.chart = SegmentedControl([("3", "3 h"), ("6", "6 h"), ("12", "12 h")])
        form.addRow(tr("Chart"), self.chart)

        form2 = self.add_card(tr("Behavior"))
        self.on_top = Toggle(tr("Keep above other windows"))
        self.hide_taskbar = Toggle(tr("Hide from the taskbar"))
        self.reduce_motion = Toggle(tr("Reduce animations"))
        self.autostart = Toggle(tr("Start with the system"))
        for cb in (self.on_top, self.hide_taskbar, self.reduce_motion, self.autostart):
            form2.addRow(cb)
        self.finish()

    @staticmethod
    def _slider(lo, hi, step, suffix):
        row = QWidget()
        h = QHBoxLayout(row)
        h.setContentsMargins(0, 0, 0, 0)
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setSingleStep(step)
        sl.setPageStep(step)
        lbl = QLabel()
        lbl.setMinimumWidth(44)
        lbl.setObjectName("muted")
        sl.valueChanged.connect(lambda v: lbl.setText(f"{v}{suffix}"))
        h.addWidget(sl, 1)
        h.addWidget(lbl)
        return sl, row

    def load(self, s: Settings) -> None:
        self.language.set_value(s.language)
        self.theme.set_value(s.theme)
        self.scale.setValue(round(s.scale * 100))
        self.opacity.setValue(round(s.opacity * 100))
        self.chart.set_value(str(s.chart_hours))
        self.on_top.setChecked(s.always_on_top)
        self.hide_taskbar.setChecked(s.hide_from_taskbar)
        self.reduce_motion.setChecked(s.reduce_motion)
        self.autostart.setChecked(s.autostart)

    def apply(self, s: Settings) -> list[str]:
        s.language = self.language.value()
        s.theme = self.theme.value()
        s.scale = round(self.scale.value() / 10) / 10
        s.opacity = self.opacity.value() / 100
        s.chart_hours = int(self.chart.value())
        s.always_on_top = self.on_top.isChecked()
        s.hide_from_taskbar = self.hide_taskbar.isChecked()
        s.reduce_motion = self.reduce_motion.isChecked()
        s.autostart = self.autostart.isChecked()
        return []


# ---------------------------------------------------------------------------
class AlertsPage(Page):
    title = N_("Alerts")
    subtitle = N_("System notifications when glucose leaves the range.")

    def __init__(self, palette, parent=None):
        super().__init__(palette, parent)
        form = self.add_card("", tr("The widget does not replace the alarms of your sensor or the LibreLink app."))
        self.enabled = Toggle(tr("Notify when leaving the target range"))
        self.urgent_only = Toggle(tr("Only very low or very high values"))
        self.enabled.toggled.connect(self.urgent_only.setEnabled)
        form.addRow(self.enabled)
        form.addRow(self.urgent_only)
        self.finish()

    def load(self, s: Settings) -> None:
        self.enabled.setChecked(s.notify_enabled)
        self.urgent_only.setChecked(s.notify_urgent_only)
        self.urgent_only.setEnabled(s.notify_enabled)

    def apply(self, s: Settings) -> list[str]:
        s.notify_enabled = self.enabled.isChecked()
        s.notify_urgent_only = self.urgent_only.isChecked()
        return []


# ---------------------------------------------------------------------------
class AIPage(Page):
    title = N_("AI analysis")
    subtitle = N_("Optional. Use your own API key to get analyses of your readings. "
                  "Data is only sent to the provider when you request an analysis.")

    def __init__(self, palette, parent=None):
        super().__init__(palette, parent)
        form = self.add_card(tr("Provider"))
        self.provider = QComboBox()
        self.provider.addItem(tr("Disabled"), "")
        for p in PROVIDERS.values():
            self.provider.addItem(tr(p.name), p.id)
        self.provider.currentIndexChanged.connect(self._provider_changed)
        form.addRow(tr("Provider"), self.provider)
        self.model = QComboBox()
        self.model.setEditable(True)
        form.addRow(tr("Model"), self.model)
        key_box, self.key = password_field(tr("Paste your API key"))
        self.key_row_label = QLabel(tr("API key"))
        form.addRow(self.key_row_label, key_box)
        self.key_link = QLabel()
        self.key_link.setObjectName("subtle")
        self.key_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.key_link.linkActivated.connect(lambda url: QDesktopServices.openUrl(QUrl(url)))
        form.addRow("", self.key_link)
        self.base_url = QLineEdit()
        form.addRow(tr("Base URL"), self.base_url)

        form2 = self.add_card(tr("Analysis"))
        self.hours = SegmentedControl([("3", "3 h"), ("6", "6 h"), ("12", "12 h"), ("24", "24 h")])
        form2.addRow(tr("Period"), self.hours)
        self.auto = QComboBox()
        for minutes, label in ((0, N_("Only when I ask")), (60, N_("Every 1 hour")),
                               (180, N_("Every 3 hours")), (360, N_("Every 6 hours"))):
            self.auto.addItem(tr(label), minutes)
        form2.addRow(tr("Automatic"), self.auto)
        self._keys: dict[str, str] = {}
        self._current = ""
        self.finish()

    def _remember_key(self):
        if self._current:
            self._keys[self._current] = self.key.text()

    def _provider_changed(self, *_):
        self._remember_key()
        pid = self.provider.currentData() or ""
        self._current = pid
        info = PROVIDERS.get(pid)
        enabled = info is not None
        for w in (self.model, self.key, self.base_url, self.hours, self.auto):
            w.setEnabled(enabled)
        self.model.clear()
        if info:
            for m in info.models or ((info.default_model,) if info.default_model else ()):
                self.model.addItem(m)
            self.model.setCurrentText(info.default_model)
            self.base_url.setPlaceholderText(info.base_url or tr("https://your-server/v1"))
            if pid not in self._keys:
                self._keys[pid] = get_secret(ai_key_name(pid))
            self.key.setText(self._keys[pid])
            self.key.setPlaceholderText(tr("Paste your API key") if info.needs_key else tr("Optional for this provider"))
            self.key_link.setText(f'<a style="color:{self.pal.accent.name()}; text-decoration:none" href="{info.key_url}">{tr("Get a key at {name} ↗", name=tr(info.name))}</a>' if info.key_url else "")
        else:
            self.key.clear()
            self.key_link.clear()

    def load(self, s: Settings) -> None:
        self.provider.setCurrentIndex(max(0, self.provider.findData(s.ai_provider)))
        self._provider_changed()
        if s.ai_model:
            self.model.setCurrentText(s.ai_model)
        self.base_url.setText(s.ai_base_url)
        self.hours.set_value(str(s.ai_hours))
        self.auto.setCurrentIndex(max(0, self.auto.findData(s.ai_auto_minutes)))

    def apply(self, s: Settings) -> list[str]:
        self._remember_key()
        pid = self.provider.currentData() or ""
        info = PROVIDERS.get(pid)
        if info:
            missing_key = info.needs_key and not self.key.text().strip()
            mark_invalid(self.key, missing_key)
            if missing_key:
                return [tr("Enter the AI provider's API key.")]
            if pid == "custom" and not self.base_url.text().strip():
                mark_invalid(self.base_url, True)
                return [tr("Enter the provider's base URL.")]
        if s.ai_provider != pid:
            s.ai_base_url = ""
        s.ai_provider = pid
        s.ai_model = self.model.currentText().strip() if info else ""
        s.ai_base_url = self.base_url.text().strip()
        s.ai_hours = int(self.hours.value())
        s.ai_auto_minutes = self.auto.currentData() or 0
        for provider, key in self._keys.items():
            if provider:
                set_secret(ai_key_name(provider), key.strip())
        return []


# ---------------------------------------------------------------------------
class AboutPage(Page):
    title = N_("About")

    def __init__(self, palette, parent=None):
        super().__init__(palette, parent)
        form = self.add_card(f"GlucoWidget {__version__}")
        text = QLabel(
            tr(
                "Open-source widget that shows FreeStyle Libre glucose using the unofficial "
                "LibreLinkUp API. Not affiliated with Abbott.<br><br>"
                "<b>Notice:</b> this application is not a medical device. Do not make treatment "
                "decisions based on it alone — always confirm on your official reader/app and "
                "talk to your healthcare team."
            )
        )
        text.setWordWrap(True)
        text.setObjectName("muted")
        text.setTextFormat(Qt.TextFormat.RichText)
        form.addRow(text)
        self.finish()


class StepDots(QWidget):
    """Indicador de etapas do onboarding."""

    def __init__(self, count: int, palette: Palette, parent=None):
        super().__init__(parent)
        self.count, self.index, self.pal = count, 0, palette
        self.setFixedHeight(10)
        self.setMinimumWidth(count * 30)

    def set_index(self, i: int):
        self.index = i
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        x = 0.0
        for i in range(self.count):
            w = 26 if i == self.index else 8
            color = self.pal.accent if i <= self.index else self.pal.border
            p.setBrush(color)
            p.drawRoundedRect(QRectF(x, 1, w, 8), 4, 4)
            x += w + 6
        p.end()
