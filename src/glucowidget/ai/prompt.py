"""Montagem do prompt de análise a partir das leituras."""
from __future__ import annotations

from datetime import datetime

from glucowidget import metrics
from glucowidget.i18n import tr
from glucowidget.libre.models import GlucoseData
from glucowidget.units import MMOL, convert, format_value

MAX_POINTS = 160


def system_prompt() -> str:
    return tr(
        "You are an assistant that helps people with diabetes understand continuous glucose "
        "monitoring (CGM) data. Always answer in English, in concise Markdown, with a warm and "
        "objective tone. Use the sections: **Summary**, **Observed patterns**, **Current trend**, "
        "**Points of attention** and **General suggestions**. Be specific, citing times and values. "
        "Never prescribe insulin or medication doses. If there is immediate risk (severe "
        "hypoglycemia or persistently very high hyperglycemia), highlight it at the start. End "
        "with a short line reminding that the analysis does not replace medical advice."
    )


def _fmt(value_mgdl: float, unit: str) -> str:
    # no prompt os decimais sempre usam ponto, independentemente do idioma
    return format_value(value_mgdl, unit).replace(",", ".")


def build_user_prompt(data: GlucoseData, unit: str, low: float, high: float, hours: int,
                      now: datetime | None = None) -> str:
    readings = metrics.window(data.history, hours, now)
    if len(readings) > MAX_POINTS:
        step = len(readings) / MAX_POINTS
        readings = [readings[int(i * step)] for i in range(MAX_POINTS)] + [readings[-1]]

    m = metrics.compute(readings, low, high)
    lines = [
        tr("Unit: {unit}. Target range: {low}–{high} {unit}.", unit=unit, low=_fmt(low, unit), high=_fmt(high, unit)),
        tr("Period analyzed: last {hours} h ({count} readings).", hours=hours, count=len(readings)),
    ]
    if data.current:
        local = data.current.timestamp.astimezone()
        lines.append(
            tr("Current reading: {value} {unit} at {time}, trend {trend}.",
               value=_fmt(data.current.value_mgdl, unit), unit=unit, time=f"{local:%H:%M}",
               trend=data.current.trend.label)
        )
    if m:
        lines.append(
            tr("Period metrics: mean {mean} {unit}; SD {sd} {unit}; CV {cv}%; time in range {tir}%; "
               "below {tbr}%; above {tar}%; min {min} {unit}; max {max} {unit}; estimated GMI {gmi}%.",
               mean=_fmt(m.mean, unit), sd=_fmt(m.sd, unit), cv=f"{m.cv:.0f}", tir=f"{m.tir:.0f}",
               tbr=f"{m.tbr:.0f}", tar=f"{m.tar:.0f}", min=_fmt(m.min, unit), max=_fmt(m.max, unit),
               unit=unit, gmi=f"{m.gmi:.1f}")
        )
    lines.append("")
    lines.append(tr("Readings (local time, value):"))
    for r in readings:
        v = convert(r.value_mgdl, unit)
        lines.append(f"{r.timestamp.astimezone():%d/%m %H:%M},{v:.1f}" if unit == MMOL
                     else f"{r.timestamp.astimezone():%d/%m %H:%M},{round(v)}")
    lines.append("")
    lines.append(tr("Analyze this data."))
    return "\n".join(lines)
