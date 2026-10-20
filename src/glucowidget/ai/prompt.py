"""Montagem do prompt de análise a partir das leituras."""
from __future__ import annotations

from datetime import datetime

from glucowidget import metrics
from glucowidget.libre.models import GlucoseData
from glucowidget.units import MMOL, convert, format_value

MAX_POINTS = 160

SYSTEM_PROMPT = (
    "Você é um assistente que ajuda pessoas com diabetes a entender dados de monitoramento "
    "contínuo de glicose (CGM). Responda sempre em português do Brasil, em Markdown conciso, "
    "com tom acolhedor e objetivo. Use as seções: **Resumo**, **Padrões observados**, "
    "**Tendência atual**, **Pontos de atenção** e **Sugestões gerais**. Seja específico, citando "
    "horários e valores. Nunca prescreva doses de insulina ou medicamentos. Se houver risco "
    "imediato (hipoglicemia grave ou hiperglicemia persistente muito alta), destaque no início. "
    "Termine com uma linha curta lembrando que a análise não substitui orientação médica."
)


def _fmt(value_mgdl: float, unit: str) -> str:
    return format_value(value_mgdl, unit).replace(",", ".") if unit == MMOL else format_value(value_mgdl, unit)


def build_user_prompt(data: GlucoseData, unit: str, low: float, high: float, hours: int,
                      now: datetime | None = None) -> str:
    readings = metrics.window(data.history, hours, now)
    if len(readings) > MAX_POINTS:
        step = len(readings) / MAX_POINTS
        readings = [readings[int(i * step)] for i in range(MAX_POINTS)] + [readings[-1]]

    m = metrics.compute(readings, low, high)
    lines = [
        f"Unidade: {unit}. Faixa-alvo: {_fmt(low, unit)}–{_fmt(high, unit)} {unit}.",
        f"Período analisado: últimas {hours} h ({len(readings)} leituras).",
    ]
    if data.current:
        local = data.current.timestamp.astimezone()
        lines.append(
            f"Leitura atual: {_fmt(data.current.value_mgdl, unit)} {unit} às {local:%H:%M}, "
            f"tendência {data.current.trend.label}."
        )
    if m:
        lines.append(
            "Métricas do período: "
            f"média {_fmt(m.mean, unit)} {unit}; DP {_fmt(m.sd, unit)}; CV {m.cv:.0f}%; "
            f"tempo no alvo {m.tir:.0f}%; abaixo {m.tbr:.0f}%; acima {m.tar:.0f}%; "
            f"mín {_fmt(m.min, unit)}; máx {_fmt(m.max, unit)}; GMI estimado {m.gmi:.1f}%."
        )
    lines.append("")
    lines.append("Leituras (hora local, valor):")
    for r in readings:
        v = convert(r.value_mgdl, unit)
        lines.append(f"{r.timestamp.astimezone():%d/%m %H:%M},{v:.1f}" if unit == MMOL
                     else f"{r.timestamp.astimezone():%d/%m %H:%M},{round(v)}")
    lines.append("")
    lines.append("Analise esses dados.")
    return "\n".join(lines)
