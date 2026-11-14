"""Place the habitat and the parked rover on a real CostGrid with a stated rule (MODELED; constants in config.py).

Rule: the nearest cell to the science centre that (1) sits at least HABITAT_MIN_DISTANCE_FROM_SCIENCE_M from it,
(2) has a pad of HABITAT_PAD_RADIUS_M where every cell is passable and under HABITAT_PAD_MAX_SLOPE_DEG, and
(3) is reachable on foot from the science centre.
"""

import math

import numpy as np

from pipeline import config as C
from pipeline.costgrid import cell_center_latlon
from pipeline.mock import reachable_from


def _all_true_in_box(ok: np.ndarray, r: int) -> np.ndarray:
    """True where every cell of the (2r+1)² box around it is True (summed-area table); False near the edges."""
    s = np.pad(ok.astype(np.int32).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
    h, w = ok.shape
    out = np.zeros_like(ok)
    k = 2 * r + 1
    if h < k or w < k:
        return out
    total = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
    out[r : h - r, r : w - r] = total == k * k
    return out


def rc_of(bounds: dict, shape: tuple[int, int], lat: float, lon: float) -> tuple[int, int]:
    h, w = shape
    r = int((bounds["latMax"] - lat) / (bounds["latMax"] - bounds["latMin"]) * h)
    c = int((lon - bounds["lonMin"]) / (bounds["lonMax"] - bounds["lonMin"]) * w)
    return min(max(r, 0), h - 1), min(max(c, 0), w - 1)


def place_habitat(grid: dict, science: tuple[float, float] = C.GALE_SCIENCE_CENTER) -> list[dict]:
    """Waypoint[] (base + rover) for the grid, or raises when no cell fits the rule."""
    slope, terrain, cell = grid["slopeDeg"], grid["terrainClass"], grid["cellSizeM"]
    shape = slope.shape
    passable = (slope < C.SLOPE_IMPASSABLE_DEG) & (terrain != C.TERRAIN_NO_GO)
    sr, sc = rc_of(grid["bounds"], shape, *science)
    # Start the reachability flood from the nearest passable cell to the science centre.
    if not passable[sr, sc]:
        rr, cc = np.nonzero(passable)
        k = np.argmin((rr - sr) ** 2 + (cc - sc) ** 2)
        sr, sc = int(rr[k]), int(cc[k])
    reachable = reachable_from(passable, (sr, sc))

    pad = _all_true_in_box(passable & (slope < C.HABITAT_PAD_MAX_SLOPE_DEG), round(C.HABITAT_PAD_RADIUS_M / cell))
    rows, cols = np.indices(shape)
    dist = np.hypot(rows - sr, cols - sc) * cell
    candidates = pad & reachable & (dist >= C.HABITAT_MIN_DISTANCE_FROM_SCIENCE_M)
    if not candidates.any():
        raise RuntimeError("no cell fits the habitat rule (flat pad, reachable, far enough from the science)")
    k = np.argmin(np.where(candidates, dist, np.inf))
    br, bc = divmod(int(k), shape[1])
    lat, lon = cell_center_latlon(grid["bounds"], shape, br, bc)
    m_per_deg_lon = 2 * math.pi * C.MARS_EQUATORIAL_RADIUS_M / 360 * math.cos(math.radians(lat))
    return [
        {"id": "base", "lat": round(lat, 7), "lon": round(lon, 7), "kind": "base", "name": "Habitat"},
        {"id": "rover", "lat": round(lat, 7), "lon": round(lon + C.ROVER_OFFSET_EAST_M / m_per_deg_lon, 7), "kind": "rover", "name": "Support rover (parked)"},
    ]
