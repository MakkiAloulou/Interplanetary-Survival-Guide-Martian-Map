"""Curiosity boxwork campaign → ScienceTarget[] for the site (CLAUDE.md §8, science-targets slot).

    python -m pipeline msl-targets        # writes data/processed/gale/science_targets.json

Each curated stop (pipeline/sources/msl_boxwork_targets.json) is placed where Curiosity stood on its sol: the last
MMGIS waypoint on or before that sol. A stop the habitat cannot reach on foot moves to the nearest reachable cell within
TARGET_MAX_SNAP_M (and says so); farther than that, or outside the site, it is dropped with a reason.
"""

import json
import math
import urllib.request
from pathlib import Path

import numpy as np

from pipeline import config as C
from pipeline.costgrid import cell_center_latlon, read_costgrid
from pipeline.habitat import rc_of
from pipeline.mock import reachable_from

CURATED = Path(__file__).with_name("msl_boxwork_targets.json")


def load_waypoints(cache: Path, url: str = C.MSL_WAYPOINTS_URL) -> list[dict]:
    """MMGIS waypoint properties, downloaded once into cache."""
    cache = Path(cache)
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "martian-map-pipeline"})
        cache.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    features = json.loads(cache.read_text(encoding="utf-8"))["features"]
    return sorted((f["properties"] for f in features), key=lambda p: (p["sol"], p["dist_total_m"]))


def position_on_sol(waypoints: list[dict], sol: int) -> dict:
    """The last waypoint reached on or before sol (where the rover stood that sol)."""
    before = [w for w in waypoints if w["sol"] <= sol]
    if not before:
        raise ValueError(f"no waypoint on or before sol {sol}")
    return before[-1]


def place_targets(grid: dict, base: dict, curated: list[dict], waypoints: list[dict]) -> tuple[list[dict], list[str]]:
    """(ScienceTarget[], dropped reasons) for the curated stops on this grid."""
    slope, terrain, cell, bounds = grid["slopeDeg"], grid["terrainClass"], grid["cellSizeM"], grid["bounds"]
    passable = (slope < C.SLOPE_IMPASSABLE_DEG) & (terrain != C.TERRAIN_NO_GO)
    reach = reachable_from(passable, rc_of(bounds, slope.shape, base["lat"], base["lon"]))
    rr, cc = np.nonzero(reach)
    targets, dropped = [], []
    for t in curated:
        w = position_on_sol(waypoints, t["sol"])
        lat, lon = w["lat"], w["lon"]
        if not (bounds["latMin"] <= lat <= bounds["latMax"] and bounds["lonMin"] <= lon <= bounds["lonMax"]):
            dropped.append(f"{t['id']}: rover position on sol {t['sol']} is outside the site")
            continue
        r, c = rc_of(bounds, slope.shape, lat, lon)
        note = ""
        if not reach[r, c]:
            k = int(np.argmin((rr - r) ** 2 + (cc - c) ** 2))
            lat, lon = cell_center_latlon(bounds, slope.shape, int(rr[k]), int(cc[k]))
            # true distance from the rover position to the new stop (not grid steps), as the app measures it
            m_per_deg = 2 * math.pi * C.MARS_MEAN_RADIUS_M / 360
            snap_m = math.hypot((lat - w["lat"]) * m_per_deg, (lon - w["lon"]) * m_per_deg * math.cos(math.radians(lat)))
            if snap_m > C.TARGET_MAX_SNAP_M:
                dropped.append(f"{t['id']}: nearest walkable ground is {snap_m:.0f} m from the rover position")
                continue
            note = f" The rover stood on ground too steep to walk (slope {slope[r, c]:.0f}°); this stop is {snap_m:.0f} m away on walkable ground."
        targets.append({
            "id": t["id"],
            "lat": round(float(lat), 7),
            "lon": round(float(lon), 7),
            "name": t["name"],
            "why": t["why"] + note,
            "instrumentsNeeded": t["instrumentsNeeded"],
            "source": (
                f"Curiosity (NASA/JPL-Caltech): rover position on sol {w['sol']} (MMGIS waypoint, site {w['site']}, "
                f"drive {w['drive']}). Reports: {' '.join(t['sources'])}. Kit: our suited-crew equivalent (MODELED)."
            ),
            "status": "DERIVED",
        })
    return targets, dropped


def convert(
    grid_json: Path = C.DATA_DIR / "processed" / "gale" / "costgrid.json",
    waypoints_json: Path = C.DATA_DIR / "processed" / "gale" / "waypoints.json",
    out_json: Path = C.DATA_DIR / "processed" / "gale" / "science_targets.json",
    cache: Path = C.DATA_DIR / "raw" / "MSL_waypoints.json",
    curated: Path = CURATED,
) -> dict:
    base = next(w for w in json.loads(Path(waypoints_json).read_text(encoding="utf-8")) if w["kind"] == "base")
    stops = json.loads(Path(curated).read_text(encoding="utf-8"))["targets"]
    targets, dropped = place_targets(read_costgrid(grid_json), base, stops, load_waypoints(cache))
    Path(out_json).write_text(json.dumps(targets, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"targets": [t["id"] for t in targets], "dropped": dropped, "file": str(out_json)}
