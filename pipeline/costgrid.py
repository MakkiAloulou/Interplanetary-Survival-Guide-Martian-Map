"""CostGrid on disk: <name>.json (CostGridMeta) + <name>.bin. Layout is defined in app/src/types.ts."""

import json
import math
from pathlib import Path

import numpy as np

from pipeline import config


def bounds_from_center(lat: float, lon: float, width_m: float, height_m: float) -> dict:
    """Equirectangular bounds of a width x height box centred on (lat, lon), using the equatorial radius (map projection)."""
    m_per_deg_lat = 2 * math.pi * config.MARS_EQUATORIAL_RADIUS_M / 360
    half_lat = height_m / m_per_deg_lat / 2
    half_lon = width_m / (m_per_deg_lat * math.cos(math.radians(lat))) / 2
    return {
        "latMin": round(lat - half_lat, 6),
        "latMax": round(lat + half_lat, 6),
        "lonMin": round(lon - half_lon, 6),
        "lonMax": round(lon + half_lon, 6),
    }


def cell_center_latlon(bounds: dict, shape: tuple[int, int], row: int, col: int) -> tuple[float, float]:
    """Latitude/longitude of a cell centre. Row 0 = latMax, column 0 = lonMin."""
    height, width = shape
    lat = bounds["latMax"] - (row + 0.5) * (bounds["latMax"] - bounds["latMin"]) / height
    lon = bounds["lonMin"] + (col + 0.5) * (bounds["lonMax"] - bounds["lonMin"]) / width
    return round(lat, 7), round(lon, 7)


def write_costgrid(
    json_path: Path,
    elevation: np.ndarray,
    slope_deg: np.ndarray,
    terrain_class: np.ndarray,
    cell_size_m: float,
    bounds: dict,
    status: str,
    source: str,
    array_status: dict | None = None,
) -> None:
    if not (elevation.shape == slope_deg.shape == terrain_class.shape and elevation.ndim == 2):
        raise ValueError("elevation, slope_deg and terrain_class must be 2-D arrays of the same shape")
    if terrain_class.min() < config.TERRAIN_BEDROCK or terrain_class.max() > config.TERRAIN_NO_GO:
        raise ValueError("terrain_class codes must be 0..3")
    if status not in config.DATA_STATUSES:
        raise ValueError(f"unknown status {status!r}")

    json_path = Path(json_path)
    bin_path = json_path.with_suffix(".bin")
    with open(bin_path, "wb") as f:
        f.write(elevation.astype("<f4").tobytes())
        f.write(slope_deg.astype("<f4").tobytes())
        f.write(terrain_class.astype("u1").tobytes())

    height, width = elevation.shape
    meta = {
        "width": width,
        "height": height,
        "cellSizeM": cell_size_m,
        "bounds": bounds,
        "binary": bin_path.name,
        "status": status,
        "source": source,
    }
    if array_status:
        meta["arrayStatus"] = array_status
    json_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")


def read_costgrid(json_path: Path) -> dict:
    """Metadata dict plus 'elevation', 'slopeDeg', 'terrainClass' arrays of shape (height, width)."""
    json_path = Path(json_path)
    meta = json.loads(json_path.read_text(encoding="utf-8"))
    raw = (json_path.parent / meta["binary"]).read_bytes()
    shape = (meta["height"], meta["width"])
    n = shape[0] * shape[1]
    if len(raw) != 9 * n:
        raise ValueError(f"{meta['binary']}: expected {9 * n} bytes, got {len(raw)}")
    meta["elevation"] = np.frombuffer(raw, "<f4", n, 0).reshape(shape)
    meta["slopeDeg"] = np.frombuffer(raw, "<f4", n, 4 * n).reshape(shape)
    meta["terrainClass"] = np.frombuffer(raw, "u1", n, 8 * n).reshape(shape)
    return meta
