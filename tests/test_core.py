from datetime import datetime, timedelta, timezone

import pytest

from glucowidget import metrics
from glucowidget.ai.prompt import build_user_prompt
from glucowidget.config import Settings
from glucowidget.libre.models import GlucoseData, GlucoseReading, Trend
from glucowidget.status import Level, reading_level
from glucowidget.units import MGDL, MMOL, convert, format_delta, format_value, to_mgdl

NOW = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)


def series(values, step_min=5, end=NOW):
    n = len(values)
    return [GlucoseReading(v, end - timedelta(minutes=step_min * (n - 1 - i))) for i, v in enumerate(values)]


def test_unit_conversion_roundtrip():
    assert convert(180, MGDL) == 180
    assert convert(180, MMOL) == pytest.approx(9.99, abs=0.01)
    assert to_mgdl(convert(123, MMOL), MMOL) == pytest.approx(123)


def test_format_value_and_delta():
    assert format_value(123.4, MGDL) == "123"
    assert format_value(180, MMOL) == "10.0"
    assert format_delta(4, MGDL) == "+4"
    assert format_delta(-12, MGDL) == "−12"
    assert format_delta(0.2, MGDL) == "±0"
    assert format_delta(9, MMOL) == "+0.5"


def test_metrics():
    m = metrics.compute(series([60, 100, 150, 200]), 70, 180)
    assert m.count == 4
    assert m.mean == pytest.approx(127.5)
    assert m.tir == 50 and m.tbr == 25 and m.tar == 25
    assert m.gmi == pytest.approx(3.31 + 0.02392 * 127.5)
    assert metrics.compute([], 70, 180) is None


def test_window_filters_by_hours():
    rs = series(list(range(100, 100 + 48)), step_min=15)  # 12 h
    assert len(metrics.window(rs, 3, NOW)) == 13


def test_levels():
    s = Settings()
    fresh = lambda v: GlucoseReading(v, datetime.now(timezone.utc))  # noqa: E731
    assert reading_level(fresh(50), s) == Level.URGENT_LOW
    assert reading_level(fresh(65), s) == Level.LOW
    assert reading_level(fresh(120), s) == Level.IN_RANGE
    assert reading_level(fresh(200), s) == Level.HIGH
    assert reading_level(fresh(300), s) == Level.URGENT_HIGH
    old = GlucoseReading(120, datetime.now(timezone.utc) - timedelta(minutes=30))
    assert reading_level(old, s) == Level.STALE
    assert reading_level(None, s) == Level.NONE


def test_delta_uses_previous_reading():
    rs = series([100, 110, 118])
    data = GlucoseData(current=rs[-1], history=rs)
    assert data.delta_mgdl == 8


def test_prompt_contains_readings_and_metrics():
    rs = series([100, 150, 210])
    current = GlucoseReading(210, rs[-1].timestamp, Trend.RISING)
    data = GlucoseData(current=current, history=rs[:-1] + [current])
    text = build_user_prompt(data, MGDL, 70, 180, 3, now=NOW)
    assert "Target range: 70–180 mg/dL" in text
    assert "trend rising" in text
    assert "in range 67%" in text
    assert text.rstrip().splitlines()[-3].endswith(",210")


def test_settings_roundtrip(tmp_path):
    path = tmp_path / "s.json"
    s = Settings(email="a@b.com", unit=MMOL, compact=True)
    s.save(path)
    loaded = Settings.load(path)
    assert loaded.email == "a@b.com" and loaded.unit == MMOL and loaded.compact
    path.write_text('{"email": "x@y.z", "unknown_field": 1}')
    assert Settings.load(path).email == "x@y.z"
