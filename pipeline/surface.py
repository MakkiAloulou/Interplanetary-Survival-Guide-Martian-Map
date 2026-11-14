"""Sand and boulder masks from the HiRISE orthophoto, on the CostGrid's 2 m cells (MODELED; constants in config.py).

The 25 cm orthophoto is warped onto the cell grid at 0.25 m (8 x 8 samples per 2 m cell). Per cell:
- brightness: mean grey; `relative brightness` = brightness minus the mean over the cells within
  SURFACE_CONTEXT_CELLS (Gale's sand is dark basaltic sand, the cemented boxwork ridges are pale);
- speckle: standard deviation of the 0.25 m samples (ridge rims, blocks and their shadows are speckled; sandy hollow
  floors are smooth at this scale).
Sand = smooth (speckle below its SAND_SMOOTH_PERCENTILE in the site) AND darker than the surroundings AND slope below
SAND_MAX_SLOPE_DEG, kept only where at least SAND_MIN_NEIGHBOURS of the 3 x 3 cells qualify (patches, not specks).
Boulders = speckle above its BOULDER_SPECKLE_PERCENTILE, not sand, in clusters of BOULDER_MIN_NEIGHBOURS.
Percentile thresholds are relative to the site. The DEM's local relief was tried for "in a hollow" and dropped: the
elevation model is too smooth to resolve 1-2 m ridges.
"""

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.warp import Resampling

from pipeline import config as C
from pipeline.build import MARS_GEOGRAPHIC, target_grid, warp_to_grid


def box_mean(a: np.ndarray, r: int) -> np.ndarray:
    """Mean over the (2r+1)² box around each cell (at the edges, over the part of the box inside the array)."""
    s = np.pad(a.astype(np.float64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    h, w = a.shape
    r0, r1 = np.clip(np.arange(h) - r, 0, h), np.clip(np.arange(h) + r + 1, 0, h)
    c0, c1 = np.clip(np.arange(w) - r, 0, w), np.clip(np.arange(w) + r + 1, 0, w)
    total = s[r1][:, c1] - s[r0][:, c1] - s[r1][:, c0] + s[r0][:, c0]
    count = (r1 - r0)[:, None] * (c1 - c0)[None, :]
    return total / count


def block_stats(fine: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """(mean, std) of each k x k block of `fine`."""
    h, w = fine.shape[0] // k, fine.shape[1] // k
    blocks = fine[: h * k, : w * k].reshape(h, k, w, k).astype(np.float64)
    return blocks.mean(axis=(1, 3)), blocks.std(axis=(1, 3))


def neighbour_count(mask: np.ndarray) -> np.ndarray:
    """Number of True cells in the 3 x 3 box around each cell, itself included."""
    p = np.pad(mask.astype(int), 1)
    h, w = mask.shape
    return sum(p[dr : dr + h, dc : dc + w] for dr in range(3) for dc in range(3))


def features(ortho: Path, grid: dict) -> dict:
    """Per-cell brightness and speckle of the orthophoto, on the CostGrid `grid` (read_costgrid output)."""
    b = grid["bounds"]
    k = round(grid["cellSizeM"] / C.SURFACE_SAMPLE_M)
    fine = target_grid((b["lonMin"], b["latMin"], b["lonMax"], b["latMax"]), C.SURFACE_SAMPLE_M)
    if (fine["height"], fine["width"]) != (grid["height"] * k, grid["width"] * k):
        raise ValueError("orthophoto sample grid does not nest in the CostGrid cells")
    image = np.nan_to_num(warp_to_grid(Path(ortho), fine, Resampling.nearest), nan=0.0)
    brightness, speckle = block_stats(image, k)
    return {"brightness": brightness, "speckle": speckle}


def classify(brightness: np.ndarray, speckle: np.ndarray, slope_deg: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(sand, boulders) boolean masks by the rule in the module docstring."""
    relative = brightness - box_mean(brightness, C.SURFACE_CONTEXT_CELLS)
    raw_sand = (speckle < np.percentile(speckle, C.SAND_SMOOTH_PERCENTILE)) & (relative < 0) & (slope_deg < C.SAND_MAX_SLOPE_DEG)
    sand = raw_sand & (neighbour_count(raw_sand) >= C.SAND_MIN_NEIGHBOURS)
    raw_boulders = (speckle > np.percentile(speckle, C.BOULDER_SPECKLE_PERCENTILE)) & ~sand
    boulders = raw_boulders & (neighbour_count(raw_boulders) >= C.BOULDER_MIN_NEIGHBOURS)
    return sand, boulders


def write_mask(mask: np.ndarray, bounds: dict, path: Path) -> None:
    """A 0/1 GeoTIFF on exactly the CostGrid cells (Mars geographic), for pipeline.build's --sand / --boulders."""
    h, w = mask.shape
    transform = from_bounds(bounds["lonMin"], bounds["latMin"], bounds["lonMax"], bounds["latMax"], w, h)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(path, "w", driver="GTiff", width=w, height=h, count=1, dtype="uint8", crs=MARS_GEOGRAPHIC,
                       transform=transform, compress="deflate") as d:  # fmt: skip
        d.write(mask.astype(np.uint8), 1)
