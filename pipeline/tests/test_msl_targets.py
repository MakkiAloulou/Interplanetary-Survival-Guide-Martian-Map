"""Curiosity boxwork stops (pipeline/sources/msl_targets.py) on a small synthetic grid, no network."""

import json

import numpy as np
import pytest

from pipeline import config as C
from pipeline.costgrid import bounds_from_center, cell_center_latlon
from pipeline.sources.msl_targets import CURATED, place_targets, position_on_sol

LAT, LON, N, CELL = -4.80, 137.38, 100, 2.0  # 200 m square
BOUNDS = bounds_from_center(LAT, LON, N * CELL, N * CELL)


def grid(slope):
    return {"slopeDeg": slope.astype(np.float32), "terrainClass": np.zeros(slope.shape, np.uint8), "cellSizeM": CELL, "bounds": BOUNDS}


def at(r, c):
    return cell_center_latlon(BOUNDS, (N, N), r, c)


def wp(sol, r, c, site=1, dist=0.0):
    lat, lon = at(r, c)
    return {"sol": sol, "lat": lat, "lon": lon, "site": site, "drive": 0, "dist_total_m": dist}


def stop(id_, sol):
    return {"id": id_, "name": id_, "sol": sol, "why": "Why.", "instrumentsNeeded": ["hand lens imager"], "sources": ["https://example.org/report"]}


BASE = dict(zip(("lat", "lon"), at(50, 5)))


def test_position_on_sol_is_the_last_waypoint_on_or_before_it():
    wps = [wp(10, 1, 1, dist=0), wp(12, 2, 2, dist=5), wp(12, 3, 3, dist=9), wp(20, 4, 4, dist=15)]
    assert position_on_sol(wps, 12) is wps[2]  # last drive of sol 12
    assert position_on_sol(wps, 19) is wps[2]  # parked between drives
    with pytest.raises(ValueError):
        position_on_sol(wps, 9)


def test_reachable_stop_keeps_the_rover_position():
    targets, dropped = place_targets(grid(np.full((N, N), 5.0)), BASE, [stop("a", 10)], [wp(10, 50, 60)])
    assert dropped == []
    assert (targets[0]["lat"], targets[0]["lon"]) == at(50, 60)
    assert targets[0]["status"] == "DERIVED" and "sol 10" in targets[0]["source"]


def test_stop_on_a_steep_wall_moves_to_walkable_ground_and_says_so():
    slope = np.full((N, N), 5.0)
    slope[48:53, 58:63] = 35.0  # a small steep knob around the rover position
    targets, dropped = place_targets(grid(slope), BASE, [stop("a", 10)], [wp(10, 50, 60)])
    assert dropped == []
    assert (targets[0]["lat"], targets[0]["lon"]) != at(50, 60)
    assert "too steep to walk" in targets[0]["why"] and "6 m away" in targets[0]["why"]


def test_unreachable_or_outside_stops_are_dropped_with_a_reason():
    slope = np.full((N, N), 5.0)
    slope[:, 30:45] = 40.0  # a 30 m impassable band cuts the east off from the base
    stops = [stop("cut-off", 10), stop("outside", 11)]
    far = {"sol": 11, "lat": LAT + 1.0, "lon": LON, "site": 1, "drive": 0, "dist_total_m": 1.0}
    targets, dropped = place_targets(grid(slope), BASE, stops, [wp(10, 50, 60), far])  # east side: 62 m from reachable ground
    assert targets == []
    assert any(d.startswith("cut-off") and "walkable" in d for d in dropped)
    assert any(d.startswith("outside") for d in dropped)


def test_curated_file_is_complete():
    curated = json.loads(CURATED.read_text(encoding="utf-8"))["targets"]
    ids = [t["id"] for t in curated]
    assert len(ids) == len(set(ids))
    for t in curated:
        assert t["why"] and t["instrumentsNeeded"] and t["sources"] and isinstance(t["sol"], int)
        assert all(u.startswith("https://") for u in t["sources"])
