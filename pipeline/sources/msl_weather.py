"""Curiosity REMS daily weather report → Conditions[] for one sol at the site (CLAUDE.md §8, weather slot).

    python -m pipeline msl-weather        # writes data/processed/gale/conditions.json

The feed (NASA, "Mars Weather" from Curiosity's REMS station) gives per sol: air temperature min and max, pressure,
an opacity word ("Sunny"), sunrise and sunset in local mean solar time. It has no hourly values, no numeric dust
opacity and no radiation. So, for MSL_WEATHER_SOL:
- times: one sample per Mars hour from local mean midnight at the habitat (25 samples, Mars24 time scale);
- temperature: the reported minimum at the reported sunrise and the maximum at REMS_MAX_TEMP_LMST, joined by
  half-cosine curves (shape MODELED, end values OBSERVED);
- pressure: the reported daily value (OBSERVED, no diurnal cycle);
- dust opacity: SUNNY_DUST_TAU for "Sunny" (MODELED);
- radiation alert: false, no public real-time alert data (MODELED); the app's solar-storm drill tests that check;
- sun elevation: an approximation from the reported Ls; the app replaces it with its Mars24 clock (DERIVED).
Every sample is therefore MODELED, and its `source` says which parts were measured.
"""

import json
import math
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from pipeline import config as C

# Mars24 (Allison & McEwen 2000; https://www.giss.nasa.gov/tools/mars24/help/algorithm.html), as in app/src/marsTime.ts.
# TAI - UTC leap seconds by start date (IERS; the same table as app/src/marsTime.ts), 1999 onwards.
LEAP_SECONDS = [
    (datetime(1999, 1, 1, tzinfo=timezone.utc), 32),
    (datetime(2006, 1, 1, tzinfo=timezone.utc), 33),
    (datetime(2009, 1, 1, tzinfo=timezone.utc), 34),
    (datetime(2012, 7, 1, tzinfo=timezone.utc), 35),
    (datetime(2015, 7, 1, tzinfo=timezone.utc), 36),
    (datetime(2017, 1, 1, tzinfo=timezone.utc), 37),
]
MARS_SOL_RATIO = 1.0274912517  # Earth days per sol
MSD_EPOCH_JD_TT = 2451549.5
MSD_OFFSET = 44796.0 - 0.0009626
# Curiosity sol 0 = the sol of landing, 2012-08-06T05:17:57Z at Bradbury Landing (137.4417 E).
MSL_LANDING_UTC = datetime(2012, 8, 6, 5, 17, 57, tzinfo=timezone.utc)
MSL_LANDING_LON_E = 137.4417


def tt_minus_utc_s(t: datetime) -> float:
    """TT - UTC in seconds: leap seconds + 32.184 s (dates from 1999)."""
    if t < LEAP_SECONDS[0][0]:
        raise ValueError("leap-second table starts in 1999")
    return [n for start, n in LEAP_SECONDS if t >= start][-1] + 32.184


def msd(t: datetime) -> float:
    """Mars Sol Date at UTC time t."""
    jd_tt = t.timestamp() / 86400 + 2440587.5 + tt_minus_utc_s(t) / 86400
    return (jd_tt - MSD_EPOCH_JD_TT) / MARS_SOL_RATIO + MSD_OFFSET


def utc_of_msd(m: float) -> datetime:
    """Inverse of msd (the leap-second count is taken at the first estimate; exact except within seconds of a leap)."""
    jd_tt = (m - MSD_OFFSET) * MARS_SOL_RATIO + MSD_EPOCH_JD_TT
    guess = datetime.fromtimestamp((jd_tt - 2440587.5) * 86400, tz=timezone.utc)
    return datetime.fromtimestamp((jd_tt - 2440587.5 - tt_minus_utc_s(guess) / 86400) * 86400, tz=timezone.utc)


def sol_start_utc(sol: int, lon_east: float) -> datetime:
    """UTC of local mean midnight at lon_east that starts Curiosity mission sol `sol`."""
    landing_sol_msd = math.floor(msd(MSL_LANDING_UTC) + MSL_LANDING_LON_E / 360)  # local MSD of sol 0
    return utc_of_msd(landing_sol_msd + sol - lon_east / 360)


