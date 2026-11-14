"""Phase 8 pipeline on small synthetic GeoTIFFs in a Mars equirectangular projection, like a HiRISE DTM."""

import math

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_origin

from pipeline import config as C
from pipeline.__main__ import main
from pipeline.build import build, parse_bbox, parse_mask, target_grid
from pipeline.costgrid import read_costgrid

LAT0, LON0 = -4.80, 137.38
R = C.MARS_EQUATORIAL_RADIUS_M
# Equidistant cylindrical, true scale at the site latitude (as HiRISE DTMs of low-latitude sites are).
EQC = CRS.from_proj4(f"+proj=eqc +lat_ts={LAT0} +lon_0=0 +R={R:.0f} +units=m +no_defs")
M_PER_DEG = 2 * math.pi * R / 360
SIZE_M = 600.0  # DEM side
PIXEL_M = 1.0


def eqc_xy(lat: float, lon: float) -> tuple[float, float]:
    return R * math.cos(math.radians(LAT0)) * math.radians(lon), R * math.radians(lat)


def write_raster(path, values: np.ndarray, nodata=None):
    """A square raster centred on the site, 1 m pixels, row 0 at the north."""
    x0, y0 = eqc_xy(LAT0, LON0)
    transform = from_origin(x0 - SIZE_M / 2, y0 + SIZE_M / 2, PIXEL_M, PIXEL_M)
    with rasterio.open(
        path, "w", driver="GTiff", width=values.shape[1], height=values.shape[0], count=1,
        dtype="float32", crs=EQC, transform=transform, nodata=nodata,
    ) as dst:  # fmt: skip
        dst.write(values.astype("float32"), 1)


def plane(gx: float, gy: float) -> np.ndarray:
    """Elevation rising gx m/m to the east and gy m/m to the north, around -3700 m."""
    n = int(SIZE_M / PIXEL_M)
    x = (np.arange(n) + 0.5) * PIXEL_M
    y = (np.arange(n)[::-1] + 0.5) * PIXEL_M
    return -3700.0 + gx * x[None, :] + gy * y[:, None]


def bbox_m(half_m: float) -> tuple[float, float, float, float]:
    """A bbox of ±half_m metres around the site, in degrees."""
    dlat = half_m / M_PER_DEG
    dlon = half_m / (M_PER_DEG * math.cos(math.radians(LAT0)))
    return LON0 - dlon, LAT0 - dlat, LON0 + dlon, LAT0 + dlat


def test_parse_bbox_and_masks():
    assert parse_bbox("137.3,-4.9,137.4,-4.7") == (137.3, -4.9, 137.4, -4.7)
    with pytest.raises(ValueError):
        parse_bbox("137.4,-4.9,137.3,-4.7")
    assert parse_mask("ti.tif:<300") == (parse_mask("ti.tif")[0], "<", 300.0)
    assert parse_mask("rocks.tif") [1:] == (">", 0.0)
    assert parse_mask("C:/data/rocks.tif:>=2")[1:] == (">=", 2.0)


def test_target_grid_has_square_metre_cells():
    g = target_grid(bbox_m(200), 2.0)
    b = g["bounds"]
    assert (g["width"], g["height"]) == (200, 200)
    dy = (b["latMax"] - b["latMin"]) * M_PER_DEG / g["height"]
    dx = (b["lonMax"] - b["lonMin"]) * M_PER_DEG * math.cos(math.radians((b["latMin"] + b["latMax"]) / 2)) / g["width"]
    assert dy == pytest.approx(2.0, abs=1e-3)
    assert dx == pytest.approx(2.0, abs=1e-3)


def test_tilted_plane_gives_its_true_slope(tmp_path):
    gx, gy = 0.10, 0.05
    write_raster(tmp_path / "dem.tif", plane(gx, gy))
    summary = build(tmp_path / "dem.tif", bbox_m(200), tmp_path / "out", cell_size_m=2.0)
    grid = read_costgrid(tmp_path / "out" / "costgrid.json")

    interior = grid["slopeDeg"][5:-5, 5:-5]
    assert np.median(interior) == pytest.approx(math.degrees(math.atan(math.hypot(gx, gy))), abs=0.3)
    # Rising to the east and north: west-to-east and south-to-north differences have the right signs and sizes.
    e = grid["elevation"]
    assert (e[100, 150] - e[100, 50]) == pytest.approx(gx * 200, rel=0.02)
    assert (e[50, 100] - e[150, 100]) == pytest.approx(gy * 200, rel=0.02)
    assert summary["fraction"]["noData"] == 0


