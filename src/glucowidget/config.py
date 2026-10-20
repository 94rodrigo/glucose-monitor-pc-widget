"""Configurações persistidas em JSON; segredos no cofre do sistema (keyring)."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from platformdirs import user_config_dir

from glucowidget import APP_ID
from glucowidget.units import MGDL

log = logging.getLogger(__name__)

CONFIG_DIR = Path(user_config_dir(APP_ID, appauthor=False))
CONFIG_FILE = CONFIG_DIR / "settings.json"
FALLBACK_SECRETS_FILE = CONFIG_DIR / "secrets.json"
KEYRING_SERVICE = APP_ID


@dataclass
class Settings:
    # Conta LibreLinkUp
    email: str = ""
    region: str = ""
    patient_id: str = ""
    api_version: str = "4.16.0"
    poll_seconds: int = 60

    # Glicemia (sempre armazenado em mg/dL)
    unit: str = MGDL
    target_low: float = 70
    target_high: float = 180
    urgent_low: float = 54
    urgent_high: float = 250
    stale_minutes: int = 15

    # Aparência
    language: str = "en"  # en | pt
    theme: str = "system"  # system | dark | light
    always_on_top: bool = True
    hide_from_taskbar: bool = True
    opacity: float = 0.96
    scale: float = 1.0
    compact: bool = False
    chart_hours: int = 3
    reduce_motion: bool = False
    pos_x: int | None = None
    pos_y: int | None = None

    # Alertas
    notify_enabled: bool = True
    notify_urgent_only: bool = False

    # IA
    ai_provider: str = ""  # vazio = desativado
    ai_model: str = ""
    ai_base_url: str = ""
    ai_hours: int = 12
    ai_auto_minutes: int = 0  # 0 = desligado

    # Sistema
    autostart: bool = False
    onboarded: bool = False

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_provider)

    # -- persistência ----------------------------------------------------------
    @classmethod
    def load(cls, path: Path = CONFIG_FILE) -> "Settings":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return cls()
        except (OSError, ValueError) as exc:
            log.warning("Unreadable settings (%s); using defaults.", exc)
            return cls()
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in raw.items() if k in known})

    def save(self, path: Path = CONFIG_FILE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)


# -- segredos ------------------------------------------------------------------
def _fallback_load() -> dict[str, str]:
    try:
        return json.loads(FALLBACK_SECRETS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _fallback_save(data: dict[str, str]) -> None:
    FALLBACK_SECRETS_FILE.parent.mkdir(parents=True, exist_ok=True)
    FALLBACK_SECRETS_FILE.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(FALLBACK_SECRETS_FILE, 0o600)
    except OSError:
        pass


def get_secret(name: str) -> str:
    try:
        import keyring

        value = keyring.get_password(KEYRING_SERVICE, name)
        if value is not None:
            return value
    except Exception as exc:  # backend indisponível
        log.debug("keyring unavailable: %s", exc)
    return _fallback_load().get(name, "")


def set_secret(name: str, value: str) -> None:
    try:
        import keyring

        if value:
            keyring.set_password(KEYRING_SERVICE, name, value)
        else:
            try:
                keyring.delete_password(KEYRING_SERVICE, name)
            except Exception:
                pass
        # se gravou no keyring, garante que não sobra cópia no arquivo
        data = _fallback_load()
        if name in data:
            data.pop(name)
            _fallback_save(data)
        return
    except Exception as exc:
        log.warning("System keyring unavailable (%s); saving to %s.", exc, FALLBACK_SECRETS_FILE)
    data = _fallback_load()
    if value:
        data[name] = value
    else:
        data.pop(name, None)
    _fallback_save(data)


LIBRE_PASSWORD = "libre_password"


def ai_key_name(provider: str) -> str:
    return f"ai_key:{provider}"
