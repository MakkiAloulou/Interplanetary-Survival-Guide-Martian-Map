"""A NASA Mars Trek tile layer → one colour image overlay cut exactly to the site (CLAUDE.md §8).

    python -m pipeline themis-night-ir      # writes data/processed/gale/themis_night_ir.png

Trek's EQ tile grid (WMTSCapabilities, TileMatrixSet default028mm) is the app's: level z has 2^(z+1) x 2^z tiles of
256 px, top-left -180/90. The tiles covering the site at `zoom` are fetched, each output pixel samples the nearest tile
pixel (no smoothing: the source pixels stay visible), values are stretched between their 2nd and 98th percentile
inside the site, and coloured with a ramp. Trek's tiles are already display-stretched, so values are relative.
"""

import json
import math
import urllib.request
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from pipeline import config as C
from pipeline.mock import colormap
from pipeline.png import write_png

TILE_URL = "https://trek.nasa.gov/tiles/Mars/EQ/{layer}/1.0.0//default/default028mm/{z}/{row}/{col}.png"
# Cool to warm: low night-time brightness (sand, dust) dark blue, high (rock that keeps its heat) orange-yellow.
COOL_TO_WARM = [(0.0, (0.12, 0.16, 0.42)), (0.5, (0.55, 0.45, 0.62)), (0.75, (0.92, 0.48, 0.25)), (1.0, (1.0, 0.86, 0.42))]


def tile_index(lat: float, lon: float, z: int) -> tuple[float, float]:
    """Fractional (row, col) of a point in the tile grid of level z."""
    span = 180 / 2**z
    return (90 - lat) / span, (lon + 180) / span


def fetch_tile(layer: str, z: int, row: int, col: int, cache_dir: Path) -> np.ndarray:
    """Band 1 (grey) of one tile as uint8 (256, 256); cached."""
    path = Path(cache_dir) / f"{layer}_{z}_{row}_{col}.png"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(TILE_URL.format(layer=layer, z=z, row=row, col=col), headers={"User-Agent": "martian-map-pipeline"})
        path.write_bytes(urllib.request.urlopen(req, timeout=60).read())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(path) as s:
            return s.read(1)


def sample_site(layer: str, z: int, bounds: dict, out_px: int, cache_dir: Path, fetch=fetch_tile) -> np.ndarray:
    """out_px x out_px grey values over bounds, each the nearest tile pixel to the output pixel centre."""
    t = (np.arange(out_px) + 0.5) / out_px
    lats = bounds["latMax"] - t * (bounds["latMax"] - bounds["latMin"])
    lons = bounds["lonMin"] + t * (bounds["lonMax"] - bounds["lonMin"])
    rows = ((90 - lats) / (180 / 2**z) * 256).astype(np.int64)  # global pixel row of each output row
    cols = ((lons + 180) / (180 / 2**z) * 256).astype(np.int64)
    out = np.zeros((out_px, out_px), np.uint8)
    tiles = {}
    for i, r in enumerate(rows):
        for j, c in enumerate(cols):
            key = (int(r // 256), int(c // 256))
            if key not in tiles:
                tiles[key] = fetch(layer, z, key[0], key[1], cache_dir)
            out[i, j] = tiles[key][r % 256, c % 256]
    return out


def stretch(values: np.ndarray) -> np.ndarray:
    """Values scaled to [0, 1] between their 2nd and 98th percentile (clipped)."""
    lo, hi = np.percentile(values, [2, 98])
    return np.clip((values.astype(np.float64) - lo) / max(hi - lo, 1e-9), 0, 1)


def convert_themis_night_ir(
    out_png: Path = C.DATA_DIR / "processed" / "gale" / "themis_night_ir.png",
    cache_dir: Path = C.DATA_DIR / "raw" / "trek_tiles",
    config_json: Path = C.DATA_DIR / "config.json",
) -> dict:
    bounds = json.loads(Path(config_json).read_text(encoding="utf-8"))["site"]["bounds"]
    grey = sample_site(C.THEMIS_NIGHT_IR_LAYER, C.THEMIS_NIGHT_IR_ZOOM, bounds, C.OVERLAY_PX, cache_dir)
    write_png(out_png, colormap(stretch(grey), COOL_TO_WARM))
    span_m = (bounds["latMax"] - bounds["latMin"]) * 2 * math.pi * C.MARS_EQUATORIAL_RADIUS_M / 360
    source_px = span_m / (180 / 2**C.THEMIS_NIGHT_IR_ZOOM / 256 * 2 * math.pi * C.MARS_EQUATORIAL_RADIUS_M / 360)
    return {"file": str(out_png), "greyRange": [int(grey.min()), int(grey.max())], "tilePixelsAcrossSite": round(source_px, 1)}