def test_output_matches_the_phase_2_format(tmp_path):
    write_raster(tmp_path / "dem.tif", plane(0.02, 0.0))
    build(tmp_path / "dem.tif", bbox_m(100), tmp_path / "out", cell_size_m=2.0, source="test DEM")
    grid = read_costgrid(tmp_path / "out" / "costgrid.json")
    assert grid["status"] == "DERIVED"
    # No masks: every measured cell is assumed bedrock, which is MODELED, not DERIVED.
    assert grid["arrayStatus"] == {"elevation": "DERIVED", "slopeDeg": "DERIVED", "terrainClass": "MODELED"}
    assert grid["source"] == "test DEM"
    assert grid["elevation"].dtype == np.dtype("<f4") and grid["terrainClass"].dtype == np.uint8
    assert np.isfinite(grid["elevation"]).all() and (grid["slopeDeg"] < 90).all()
    assert (tmp_path / "out" / "hillshade.png").read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    assert (tmp_path / "out" / "build.json").exists()


def test_masks_classify_sand_and_boulders(tmp_path):
    write_raster(tmp_path / "dem.tif", plane(0.0, 0.0))
    n = int(SIZE_M / PIXEL_M)
    ti = np.full((n, n), 600.0)
    ti[:, : n // 2] = 200.0  # west half: low thermal inertia = sand
    rocks = np.zeros((n, n))
    rocks[: n // 4, :] = 1.0  # north quarter: boulders (wins over sand)
    write_raster(tmp_path / "ti.tif", ti)
    write_raster(tmp_path / "rocks.tif", rocks)
    build(tmp_path / "dem.tif", bbox_m(200), tmp_path / "out", 2.0, sand=f"{tmp_path / 'ti.tif'}:<300", boulders=str(tmp_path / "rocks.tif"))
    grid = read_costgrid(tmp_path / "out" / "costgrid.json")
    t = grid["terrainClass"]
    assert t[150, 20] == C.TERRAIN_SAND  # south-west
    assert t[150, 180] == C.TERRAIN_BEDROCK  # south-east
    assert t[10, 20] == C.TERRAIN_BOULDERS  # north-west: boulders mask applied after sand
    assert grid["arrayStatus"]["terrainClass"] == "MODELED"


def test_cells_without_elevation_are_no_go(tmp_path):
    dem = plane(0.0, 0.0)
    dem[:, :150] = -9999.0  # western 150 m of the 600 m DEM not measured
    write_raster(tmp_path / "dem.tif", dem, nodata=-9999.0)
    summary = build(tmp_path / "dem.tif", bbox_m(200), tmp_path / "out", 2.0)
    grid = read_costgrid(tmp_path / "out" / "costgrid.json")
    # The grid spans ±200 m, so the hole covers its western 50 m = 25 cells.
    assert (grid["terrainClass"][:, :24] == C.TERRAIN_NO_GO).all()
    assert (grid["terrainClass"][:, 27:] == C.TERRAIN_BEDROCK).all()
    assert np.isfinite(grid["elevation"]).all()
    assert summary["fraction"]["noData"] > 0.1


def test_bbox_outside_the_dem_is_an_error(tmp_path):
    write_raster(tmp_path / "dem.tif", plane(0.0, 0.0))
    far = (LON0 + 1, LAT0 + 1, LON0 + 1.01, LAT0 + 1.01)
    with pytest.raises(ValueError, match="does not cover"):
        build(tmp_path / "dem.tif", far, tmp_path / "out", 2.0)


def test_cli_build(tmp_path, capsys):
    write_raster(tmp_path / "dem.tif", plane(0.03, 0.0))
    b = bbox_m(80)
    code = main(["build", "--dem", str(tmp_path / "dem.tif"), "--bbox", ",".join(map(str, b)), "--out", str(tmp_path / "out")])
    assert code == 0
    assert '"cells": "80 x 80 @ 2.0 m"' in capsys.readouterr().out
    assert (tmp_path / "out" / "costgrid.bin").stat().st_size == 9 * 80 * 80
