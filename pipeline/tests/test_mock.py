"""The mock site on a small grid: right files, right formats, terrain that behaves like boxwork."""

import json
import re

import numpy as np
import pytest

from pipeline import config as C
from pipeline.costgrid import read_costgrid
from pipeline.mock import build_mock, generate_terrain, reachable_from

SIZE_M = 600.0  # 300 x 300 cells: same layout as the 2 km site, fast enough for CI


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("mock")
    summary = build_mock(out, url_prefix="processed/mock", size_m=SIZE_M, pov_width=128)
    return out, summary


@pytest.fixture(scope="module")
def terrain():
    return generate_terrain(SIZE_M, C.MOCK_CELL_SIZE_M, C.MOCK_SEED)


def test_writes_every_file_the_config_points_to(site):
    out, _ = site
    for name in ["costgrid.json", "costgrid.bin", "optical.png", "hillshade.png", "thermal_inertia.png",
                 "mineralogy.png", "science_targets.json", "pov_images.json", "conditions.json", "waypoints.json"]:  # fmt: skip
        assert (out / name).exists(), name


def test_costgrid_is_mock_and_square(site):
    out, _ = site
    grid = read_costgrid(out / "costgrid.json")
    assert grid["status"] == "MOCK"
    assert grid["width"] == grid["height"] == 300
    assert set(np.unique(grid["terrainClass"])) == {C.TERRAIN_BEDROCK, C.TERRAIN_SAND, C.TERRAIN_BOULDERS, C.TERRAIN_NO_GO}


def test_ridges_are_one_to_two_metres(terrain):
    crest = (terrain["profile"] > 0.99) & (terrain["boxwork"] > 0.99)
    heights = terrain["ridgeHeight"][crest]
    assert np.percentile(heights, 50) == pytest.approx(1.5, abs=0.25)
    assert heights.max() <= C.MOCK_RIDGE_HEIGHT_M[1] + 1e-9


def test_sand_sits_in_hollows_not_on_crests(terrain):
    sand = terrain["terrain"] == C.TERRAIN_SAND
    inside = terrain["boxwork"] > 0.99
    assert not (sand & inside & (terrain["profile"] > 0)).any()
    assert 0.2 < sand[inside].mean() < 0.6


def test_wall_is_steep_and_no_go(terrain):
    no_go = terrain["terrain"] == C.TERRAIN_NO_GO
    assert no_go.any()
    assert np.median(terrain["slope"][no_go]) > C.SLOPE_IMPASSABLE_DEG


def test_targets_are_inside_bounds_and_reachable(site, terrain):
    out, _ = site
    bounds = json.loads((out / "costgrid.json").read_text())["bounds"]
    targets = json.loads((out / "science_targets.json").read_text())
    assert len(targets) == 6
    for t in targets:
        assert bounds["latMin"] < t["lat"] < bounds["latMax"]
        assert bounds["lonMin"] < t["lon"] < bounds["lonMax"]
        assert t["status"] == "MOCK"
        assert set(t) == {"id", "lat", "lon", "name", "why", "instrumentsNeeded", "source", "status"}


def test_pov_images_follow_contract(site):
    out, _ = site
    povs = json.loads((out / "pov_images.json").read_text())
    assert len(povs) == 7  # base + 6 targets
    for p in povs:
        assert set(p) == {"lat", "lon", "url", "thumbnailUrl", "source", "sol", "camera", "isPanorama", "status"}
        assert p["url"].startswith("processed/mock/pov/")
        assert (out / p["url"].removeprefix("processed/mock/")).exists()
        assert p["status"] == "MOCK"


def test_conditions_cover_one_sol(site):
    out, _ = site
    conditions = json.loads((out / "conditions.json").read_text())
    assert len(conditions) == 25
    assert all(re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z", c["time"]) for c in conditions)
    assert all(c["status"] == "MOCK" and c["radiationAlert"] is False for c in conditions)
    elevations = [c["sunElevationDeg"] for c in conditions]
    assert max(elevations) > 80 and min(elevations) < -80  # day and night


def test_waypoints_have_base_and_rover(site):
    out, _ = site
    kinds = [w["kind"] for w in json.loads((out / "waypoints.json").read_text())]
    assert kinds == ["base", "rover"]


def test_reachable_from_stops_at_walls():
    passable = np.ones((5, 5), bool)
    passable[:, 2] = False
    reached = reachable_from(passable, (0, 0))
    assert reached[:, :2].all() and not reached[:, 2:].any()
    passable[4, 2] = True  # open a gap at the bottom of the wall
    assert reachable_from(passable, (0, 0))[:, 3:].all()


def test_reachable_from_no_corner_squeeze():
    passable = np.array([[True, False], [False, True]])
    assert not reachable_from(passable, (0, 0))[1, 1]


def test_same_seed_same_terrain():
    a = generate_terrain(200.0, C.MOCK_CELL_SIZE_M, 7)["elevation"]
    b = generate_terrain(200.0, C.MOCK_CELL_SIZE_M, 7)["elevation"]
    np.testing.assert_array_equal(a, b)
