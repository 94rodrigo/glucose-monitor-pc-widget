from datetime import timedelta

from glucowidget import metrics
from glucowidget.ai.prompt import MAX_POINTS, build_user_prompt, system_prompt
from glucowidget.i18n import set_language
from glucowidget.libre.models import GlucoseData, GlucoseReading, Trend
from glucowidget.units import MGDL, MMOL
from tests.test_core import NOW, series


def data_from(readings, trend=Trend.STABLE):
    current = GlucoseReading(readings[-1].value_mgdl, readings[-1].timestamp, trend)
    return GlucoseData(current=current, history=readings[:-1] + [current])


def prompt(readings, hours=12, unit=MGDL, now=NOW, **kw):
    return build_user_prompt(data_from(readings), unit, 70, 180, hours, now=now, **kw)


# --- métricas -----------------------------------------------------------------------------

def test_compute_splits_urgent_levels():
    m = metrics.compute(series([40, 60, 100, 100, 200, 300]), 70, 180, 54, 250)
    assert round(m.very_low) == 17 and round(m.tbr) == 33  # tbr inclui o muito baixo
    assert round(m.very_high) == 17 and round(m.tar) == 33
    assert round(m.tir) == 33


def test_coverage_and_gaps():
    rs = series(list(range(100, 112)), step_min=5)
    assert metrics.coverage_hours(rs) == 55 / 60
    assert metrics.find_gaps(rs) == []
    with_hole = rs[:6] + [GlucoseReading(v.value_mgdl, v.timestamp + timedelta(minutes=60)) for v in rs[6:]]
    gaps = metrics.find_gaps(with_hole)
    assert len(gaps) == 1 and round(gaps[0][1]) == 65


# --- o que o modelo recebe -----------------------------------------------------------------

def test_reports_real_coverage_when_less_than_requested():
    rs = series([120] * 145, step_min=5)  # 12 h de dados
    text = prompt(rs, hours=24)
    assert "Only 12.0 h of data are available, less than the 24 h requested." in text
    assert "Only" not in prompt(rs, hours=6)


def test_current_time_age_and_staleness():
    fresh = prompt(series([120, 121, 122]))
    assert "Current time:" in fresh and "(0 min ago)" in fresh and "Warning" not in fresh
    old = series([120, 121, 122], end=NOW - timedelta(minutes=40))
    text = prompt(old)
    assert "(40 min ago)" in text and "more than 15 minutes old" in text
    assert "more than 30 minutes old" in prompt(old, stale_minutes=30)


def test_urgent_thresholds_and_time_in_each_range():
    text = prompt(series([40, 60, 100, 100, 200, 300]))
    assert "Urgent thresholds: below 54 and above 250 mg/dL" in text
    assert "Time in ranges: very low 17%; low 17%; in range 33%; high 17%; very high 17%." in text
    mmol = prompt(series([100, 110]), unit=MMOL, urgent_low=54, urgent_high=250)
    assert "below 3.0 and above 13.9 mmol/L" in mmol
    assert "below 60 and above 200 mg/dL" in prompt(series([100, 110]), urgent_low=60, urgent_high=200)


def test_gmi_is_not_sent():
    text = prompt(series([100, 110, 120]))
    assert "GMI" not in text and "Period metrics:" in text


def test_data_gaps_are_reported():
    rs = series(list(range(100, 112)), step_min=5)
    assert "No data gaps." in prompt(rs)
    with_hole = rs[:6] + [GlucoseReading(v.value_mgdl, v.timestamp + timedelta(minutes=60)) for v in rs[6:]]
    assert "Data gaps: 1 (longest 65 min" in prompt(with_hole)


def test_no_readings_in_period():
    rs = series([100, 110], end=NOW - timedelta(hours=30))
    assert "There are no readings in the requested period." in prompt(rs, hours=6)


def test_downsampling_keeps_extremes_and_metrics_use_all_readings():
    values = [120] * 400
    values[123] = 45  # queda breve que uma amostragem simples poderia perder
    values[300] = 260
    rs = series(values, step_min=2)
    text = prompt(rs, hours=24, now=NOW)
    readings = [l for l in text.splitlines() if "," in l and l[:2].isdigit()]
    assert len(readings) <= MAX_POINTS + 3
    assert any(l.endswith(",45") for l in readings) and any(l.endswith(",260") for l in readings)
    assert "400 readings" in text  # métricas e cobertura sobre todas as leituras
    assert "min 45 mg/dL; max 260 mg/dL" in text


def test_system_prompt_grounding_rules():
    s = system_prompt()
    for clause in ("Use only the data provided", "never invent causes", "Never prescribe",
                   "very-low threshold", "say so first", "Do not repeat the summary numbers"):
        assert clause in s, clause


def test_portuguese_prompt_is_fully_translated():
    set_language("pt")
    text = prompt(series([40, 100, 200]), hours=24)
    for expected in ("Limites de urgência", "Hora atual", "Última leitura", "Os dados cobrem", "Há apenas",
                     "Tempo nas faixas", "Métricas do período"):
        assert expected in text, expected
    for leftover in ("Data covers", "Latest reading", "Urgent thresholds", "Time in ranges"):
        assert leftover not in text, leftover
    assert "Use apenas os dados fornecidos" in system_prompt()
