"""Cliente da API (não oficial) do LibreLinkUp.

A API é a mesma usada pelo app LibreLinkUp. É preciso uma conta *seguidora*
(convidada pelo paciente no app LibreLink) — o LibreView não tem API pública.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone

import httpx

from glucowidget.i18n import tr
from glucowidget.libre.models import GlucoseData, GlucoseReading, Patient, Trend

DEFAULT_HOST = "https://api.libreview.io"
DEFAULT_VERSION = "4.16.0"
TIMESTAMP_FORMAT = "%m/%d/%Y %I:%M:%S %p"


class LibreError(Exception):
    """Erro genérico da API."""


class AuthError(LibreError):
    """Credenciais inválidas ou sessão rejeitada."""


class TermsError(LibreError):
    """A conta precisa aceitar termos / verificar algo no app LibreLinkUp."""


class NoPatientError(LibreError):
    """A conta não segue nenhum paciente."""


class RateLimitError(LibreError):
    """Muitas requisições; aguarde."""


def host_for_region(region: str | None) -> str:
    return f"https://api-{region}.libreview.io" if region else DEFAULT_HOST


def parse_timestamp(item: dict) -> datetime:
    raw = item.get("FactoryTimestamp") or item.get("Timestamp")
    try:
        return datetime.strptime(raw, TIMESTAMP_FORMAT).replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def parse_measurement(item: dict) -> GlucoseReading:
    value = item.get("ValueInMgPerDl")
    if value is None:
        value = item.get("Value", 0)
    try:
        trend = Trend(int(item.get("TrendArrow") or 0))
    except ValueError:
        trend = Trend.UNKNOWN
    return GlucoseReading(value_mgdl=float(value), timestamp=parse_timestamp(item), trend=trend)


def parse_patient(item: dict) -> Patient:
    return Patient(
        id=str(item.get("patientId", "")),
        first_name=item.get("firstName", "") or "",
        last_name=item.get("lastName", "") or "",
    )


def parse_graph(payload: dict) -> GlucoseData:
    data = payload.get("data") or {}
    connection = data.get("connection") or {}
    current = None
    if connection.get("glucoseMeasurement"):
        current = parse_measurement(connection["glucoseMeasurement"])
    history = {r.timestamp: r for r in (parse_measurement(i) for i in data.get("graphData") or [])}
    if current:
        history[current.timestamp] = current
    patient = parse_patient(connection) if connection.get("patientId") else None
    return GlucoseData(current=current, history=sorted(history.values(), key=lambda r: r.timestamp), patient=patient)


class LibreLinkUpClient:
    def __init__(
        self,
        email: str,
        password: str,
        region: str | None = None,
        version: str = DEFAULT_VERSION,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 20.0,
    ):
        self.email = email
        self.password = password
        self.region = region or None
        self.version = version or DEFAULT_VERSION
        self._token: str | None = None
        self._token_expires: float = 0
        self._account_id: str | None = None
        self._http = httpx.Client(transport=transport, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    # -- infra ---------------------------------------------------------------
    @property
    def host(self) -> str:
        return host_for_region(self.region)

    def _headers(self, auth: bool) -> dict[str, str]:
        headers = {
            "product": "llu.android",
            "version": self.version,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Connection": "Keep-Alive",
        }
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"
            if self._account_id:
                headers["Account-Id"] = self._account_id
        return headers

    @staticmethod
    def _check_http(resp: httpx.Response) -> dict:
        if resp.status_code == 429:
            raise RateLimitError(tr("Too many requests to LibreLinkUp. Retrying shortly."))
        if resp.status_code in (401, 403):
            raise AuthError(tr("Session expired or access denied by LibreLinkUp."))
        if resp.status_code >= 400:
            raise LibreError(tr("LibreLinkUp server error (HTTP {code}).", code=resp.status_code))
        try:
            return resp.json()
        except ValueError as exc:
            raise LibreError(tr("Invalid response from LibreLinkUp.")) from exc

    # -- API -----------------------------------------------------------------
    def login(self) -> None:
        for _ in range(3):  # no máximo alguns redirects de região
            resp = self._http.post(
                f"{self.host}/llu/auth/login",
                headers=self._headers(auth=False),
                json={"email": self.email, "password": self.password},
            )
            payload = self._check_http(resp)
            status = payload.get("status")
            data = payload.get("data") or {}

            if data.get("redirect") and data.get("region"):
                self.region = data["region"]
                continue
            if status == 4:
                step = (data.get("step") or {}).get("type", "")
                raise TermsError(
                    tr(
                        "Open the LibreLinkUp app on your phone, sign in with this account and finish "
                        "the pending steps (terms of use / verification{step}).",
                        step=f": {step}" if step else "",
                    )
                )
            if status == 2 or not data.get("authTicket"):
                message = (payload.get("error") or {}).get("message", "")
                raise AuthError(
                    tr("Incorrect email or password.")
                    if status == 2
                    else tr("Login failed: {message}.", message=message or tr("unexpected response"))
                )
            if status not in (0, None):
                raise LibreError(tr("Login failed (status {status}).", status=status))

            ticket = data["authTicket"]
            self._token = ticket["token"]
            self._token_expires = float(ticket.get("expires") or (time.time() + 3600))
            user_id = (data.get("user") or {}).get("id", "")
            self._account_id = hashlib.sha256(user_id.encode()).hexdigest() if user_id else None
            return
        raise LibreError(tr("Too many region redirects."))

    def _authed_get(self, path: str) -> dict:
        if not self._token or time.time() > self._token_expires - 60:
            self.login()
        for attempt in range(2):
            resp = self._http.get(f"{self.host}{path}", headers=self._headers(auth=True))
            try:
                payload = self._check_http(resp)
            except AuthError:
                if attempt == 0:
                    self.login()
                    continue
                raise
            if payload.get("status") == 2 and attempt == 0:  # token rejeitado
                self.login()
                continue
            return payload
        raise AuthError(tr("Could not authenticate with LibreLinkUp."))

    def connections(self) -> list[Patient]:
        payload = self._authed_get("/llu/connections")
        return [parse_patient(i) for i in payload.get("data") or []]

    def graph(self, patient_id: str) -> GlucoseData:
        return parse_graph(self._authed_get(f"/llu/connections/{patient_id}/graph"))
