import ast
import re
from pathlib import Path

import glucowidget
from glucowidget.ai.prompt import build_user_prompt, system_prompt
from glucowidget.i18n import DEFAULT_LANGUAGE, decimal, get_language, set_language, tr
from glucowidget.libre.models import GlucoseData, GlucoseReading, Trend
from glucowidget.locales.pt import CATALOG
from glucowidget.status import Level
from glucowidget.units import MGDL, MMOL, format_delta, format_value
from tests.test_core import NOW, series

PLACEHOLDER = re.compile(r"\{(\w+)(?::[^}]*)?\}")


def source_keys() -> set[str]:
    keys = set()
    for f in Path(glucowidget.__file__).parent.rglob("*.py"):
        if "locales" in f.parts:
            continue
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("tr", "N_")
                    and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)):
                keys.add(n.args[0].value)
    return keys


def test_default_language_is_english():
    assert DEFAULT_LANGUAGE == "en" and get_language() == "en"
    from glucowidget.config import Settings

    assert Settings().language == "en"


def test_every_source_string_has_portuguese_translation():
    missing = sorted(k for k in source_keys() if k not in CATALOG)
    assert not missing, f"sem tradução: {missing}"


def test_catalog_has_no_stale_entries():
    stale = sorted(k for k in CATALOG if k not in source_keys())
    assert not stale, f"entradas não usadas: {stale}"


def test_placeholders_match():
    for en, pt in CATALOG.items():
        assert set(PLACEHOLDER.findall(en)) == set(PLACEHOLDER.findall(pt)), en


def test_tr_switches_language_and_formats():
    assert tr("Try again") == "Try again"
    assert tr("Step {i} of {n}", i=1, n=3) == "Step 1 of 3"
    set_language("pt")
    assert tr("Try again") == "Tentar novamente"
    assert tr("Step {i} of {n}", i=1, n=3) == "Etapa 1 de 3"
    assert tr("not in catalog") == "not in catalog"  # fallback para o texto-fonte
    set_language("xx")
    assert get_language() == "en"


def test_number_and_enum_localization():
    assert format_value(180, MMOL) == "10.0" and decimal("1.5") == "1.5"
    set_language("pt")
    assert format_value(180, MMOL) == "10,0" and format_delta(9, MMOL) == "+0,5"
    assert format_value(120, MGDL) == "120"
    assert Level.LOW.label == "Baixo" and Trend.RISING.label == "subindo"
    set_language("en")
    assert Level.LOW.label == "Low" and Trend.RISING.label == "rising"


def test_ai_prompt_follows_language():
    rs = series([100, 150, 210])
    cur = GlucoseReading(210, rs[-1].timestamp, Trend.RISING)
    data = GlucoseData(current=cur, history=rs[:-1] + [cur])
    assert "Answer in English" in system_prompt()
    assert "Target range" in build_user_prompt(data, MGDL, 70, 180, 3, now=NOW)
    set_language("pt")
    assert "português do Brasil" in system_prompt()
    text = build_user_prompt(data, MMOL, 70, 180, 3, now=NOW)
    assert "Faixa-alvo: 3.9–10.0 mmol/L" in text  # decimais com ponto no prompt
