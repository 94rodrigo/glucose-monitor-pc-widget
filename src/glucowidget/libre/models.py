from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import IntEnum


class Trend(IntEnum):
    UNKNOWN = 0
    FALLING_FAST = 1
    FALLING = 2
    STABLE = 3
    RISING = 4
    RISING_FAST = 5

    @property
    def label(self) -> str:
        return {
            Trend.FALLING_FAST: "caindo rápido",
            Trend.FALLING: "caindo",
            Trend.STABLE: "estável",
            Trend.RISING: "subindo",
            Trend.RISING_FAST: "subindo rápido",
        }.get(self, "desconhecida")

    @property
    def arrow(self) -> str:
        return {
            Trend.FALLING_FAST: "↓↓",
            Trend.FALLING: "↘",
            Trend.STABLE: "→",
            Trend.RISING: "↗",
            Trend.RISING_FAST: "↑↑",
        }.get(self, "")


@dataclass(frozen=True)
class GlucoseReading:
    value_mgdl: float
    timestamp: datetime  # sempre com timezone (UTC)
    trend: Trend = Trend.UNKNOWN

    def age_minutes(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return (now - self.timestamp).total_seconds() / 60


@dataclass(frozen=True)
class Patient:
    id: str
    first_name: str = ""
    last_name: str = ""

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.id


@dataclass
class GlucoseData:
    current: GlucoseReading | None
    history: list[GlucoseReading] = field(default_factory=list)  # ordenado, inclui a atual
    patient: Patient | None = None

    @property
    def previous(self) -> GlucoseReading | None:
        """Leitura anterior à atual com pelo menos ~4 min de distância."""
        if not self.current:
            return None
        for r in reversed(self.history):
            if (self.current.timestamp - r.timestamp).total_seconds() >= 240:
                return r
        return None

    @property
    def delta_mgdl(self) -> float | None:
        prev = self.previous
        if not prev or not self.current:
            return None
        return self.current.value_mgdl - prev.value_mgdl
