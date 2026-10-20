"""Classificação da leitura em níveis (independente da UI)."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from glucowidget.libre.models import GlucoseReading


class Level(Enum):
    NONE = "none"
    URGENT_LOW = "urgent_low"
    LOW = "low"
    IN_RANGE = "in_range"
    HIGH = "high"
    URGENT_HIGH = "urgent_high"
    STALE = "stale"

    @property
    def label(self) -> str:
        return {
            Level.URGENT_LOW: "Muito baixo",
            Level.LOW: "Baixo",
            Level.IN_RANGE: "No alvo",
            Level.HIGH: "Alto",
            Level.URGENT_HIGH: "Muito alto",
            Level.STALE: "Desatualizado",
        }.get(self, "—")

    @property
    def is_alert(self) -> bool:
        return self in (Level.URGENT_LOW, Level.LOW, Level.HIGH, Level.URGENT_HIGH)

    @property
    def is_urgent(self) -> bool:
        return self in (Level.URGENT_LOW, Level.URGENT_HIGH)


def value_level(value_mgdl: float, low: float, high: float, urgent_low: float, urgent_high: float) -> Level:
    if value_mgdl < urgent_low:
        return Level.URGENT_LOW
    if value_mgdl < low:
        return Level.LOW
    if value_mgdl > urgent_high:
        return Level.URGENT_HIGH
    if value_mgdl > high:
        return Level.HIGH
    return Level.IN_RANGE


def reading_level(reading: GlucoseReading | None, settings, now: datetime | None = None) -> Level:
    if reading is None:
        return Level.NONE
    if reading.age_minutes(now) > settings.stale_minutes:
        return Level.STALE
    return value_level(reading.value_mgdl, settings.target_low, settings.target_high,
                       settings.urgent_low, settings.urgent_high)
