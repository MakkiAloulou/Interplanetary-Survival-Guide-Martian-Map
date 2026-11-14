"""Gale DEM converter, on a local synthetic GeoTIFF standing in for the remote USGS file (no network in tests)."""

import json

import numpy as np
import rasterio

from pipeline.costgrid import read_costgrid
from pipeline.sources.gale_dem import clip, convert
from pipeline.tests.test_build import PIXEL_M, SIZE_M, bbox_m, plane, write_raster


def test_clip_keeps_pixels_and_georeferencing(tmp_path):
    values = plane(0.05, 0.02)
    write_raster(tmp_path / "big.tif", values)
    out = clip(str(tmp_path / "big.tif"), bbox_m(100), tmp_path / "raw" / "site.tif", margin_m=20)
    with rasterio.open(tmp_path / "big.tif") as big, rasterio.open(tmp_path / "raw" / "site.tif") as small:
        # ~240 m square (±100 m + 20 m margin) at 1 m pixels, cut from the centre of the 600 m raster.
        assert abs(small.width - 240) <= 2 and abs(small.height - 240) <= 2
        assert small.crs == big.crs and small.res == big.res
        col, row, *_ = out["window"]
        np.testing.assert_array_equal(small.read(1), values[row : row + small.height, col : col + small.width].astype("float32"))
        # Same ground point, same pixel value, in both files.
        x, y = small.xy(10, 10)
        assert next(big.sample([(x, y)]))[0] == small.read(1)[10, 10]


def test_clip_is_limited_to_the_source(tmp_path):
    write_raster(tmp_path / "big.tif", plane(0.0, 0.0))
    clip(str(tmp_path / "big.tif"), bbox_m(SIZE_M), tmp_path / "site.tif", margin_m=50)  # box larger than the DEM
    with rasterio.open(tmp_path / "site.tif") as small:
        assert (small.width, small.height) == (int(SIZE_M / PIXEL_M), int(SIZE_M / PIXEL_M))


def test_convert_builds_a_cost_grid_and_caches_the_clip(tmp_path):
    write_raster(tmp_path / "big.tif", plane(0.1, 0.0))
    raw = tmp_path / "raw" / "site.tif"
    lonmin, latmin, *_ = bbox_m(280)
    science = (latmin + 0.0005, lonmin + 0.0005)  # south-west corner, so a pad 300 m away fits in the box
    first = convert(tmp_path / "out", raw, bbox_m(280), src=str(tmp_path / "big.tif"), science=science)
    grid = read_costgrid(tmp_path / "out" / "costgrid.json")
    assert (grid["width"], grid["height"]) == (280, 280)  # 560 m at the app's 2 m cells
    assert [w["kind"] for w in json.loads((tmp_path / "out" / "waypoints.json").read_text())] == ["base", "rover"]
    assert "USGS MSL Gale Merged DEM" in grid["source"]
    assert first["clip"] != "cached"
    assert convert(tmp_path / "out", raw, bbox_m(280), src=str(tmp_path / "missing.tif"), science=science)["clip"] == "cached"
