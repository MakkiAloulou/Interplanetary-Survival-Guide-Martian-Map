"""NASA DONKI space weather around the planned sol → SpaceWeather for the site (CLAUDE.md §8, radiation slot).

    python -m pipeline donki          # writes data/processed/gale/space_weather.json

DONKI (Space Weather Database Of Notifications, Knowledge, Information; NASA CCMC) is read through api.nasa.gov
(key from the NASA_API_KEY environment variable, else the public DEMO_KEY). For the window from SPACE_WEATHER_LOOKBACK_DAYS
before the planned sol to its end:
- WSA-Enlil CME simulations with an impact at Mars → one entry per forecast arrival. Rule (MODELED, config.py):
  a direct, non-minor arrival is an ALERT (the app's radiation check: NO-GO) and a minor or glancing one an ADVISORY
  (a caution), each for the arrival time ± CME_ARRIVAL_UNCERTAINTY_H;
- solar energetic particle (SEP) events, listed as context: they are measured near Earth or by STEREO-A, not at Mars.
Then `python -m pipeline msl-weather` marks the ALERT windows as radiation alerts in the conditions.
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline import config as C

DONKI_API = "https://api.nasa.gov/DONKI/"


def _parse(t: str) -> datetime:
    """DONKI times: '2025-11-13T04:00Z'."""
    return datetime.strptime(t.replace("Z", ""), "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)


def _iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def fetch(kind: str, start: datetime, end: datetime, cache_dir: Path) -> list[dict]:
    """One DONKI endpoint for a date range (cached as JSON). A failed endpoint returns [] and is reported."""
    cache = Path(cache_dir) / f"donki_{kind}_{start:%Y%m%d}_{end:%Y%m%d}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    key = os.environ.get("NASA_API_KEY", "DEMO_KEY")
    url = f"{DONKI_API}{kind}?startDate={start:%Y-%m-%d}&endDate={end:%Y-%m-%d}&api_key={key}"
    req = urllib.request.Request(url, headers={"User-Agent": "martian-map-pipeline"})
    data = json.loads(urllib.request.urlopen(req, timeout=90).read())
    if not isinstance(data, list):
        raise ValueError(f"DONKI {kind}: unexpected response")
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(data), encoding="utf-8")
    return data


def mars_forecasts(sims: list[dict]) -> list[dict]:
    """Forecast CME arrivals at Mars from WSA-Enlil simulations (one per distinct arrival time, earliest model run)."""
    out: dict[str, dict] = {}
    for s in sims:
        for imp in s.get("impactList") or []:
            if "Mars" not in (imp.get("location") or ""):
                continue
            arrival = imp["arrivalTime"]
            cme = (s.get("cmeInputs") or [{}])[0]
            entry = {
                "arrival": _parse(arrival),
                "glancing": bool(imp.get("isGlancingBlow")),
                "minor": bool(imp.get("isMinorImpact")),
                "cme": cme.get("CMEID") or "",
                "launch": cme.get("cmeStartTime") or "",
                "speed": cme.get("speed"),
                "modelRun": s.get("modelCompletionTime") or "",
                "link": s.get("link") or "",
            }
            if arrival not in out or entry["modelRun"] < out[arrival]["modelRun"]:
                out[arrival] = entry
    return sorted(out.values(), key=lambda e: e["arrival"])


def build_space_weather(sims: list[dict], seps: list[dict], start: datetime, end: datetime) -> dict:
    events, windows = [], []
    for f in mars_forecasts(sims):
        level = "advisory" if (f["minor"] or f["glancing"]) else "alert"
        impact = "glancing" if f["glancing"] else "minor direct" if f["minor"] else "direct"
        half = timedelta(hours=C.CME_ARRIVAL_UNCERTAINTY_H)
        speed = f" at {f['speed']:.0f} km/s" if f["speed"] else ""
        summary = (
            f"CME launched {f['launch'].replace('T', ' ')} UTC{speed} forecast to reach Mars {f['arrival']:%Y-%m-%d %H:%M} UTC "
            f"({impact} impact; NASA CCMC WSA-Enlil run of {f['modelRun'].replace('T', ' ')} UTC)."
        )
        events.append({"time": _iso(f["arrival"]), "kind": "cme-mars", "summary": summary, "atMars": True, "link": f["link"]})
        windows.append({
            "start": _iso(f["arrival"] - half), "end": _iso(f["arrival"] + half), "level": level,
            "reason": f"{summary} Window ±{C.CME_ARRIVAL_UNCERTAINTY_H:.0f} h.", "link": f["link"],
        })
    if seps:
        times = sorted(_parse(e["eventTime"]) for e in seps)
        events.append({
            "time": _iso(times[0]), "kind": "sep",
            "summary": (
                f"{len(seps)} solar energetic particle detections from {times[0]:%Y-%m-%d} to {times[-1]:%Y-%m-%d}, all by "
                f"spacecraft near Earth or STEREO-A: not measured at Mars."
            ),
            "atMars": False, "link": seps[0].get("link") or "",
        })
    return {
        "window": {"start": _iso(start), "end": _iso(end)},
        "events": sorted(events, key=lambda e: e["time"]),
        "windows": windows,
        "source": (
            "NASA DONKI (Community Coordinated Modeling Center), WSA-Enlil CME simulations and SEP events, via "
            f"api.nasa.gov; forecasts are model output, alert levels our rule (MODELED). {DONKI_API}"
        ),
        "status": "MODELED",
    }


def convert(
    out_json: Path = C.DATA_DIR / "processed" / "gale" / "space_weather.json",
    conditions_json: Path = C.DATA_DIR / "processed" / "gale" / "conditions.json",
    cache_dir: Path = C.DATA_DIR / "raw" / "donki",
) -> dict:
    series = json.loads(Path(conditions_json).read_text(encoding="utf-8"))
    sol_start = datetime.fromisoformat(series[0]["time"].replace("Z", "+00:00"))
    sol_end = datetime.fromisoformat(series[-1]["time"].replace("Z", "+00:00"))
    start = sol_start - timedelta(days=C.SPACE_WEATHER_LOOKBACK_DAYS)
    sims = fetch("WSAEnlilSimulations", start, sol_end, cache_dir)
    seps = fetch("SEP", sol_start - timedelta(days=3), sol_end + timedelta(days=1), cache_dir)
    sw = build_space_weather(sims, seps, start, sol_end)
    Path(out_json).write_text(json.dumps(sw, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"events": len(sw["events"]), "windows": [(w["level"], w["start"], w["end"]) for w in sw["windows"]]}
