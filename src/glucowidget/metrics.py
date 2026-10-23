"""Métricas locais calculadas sem IA (consenso internacional de CGM)."""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from glucowidget.libre.models import GlucoseReading


@dataclass(frozen=True)
class Metrics:
    count: int
    mean: float
    sd: float
    cv: float  # %
    tir: float  # % no alvo
    tbr: float  # % abaixo do alvo (inclui muito baixo)
    tar: float  # % acima do alvo (inclui muito alto)
    very_low: float  # % abaixo do limite de urgência baixo
    very_high: float  # % acima do limite de urgência alto
    gmi: float  # % (Glucose Management Indicator; só é representativo com ~14 dias de dados)
    min: float
    max: float


def window(readings: list[GlucoseReading], hours: float, now: datetime | None = None) -> list[GlucoseReading]:
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    return [r for r in readings if r.timestamp >= start]


def coverage_hours(readings: list[GlucoseReading]) -> float:
    """Horas efetivamente cobertas (da primeira à última leitura)."""
    if len(readings) < 2:
        return 0.0
    return (readings[-1].timestamp - readings[0].timestamp).total_seconds() / 3600


def find_gaps(readings: list[GlucoseReading], min_minutes: float | None = None) -> list[tuple[datetime, float]]:
    """Intervalos sem leituras bem acima do normal: (início, duração em minutos).

    Sem ``min_minutes``, o limite é 2,5x o intervalo típico (mínimo de 20 min).
    """
    if len(readings) < 3:
        return []
    diffs = [(b.timestamp - a.timestamp).total_seconds() / 60 for a, b in zip(readings, readings[1:])]
    threshold = min_minutes if min_minutes is not None else max(20.0, statistics.median(diffs) * 2.5)
    return [(a.timestamp, d) for a, d in zip(readings, diffs) if d > threshold]


def compute(readings: list[GlucoseReading], low: float, high: float,
            urgent_low: float = 54, urgent_high: float = 250) -> Metrics | None:
    values = [r.value_mgdl for r in readings]
    if not values:
        return None
    n = len(values)
    mean = statistics.fmean(values)
    sd = statistics.pstdev(values) if n > 1 else 0.0
    return Metrics(
        count=n,
        mean=mean,
        sd=sd,
        cv=(sd / mean * 100) if mean else 0.0,
        tir=sum(low <= v <= high for v in values) / n * 100,
        tbr=sum(v < low for v in values) / n * 100,
        tar=sum(v > high for v in values) / n * 100,
        very_low=sum(v < urgent_low for v in values) / n * 100,
        very_high=sum(v > urgent_high for v in values) / n * 100,
        gmi=3.31 + 0.02392 * mean,
        min=min(values),
        max=max(values),
    )
