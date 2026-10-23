"""Montagem do prompt de análise a partir das leituras."""
from __future__ import annotations

from datetime import datetime, timezone

from glucowidget import metrics
from glucowidget.i18n import tr
from glucowidget.libre.models import GlucoseData, GlucoseReading
from glucowidget.units import MMOL, convert, format_value

MAX_POINTS = 160


def system_prompt() -> str:
    return tr(
        "You help people with diabetes understand continuous glucose monitoring (CGM) data. Answer "
        "in English, in concise Markdown, in plain language and a warm, objective tone, in under "
        "about 200 words. Use only the data provided: never invent causes (meals, exercise, insulin, "
        "illness) or facts that are not in the data, and do not predict beyond the next 30 minutes "
        "or so. If the data is sparse, outdated or has gaps, say so first. Do not repeat the summary "
        "numbers the app already shows (mean, time in range, variation, min and max); add "
        "interpretation instead, citing specific times and values. Use the sections: **Summary**, "
        "**Patterns**, **Current trend** and **Points of attention**. If the latest reading is below "
        "the very-low threshold or above the very-high threshold, start with a one-line alert. Never "
        "prescribe or suggest insulin or medication doses or changes; for anything clinical, point to "
        "the person's care team. End with one short line reminding that this does not replace "
        "medical advice."
    )


def _fmt(value_mgdl: float, unit: str) -> str:
    # no prompt os decimais sempre usam ponto, independentemente do idioma
    return format_value(value_mgdl, unit).replace(",", ".")


def _downsample(readings: list[GlucoseReading], limit: int) -> list[GlucoseReading]:
    """Reduz a lista sem perder os extremos (uma queda breve não pode sumir)."""
    if len(readings) <= limit:
        return readings
    step = len(readings) / limit
    keep = {int(i * step) for i in range(limit)} | {0, len(readings) - 1}
    keep.add(min(range(len(readings)), key=lambda i: readings[i].value_mgdl))
    keep.add(max(range(len(readings)), key=lambda i: readings[i].value_mgdl))
    return [readings[i] for i in sorted(keep)]


def build_user_prompt(data: GlucoseData, unit: str, low: float, high: float, hours: int,
                      now: datetime | None = None, *, urgent_low: float = 54, urgent_high: float = 250,
                      stale_minutes: int = 15) -> str:
    now = now or datetime.now(timezone.utc)
    window = metrics.window(data.history, hours, now)
    m = metrics.compute(window, low, high, urgent_low, urgent_high)  # métricas sobre todas as leituras
    sampled = _downsample(window, MAX_POINTS)

    lines = [
        tr("Unit: {unit}. Target range: {low}–{high} {unit}. Urgent thresholds: below {urgent_low} and "
           "above {urgent_high} {unit}.",
           unit=unit, low=_fmt(low, unit), high=_fmt(high, unit),
           urgent_low=_fmt(urgent_low, unit), urgent_high=_fmt(urgent_high, unit)),
        tr("Current time: {time}.", time=f"{now.astimezone():%d/%m %H:%M}"),
    ]
    if data.current:
        age = data.current.age_minutes(now)
        lines.append(
            tr("Latest reading: {value} {unit} at {time} ({age} min ago), trend {trend}.",
               value=_fmt(data.current.value_mgdl, unit), unit=unit,
               time=f"{data.current.timestamp.astimezone():%H:%M}", age=round(age),
               trend=data.current.trend.label)
        )
        if age > stale_minutes:
            lines.append(tr("Warning: the latest reading is more than {minutes} minutes old and may not "
                            "reflect the current glucose.", minutes=stale_minutes))

    if window:
        span = metrics.coverage_hours(window)
        lines.append(
            tr("Data covers {start} to {end} ({span} h, {count} readings).",
               start=f"{window[0].timestamp.astimezone():%d/%m %H:%M}",
               end=f"{window[-1].timestamp.astimezone():%d/%m %H:%M}",
               span=f"{span:.1f}", count=len(window))
        )
        if span < hours - 0.75:
            lines.append(tr("Only {span} h of data are available, less than the {hours} h requested.",
                            span=f"{span:.1f}", hours=hours))
        gaps = metrics.find_gaps(window)
        if gaps:
            start, minutes = max(gaps, key=lambda g: g[1])
            lines.append(tr("Data gaps: {n} (longest {minutes} min, starting {time}).",
                            n=len(gaps), minutes=round(minutes), time=f"{start.astimezone():%H:%M}"))
        else:
            lines.append(tr("No data gaps."))
    else:
        lines.append(tr("There are no readings in the requested period."))

    if m:
        lines.append(
            tr("Time in ranges: very low {vl}%; low {l}%; in range {tir}%; high {h}%; very high {vh}%.",
               vl=f"{m.very_low:.0f}", l=f"{m.tbr - m.very_low:.0f}", tir=f"{m.tir:.0f}",
               h=f"{m.tar - m.very_high:.0f}", vh=f"{m.very_high:.0f}")
        )
        lines.append(
            tr("Period metrics: mean {mean} {unit}; SD {sd} {unit}; CV {cv}%; min {min} {unit}; "
               "max {max} {unit}.",
               mean=_fmt(m.mean, unit), sd=_fmt(m.sd, unit), cv=f"{m.cv:.0f}",
               min=_fmt(m.min, unit), max=_fmt(m.max, unit), unit=unit)
        )
    lines.append("")
    lines.append(tr("Readings (local time, value):"))
    for r in sampled:
        v = convert(r.value_mgdl, unit)
        lines.append(f"{r.timestamp.astimezone():%d/%m %H:%M},{v:.1f}" if unit == MMOL
                     else f"{r.timestamp.astimezone():%d/%m %H:%M},{round(v)}")
    lines.append("")
    lines.append(tr("Analyze this data."))
    return "\n".join(lines)
