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
    tbr: float  # % abaixo
    tar: float  # % acima
    gmi: float  # % (Glucose Management Indicator)
    min: float
    max: float


def window(readings: list[GlucoseReading], hours: float, now: datetime | None = None) -> list[GlucoseReading]:
    now = now or datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    return [r for r in readings if r.timestamp >= start]


def compute(readings: list[GlucoseReading], low: float, high: float) -> Metrics | None:
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
        gmi=3.31 + 0.02392 * mean,
        min=min(values),
        max=max(values),
    )
