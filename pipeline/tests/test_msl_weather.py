"""Curiosity REMS daily report → conditions (pipeline/sources/msl_weather.py), no network."""

from datetime import datetime, timezone

import pytest

from pipeline import config as C
from pipeline.sources.msl_weather import air_temp, conditions_for_sol, msd, sol_start_utc, utc_of_msd

REPORT = {  # the real report for sol 4718, as served by the feed
    "sol": "4718", "terrestrial_date": "2025-11-13", "ls": "170", "min_temp": "-74", "max_temp": "-5",
    "pressure": "695", "atmo_opacity": "Sunny", "sunrise": "05:22", "sunset": "17:20",
}
BASE = (-4.7934087, 137.3677713)


def test_mars_sol_date_matches_the_mars24_worked_example():
    # Mars24 algorithm page, example 1: 2000-01-06T00:00:00 UTC → MTC 23.99425 h, i.e. MSD 44795 + 23.99425/24.
    assert msd(datetime(2000, 1, 6, tzinfo=timezone.utc)) == pytest.approx(44795 + 23.99425 / 24, abs=1e-6)
    t = datetime(2025, 11, 13, 12, tzinfo=timezone.utc)
    assert abs((utc_of_msd(msd(t)) - t).total_seconds()) < 1e-3


def test_sol_4718_window_contains_curiosity_images_taken_that_sol():
    start = sol_start_utc(4718, BASE[1])
    end = sol_start_utc(4719, BASE[1])
    assert (end - start).total_seconds() == pytest.approx(88_775.244, abs=0.01)
    # Front Hazcam frame FLB_816332976 (sol 4718 in the raw-image archive) was taken 2025-11-13T20:17:38Z.
    assert start < datetime(2025, 11, 13, 20, 17, 38, tzinfo=timezone.utc) < end
    assert start.date().isoformat() == REPORT["terrestrial_date"]


def test_temperature_curve_hits_the_reported_extremes():
    t = lambda h: air_temp(h, -74, -5, 5 + 22 / 60, C.REMS_MAX_TEMP_LMST)
    assert t(5 + 22 / 60) == pytest.approx(-74)
    assert t(C.REMS_MAX_TEMP_LMST) == pytest.approx(-5)
    assert all(-74 <= t(h / 4) <= -5 for h in range(96))
    assert t(0) == pytest.approx(t(24))  # continuous over midnight


def test_conditions_series_is_one_sol_and_says_what_was_measured():
    series = conditions_for_sol(REPORT, *BASE)
    assert len(series) == 25
    assert {c["pressurePa"] for c in series} == {695.0}
    assert {c["status"] for c in series} == {"MODELED"}
    assert {c["dustTau"] for c in series} == {C.SUNNY_DUST_TAU}
    assert not any(c["radiationAlert"] for c in series)
    src = series[0]["source"]
    assert "sol 4718" in src and "-74 to -5 °C" in src and "OBSERVED" in src and src.endswith(C.MSL_WEATHER_URL)
    assert series[0]["time"].endswith("Z") and len(series[0]["time"]) == 24  # millisecond ISO, as the app expects