def hhmm(text: str) -> float:
    h, m = text.split(":")
    return int(h) + int(m) / 60


def air_temp(h: float, t_min: float, t_max: float, sunrise_h: float, max_h: float) -> float:
    """Air temperature at local hour h: min at sunrise, max at max_h, half-cosine between (wraps over midnight)."""
    if h < sunrise_h:
        h += 24
    if h <= max_h:
        f = (1 - math.cos(math.pi * (h - sunrise_h) / (max_h - sunrise_h))) / 2
        return t_min + (t_max - t_min) * f
    f = (1 - math.cos(math.pi * (h - max_h) / (sunrise_h + 24 - max_h))) / 2
    return t_max - (t_max - t_min) * f


def approx_sun_elevation(lat: float, ls_deg: float, lmst_h: float) -> float:
    """Sun elevation from declination (Ls) and hour angle (LMST, no equation of time). Approximate."""
    dec = math.degrees(math.asin(0.42565 * math.sin(math.radians(ls_deg)))) + 0.25 * math.sin(math.radians(ls_deg))
    ha = math.radians(15 * (lmst_h - 12))
    la, de = math.radians(lat), math.radians(dec)
    return math.degrees(math.asin(math.sin(la) * math.sin(de) + math.cos(la) * math.cos(de) * math.cos(ha)))


def load_feed(cache: Path, url: str = C.MSL_WEATHER_URL) -> list[dict]:
    cache = Path(cache)
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "martian-map-pipeline"})
        cache.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    return json.loads(cache.read_text(encoding="utf-8"))["soles"]


def conditions_for_sol(report: dict, lat: float, lon_east: float) -> list[dict]:
    sol = int(report["sol"])
    t_min, t_max, pressure = float(report["min_temp"]), float(report["max_temp"]), float(report["pressure"])
    sunrise_h = hhmm(report["sunrise"])
    tau = C.SUNNY_DUST_TAU if report["atmo_opacity"] == "Sunny" else C.CLOUDY_DUST_TAU
    source = (
        f"Curiosity REMS daily report, sol {sol} ({report['terrestrial_date']}), NASA/JPL-Caltech/CAB(CSIC-INTA): "
        f"air {t_min:.0f} to {t_max:.0f} °C and {pressure:.0f} Pa measured (OBSERVED); hourly curve between them MODELED; "
        f"dust opacity {tau} assumed for \"{report['atmo_opacity']}\" (MODELED); no radiation alert data (MODELED). "
        f"{C.MSL_WEATHER_URL}"
    )
    start = sol_start_utc(sol, lon_east)
    hour_s = MARS_SOL_RATIO * 86400 / 24
    out = []
    for k in range(25):
        t = start + timedelta(seconds=k * hour_s)
        out.append({
            "time": t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z",
            "tempC": round(air_temp(k % 24, t_min, t_max, sunrise_h, C.REMS_MAX_TEMP_LMST), 1),
            "pressurePa": pressure,
            "dustTau": tau,
            "sunElevationDeg": round(approx_sun_elevation(lat, float(report["ls"]), k), 1),
            "radiationAlert": False,
            "source": source,
            "status": "MODELED",
        })
    return out


def convert(
    out_json: Path = C.DATA_DIR / "processed" / "gale" / "conditions.json",
    waypoints_json: Path = C.DATA_DIR / "processed" / "gale" / "waypoints.json",
    cache: Path = C.DATA_DIR / "raw" / "msl_weather.json",
    sol: int = C.MSL_WEATHER_SOL,
) -> dict:
    base = next(w for w in json.loads(Path(waypoints_json).read_text(encoding="utf-8")) if w["kind"] == "base")
    report = next((r for r in load_feed(cache) if int(r["sol"]) == sol), None)
    if report is None:
        raise ValueError(f"no REMS report for sol {sol}")
    conditions = conditions_for_sol(report, base["lat"], base["lon"])
    Path(out_json).write_text(json.dumps(conditions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"sol": sol, "date": report["terrestrial_date"], "start": conditions[0]["time"], "end": conditions[-1]["time"],
            "tempC": [report["min_temp"], report["max_temp"]], "pressurePa": report["pressure"], "file": str(out_json)}
