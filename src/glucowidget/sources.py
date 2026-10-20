"""Fontes de dados: LibreLinkUp real e modo demonstração."""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

import httpx

from glucowidget.i18n import tr

from glucowidget.libre.client import (
    LibreError,
    LibreLinkUpClient,
    NoPatientError,
)
from glucowidget.libre.models import GlucoseData, GlucoseReading, Patient, Trend


class SetupRequired(Exception):
    """Conta ainda não configurada."""


class LibreSource:
    def __init__(self, email: str, password: str, region: str, patient_id: str, version: str):
        if not email or not password:
            raise SetupRequired(tr("Set up your LibreLinkUp account."))
        self.client = LibreLinkUpClient(email, password, region=region, version=version)
        self.patient_id = patient_id

    @property
    def region(self) -> str:
        return self.client.region or ""

    def fetch(self) -> GlucoseData:
        if not self.patient_id:
            patients = self.client.connections()
            if not patients:
                raise NoPatientError(
                    tr("This account is not following any patient. In the LibreLink app, go to Share → Connect LibreLinkUp app and invite this email.")
                )
            self.patient_id = patients[0].id
        return self.client.graph(self.patient_id)

    def close(self) -> None:
        self.client.close()


class DemoSource:
    """Dados sintéticos para testar a interface sem conta."""

    SCENARIOS = ("normal", "low", "high", "stale", "offline", "auth", "nopatient")

    def __init__(self, scenario: str = "normal"):
        self.scenario = scenario if scenario in self.SCENARIOS else "normal"
        self.calls = 0
        self._rng = random.Random(42)
        self._base = {"low": 62, "high": 215}.get(self.scenario, 125)

    def _value(self, t: datetime) -> float:
        hours = t.timestamp() / 3600
        meal = 45 * max(0.0, math.sin(hours * math.pi / 4)) ** 3
        wave = 18 * math.sin(hours * 0.9)
        return max(40, min(380, self._base + meal + wave + self._rng.uniform(-4, 4)))

    def fetch(self) -> GlucoseData:
        self.calls += 1
        if self.scenario == "auth":
            from glucowidget.libre.client import AuthError

            raise AuthError(tr("Incorrect email or password."))
        if self.scenario == "nopatient":
            raise NoPatientError(
                tr("This account is not following any patient. In the LibreLink app, go to Share → Connect LibreLinkUp app and invite this email.")
            )
        if self.scenario == "offline" and self.calls > 1:
            raise httpx.ConnectError("No connection (demo)")

        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        if self.scenario == "stale":
            now -= timedelta(minutes=27)
        history = []
        for i in range(12 * 12, -1, -1):
            t = now - timedelta(minutes=5 * i)
            history.append(GlucoseReading(round(self._value(t)), t))
        current_v = history[-1].value_mgdl
        if self.scenario == "low":
            current_v = 58
            history[-1] = GlucoseReading(current_v, now)
        diff = current_v - history[-2].value_mgdl
        trend = (Trend.RISING_FAST if diff > 9 else Trend.RISING if diff > 3 else
                 Trend.FALLING_FAST if diff < -9 else Trend.FALLING if diff < -3 else Trend.STABLE)
        current = GlucoseReading(current_v, now, trend)
        history[-1] = current
        return GlucoseData(current=current, history=history, patient=Patient("demo", "Paciente", "Demo"))

    def close(self) -> None:
        pass


def classify_error(exc: Exception) -> str:
    from glucowidget.libre.client import AuthError, RateLimitError, TermsError

    if isinstance(exc, SetupRequired):
        return "setup"
    if isinstance(exc, AuthError):
        return "auth"
    if isinstance(exc, TermsError):
        return "terms"
    if isinstance(exc, NoPatientError):
        return "nopatient"
    if isinstance(exc, (httpx.HTTPError, RateLimitError)):
        return "network"
    if isinstance(exc, LibreError):
        return "error"
    return "error"
