"""NASA DONKI → space weather (pipeline/sources/donki.py) and its alerts in the conditions, no network."""

from datetime import datetime, timezone

from pipeline import config as C
from pipeline.sources.donki import build_space_weather, mars_forecasts
from pipeline.sources.msl_weather import conditions_for_sol

T0 = datetime(2025, 11, 6, tzinfo=timezone.utc)
T1 = datetime(2025, 11, 14, tzinfo=timezone.utc)


def sim(run, arrival, location="Mars", minor=False, glancing=False):
    return {
        "modelCompletionTime": run, "link": f"https://ccmc/{run}",
        "cmeInputs": [{"CMEID": "C1", "cmeStartTime": "2025-11-09T21:12Z", "speed": 975.0}],
        "impactList": [{"location": location, "arrivalTime": arrival, "isMinorImpact": minor, "isGlancingBlow": glancing}],
    }


def test_mars_forecasts_keep_mars_impacts_once_from_the_earliest_run():
    f = mars_forecasts([
        sim("2025-11-10T05:00Z", "2025-11-13T04:00Z"),
        sim("2025-11-10T02:34Z", "2025-11-13T04:00Z"),
        sim("2025-11-10T02:34Z", "2025-11-12T10:00Z", location="Earth"),
    ])
    assert len(f) == 1 and f[0]["modelRun"] == "2025-11-10T02:34Z"


def test_direct_impact_is_an_alert_and_minor_or_glancing_an_advisory():
    sw = build_space_weather([sim("r1", "2025-11-13T04:00Z"), sim("r2", "2025-11-11T00:00Z", minor=True), sim("r3", "2025-11-09T00:00Z", glancing=True)], [], T0, T1)
    levels = {w["start"][:13]: w["level"] for w in sw["windows"]}
    assert levels == {"2025-11-12T16": "alert", "2025-11-10T12": "advisory", "2025-11-08T12": "advisory"}
    w = next(x for x in sw["windows"] if x["level"] == "alert")
    assert w["end"] == "2025-11-13T16:00:00.000Z"  # arrival + CME_ARRIVAL_UNCERTAINTY_H
    assert C.CME_ARRIVAL_UNCERTAINTY_H == 12.0
    assert sw["status"] == "MODELED" and all(e["atMars"] for e in sw["events"])


def test_sep_events_are_context_not_mars():
    seps = [{"eventTime": "2025-11-11T09:45Z", "link": "https://ccmc/sep1"}, {"eventTime": "2025-11-14T09:20Z", "link": "x"}]
    sw = build_space_weather([], seps, T0, T1)
    assert sw["windows"] == []
    assert sw["events"][0]["kind"] == "sep" and not sw["events"][0]["atMars"] and "not measured at Mars" in sw["events"][0]["summary"]


def test_alert_windows_become_radiation_alerts_in_the_conditions():
    report = {"sol": "4718", "terrestrial_date": "2025-11-13", "ls": "170", "min_temp": "-74", "max_temp": "-5",
              "pressure": "695", "atmo_opacity": "Sunny", "sunrise": "05:22", "sunset": "17:20"}
    a = datetime(2025, 11, 13, 6, tzinfo=timezone.utc)
    b = datetime(2025, 11, 13, 12, tzinfo=timezone.utc)
    series = conditions_for_sol(report, -4.79, 137.37, [(a, b, "https://ccmc/x")])
    flagged = [c["time"] for c in series if c["radiationAlert"]]
    assert flagged and all("2025-11-13T0" in t or "2025-11-13T1" in t for t in flagged)
    assert "1 alert window" in series[0]["source"]
    assert not any(c["radiationAlert"] for c in conditions_for_sol(report, -4.79, 137.37))
