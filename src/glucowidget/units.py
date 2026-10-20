"""Conversão e formatação de unidades de glicemia."""
from __future__ import annotations

from glucowidget.i18n import decimal

MGDL_PER_MMOL = 18.0182
MGDL = "mg/dL"
MMOL = "mmol/L"
UNITS = (MGDL, MMOL)


def convert(value_mgdl: float, unit: str) -> float:
    return value_mgdl / MGDL_PER_MMOL if unit == MMOL else float(value_mgdl)


def to_mgdl(value: float, unit: str) -> float:
    return value * MGDL_PER_MMOL if unit == MMOL else float(value)


def format_value(value_mgdl: float, unit: str) -> str:
    v = convert(value_mgdl, unit)
    if unit == MMOL:
        return decimal(f"{v:.1f}")
    return str(round(v))


def format_delta(delta_mgdl: float, unit: str) -> str:
    v = convert(delta_mgdl, unit)
    if unit == MMOL:
        text = f"{abs(v):.1f}"
        zero = text == "0.0"
    else:
        text = str(round(abs(v)))
        zero = text == "0"
    if zero:
        return "±0"
    return ("+" if v > 0 else "−") + decimal(text)
