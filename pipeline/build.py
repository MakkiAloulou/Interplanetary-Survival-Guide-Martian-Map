"""Phase 8: a real elevation model (GeoTIFF) → CostGrid + overlay PNGs, in exactly the format of the Phase 2 mock.

    python -m pipeline build --dem <geotiff> --bbox <lonmin,latmin,lonmax,latmax> --out data/processed/<name>/

The DEM is warped (bilinear) onto a grid of square cells of --cell-size metres covering the bounding box, in Mars
geographic coordinates (sphere of the equatorial radius, as the app's map projection). Slope uses that true metre
cell size. Terrain classes come from optional mask rasters, each classified by a threshold
(e.g. ``--sand thermal_inertia.tif:<300`` or ``--boulders rocks.tif:>0``); cells the DEM does not cover are NO_GO,
because nobody walks across ground nobody has measured.
"""

import json
import math
import operator
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.transform import from_bounds
from rasterio.warp import Resampling, reproject

from pipeline import config as C
from pipeline.costgrid import write_costgrid
from pipeline.png import write_png
from pipeline.terrain import hillshade, slope_deg

# Planetocentric longitude/latitude on the Mars sphere used by the app's map (CLAUDE.md §5).
MARS_GEOGRAPHIC = CRS.from_proj4(f"+proj=longlat +R={C.MARS_EQUATORIAL_RADIUS_M:.0f} +no_defs")

_OPS = {"<": operator.lt, "<=": operator.le, ">": operator.gt, ">=": operator.ge}


def parse_bbox(text: str) -> tuple[float, float, float, float]:
    """'lonmin,latmin,lonmax,latmax' → floats, checked."""
    parts = [float(v) for v in text.split(",")]
    if len(parts) != 4:
        raise ValueError("--bbox needs four numbers: lonmin,latmin,lonmax,latmax")
    lonmin, latmin, lonmax, latmax = parts
    if not (lonmin < lonmax and latmin < latmax and -90 <= latmin and latmax <= 90):
        raise ValueError(f"--bbox is not a valid box: {text}")
    return lonmin, latmin, lonmax, latmax


def parse_mask(spec: str) -> tuple[Path, str, float]:
    """'path[:<op><value>]' with op one of < <= > >=; default '>0' (a 0/1 mask)."""
    path, sep, rule = spec.rpartition(":")
    if not sep or not rule or rule[0] not in "<>":
        return Path(spec), ">", 0.0
    op = rule[:2] if rule[:2] in _OPS else rule[:1]
    return Path(path), op, float(rule[len(op):])


def target_grid(bbox: tuple[float, float, float, float], cell_size_m: float) -> dict:
    """Square cells of cell_size_m covering the bbox, keeping its centre; returns width, height, bounds, transform."""
    lonmin, latmin, lonmax, latmax = bbox
    m_per_deg = 2 * math.pi * C.MARS_EQUATORIAL_RADIUS_M / 360
    lat_c, lon_c = (latmin + latmax) / 2, (lonmin + lonmax) / 2
    m_per_deg_lon = m_per_deg * math.cos(math.radians(lat_c))
    height = max(1, round((latmax - latmin) * m_per_deg / cell_size_m))
    width = max(1, round((lonmax - lonmin) * m_per_deg_lon / cell_size_m))
    half_lat = height * cell_size_m / m_per_deg / 2
    half_lon = width * cell_size_m / m_per_deg_lon / 2
    bounds = {
        "latMin": round(lat_c - half_lat, 7),
        "latMax": round(lat_c + half_lat, 7),
        "lonMin": round(lon_c - half_lon, 7),
        "lonMax": round(lon_c + half_lon, 7),
    }
    transform = from_bounds(bounds["lonMin"], bounds["latMin"], bounds["lonMax"], bounds["latMax"], width, height)
    return {"width": width, "height": height, "bounds": bounds, "transform": transform}


def warp_to_grid(path: Path, grid: dict, resampling: Resampling) -> np.ndarray:
    """Band 1 of a raster warped onto the target grid; cells it does not cover (or nodata) are NaN."""
    out = np.full((grid["height"], grid["width"]), np.nan, dtype=np.float32)
    with rasterio.open(path) as src:
        if src.crs is None:
            raise ValueError(f"{path} has no coordinate reference system")
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            src_nodata=src.nodata,
            dst_transform=grid["transform"],
            dst_crs=MARS_GEOGRAPHIC,
            dst_nodata=np.nan,
            resampling=resampling,
        )
    return out


def build(
    dem: Path,
    bbox: tuple[float, float, float, float],
    out_dir: Path,
    cell_size_m: float = C.MOCK_CELL_SIZE_M,
    sand: str | None = None,
    boulders: str | None = None,
    source: str = "",
) -> dict:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    grid = target_grid(bbox, cell_size_m)

    elevation = warp_to_grid(Path(dem), grid, Resampling.bilinear)
    missing = ~np.isfinite(elevation)
    if missing.all():
        raise ValueError(f"{dem} does not cover the bounding box {bbox}")
    # Fill holes before differencing so they do not spread NaN into the slope of their neighbours; the holes
    # themselves become NO_GO below.
    elevation[missing] = float(np.nanmean(elevation))
    slope = slope_deg(elevation, cell_size_m)

    terrain = np.full(elevation.shape, C.TERRAIN_BEDROCK, np.uint8)
    for spec, code in ((sand, C.TERRAIN_SAND), (boulders, C.TERRAIN_BOULDERS)):
        if spec:
            path, op, value = parse_mask(spec)
            mask = warp_to_grid(path, grid, Resampling.nearest)
            terrain[np.isfinite(mask) & _OPS[op](np.nan_to_num(mask, nan=0.0), value)] = code
    terrain[missing] = C.TERRAIN_NO_GO

    # Elevation and slope come from stereo photogrammetry: DERIVED. Classes from thresholds on masks are our call.
    array_status = {"elevation": "DERIVED", "slopeDeg": "DERIVED", "terrainClass": "MODELED" if (sand or boulders) else "DERIVED"}
    write_costgrid(
        out_dir / "costgrid.json",
        elevation.astype(np.float32),
        slope,
        terrain,
        cell_size_m,
        grid["bounds"],
        "DERIVED",
        source or f"Built by pipeline/build.py from {Path(dem).name}",
        array_status=array_status,
    )
    write_png(out_dir / "hillshade.png", (hillshade(elevation, cell_size_m) * 255).astype(np.uint8))

    total = terrain.size
    summary = {
        "cells": f"{grid['width']} x {grid['height']} @ {cell_size_m} m",
        "bounds": grid["bounds"],
        "elevationRangeM": (round(float(elevation[~missing].min()), 1), round(float(elevation[~missing].max()), 1)),
        "fraction": {
            "noData": round(float(missing.sum() / total), 3),
            "sand": round(float((terrain == C.TERRAIN_SAND).sum() / total), 3),
            "boulders": round(float((terrain == C.TERRAIN_BOULDERS).sum() / total), 3),
            "slopeImpassable": round(float((slope >= C.SLOPE_IMPASSABLE_DEG).sum() / total), 3),
        },
        "arrayStatus": array_status,
    }
    (out_dir / "build.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary
