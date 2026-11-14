import json
import math

import numpy as np
import pytest

from pipeline import config
from pipeline.costgrid import bounds_from_center, cell_center_latlon, read_costgrid, write_costgrid

BOUNDS = {"latMin": -1.0, "latMax": 1.0, "lonMin": 10.0, "lonMax": 13.0}


def test_round_trip_and_byte_layout(tmp_path):
    elevation = np.array([[-3700.0, -3701.5, 0.25], [1.0, 2.0, 3.0]], np.float32)
    slope = np.array([[0.0, 12.5, 30.0], [0.0, 1.0, 2.0]], np.float32)
    terrain = np.array([[0, 1, 2], [3, 0, 1]], np.uint8)
    write_costgrid(tmp_path / "g.json", elevation, slope, terrain, 2.0, BOUNDS, "MOCK", "test")

    raw = (tmp_path / "g.bin").read_bytes()
    assert len(raw) == 9 * 6
    assert np.frombuffer(raw[:4], "<f4")[0] == -3700.0  # little-endian, row-major from the north-west corner
    assert raw[48:] == bytes([0, 1, 2, 3, 0, 1])

    meta = json.loads((tmp_path / "g.json").read_text())
    assert meta == {"width": 3, "height": 2, "cellSizeM": 2.0, "bounds": BOUNDS, "binary": "g.bin", "status": "MOCK", "source": "test"}

    back = read_costgrid(tmp_path / "g.json")
    np.testing.assert_array_equal(back["elevation"], elevation)
    np.testing.assert_array_equal(back["slopeDeg"], slope)
    np.testing.assert_array_equal(back["terrainClass"], terrain)


def test_rejects_bad_input(tmp_path):
    ok = np.zeros((2, 2), np.float32)
    with pytest.raises(ValueError):
        write_costgrid(tmp_path / "g.json", ok, ok, np.full((2, 2), 4, np.uint8), 2.0, BOUNDS, "MOCK", "t")
    with pytest.raises(ValueError):
        write_costgrid(tmp_path / "g.json", ok, ok, np.zeros((2, 2), np.uint8), 2.0, BOUNDS, "REAL", "t")
    with pytest.raises(ValueError):
        write_costgrid(tmp_path / "g.json", ok, np.zeros((3, 2), np.float32), np.zeros((2, 2), np.uint8), 2.0, BOUNDS, "MOCK", "t")


def test_bounds_from_center_spans_requested_metres():
    b = bounds_from_center(-4.8, 137.38, 2000, 1000)
    m_per_deg = 2 * math.pi * config.MARS_EQUATORIAL_RADIUS_M / 360
    assert (b["latMax"] - b["latMin"]) * m_per_deg == pytest.approx(1000, abs=0.2)
    assert (b["lonMax"] - b["lonMin"]) * m_per_deg * math.cos(math.radians(-4.8)) == pytest.approx(2000, abs=0.2)
    assert (b["latMin"] + b["latMax"]) / 2 == pytest.approx(-4.8, abs=1e-6)


def test_cell_center_latlon_corners():
    assert cell_center_latlon(BOUNDS, (2, 3), 0, 0) == (0.5, 10.5)  # north-west cell
    assert cell_center_latlon(BOUNDS, (2, 3), 1, 2) == (-0.5, 12.5)  # south-east cell
