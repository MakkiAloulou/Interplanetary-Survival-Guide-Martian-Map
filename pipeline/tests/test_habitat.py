"""Habitat placement rule (pipeline/habitat.py) on small synthetic grids."""

import math

import numpy as np
import pytest

from pipeline import config as C
from pipeline.costgrid import bounds_from_center
from pipeline.habitat import place_habitat, rc_of

LAT, LON = -4.80, 137.38
N, CELL = 400, 2.0  # 800 m square


def grid(slope: np.ndarray) -> dict:
    return {
        "slopeDeg": slope.astype(np.float32),
        "terrainClass": np.zeros(slope.shape, np.uint8),
        "cellSizeM": CELL,
        "bounds": bounds_from_center(LAT, LON, N * CELL, N * CELL),
    }


def test_base_is_the_nearest_flat_reachable_pad_far_enough_from_the_science():
    slope = np.full((N, N), 12.0)  # walkable but too steep for a pad everywhere...
    slope[:, 300:] = 2.0  # ...except a flat strip in the east
    g = grid(slope)
    base, rover = place_habitat(g, (LAT, LON))
    r, c = rc_of(g["bounds"], (N, N), base["lat"], base["lon"])
    sr, sc = rc_of(g["bounds"], (N, N), LAT, LON)
    pad = round(C.HABITAT_PAD_RADIUS_M / CELL)
    assert (slope[r - pad : r + pad + 1, c - pad : c + pad + 1] < C.HABITAT_PAD_MAX_SLOPE_DEG).all()
    dist = math.hypot(r - sr, c - sc) * CELL
    assert dist >= C.HABITAT_MIN_DISTANCE_FROM_SCIENCE_M
    assert c >= 300 + pad  # inside the flat strip, a full pad radius from its edge
    # The nearest qualifying cell lies on the minimum-distance circle, not farther out.
    assert dist == pytest.approx(C.HABITAT_MIN_DISTANCE_FROM_SCIENCE_M, abs=2 * CELL)
    assert rover["lat"] == base["lat"] and rover["lon"] > base["lon"]
    assert (base["kind"], rover["kind"]) == ("base", "rover")


def test_a_pad_cut_off_by_a_cliff_is_not_used():
    slope = np.full((N, N), 12.0)
    slope[:, 300:] = 2.0
    slope[:40, :290] = 2.0  # a second flat strip along the north edge, on the science side
    slope[:, 290:295] = 40.0  # impassable wall, full height, between the science and the east strip
    g = grid(slope)
    base, _ = place_habitat(g, (LAT, LON))
    r, c = rc_of(g["bounds"], (N, N), base["lat"], base["lon"])
    assert r < 40 and c < 290


def test_no_pad_raises():
    with pytest.raises(RuntimeError):
        place_habitat(grid(np.full((N, N), 12.0)), (LAT, LON))
