"""USGS MSL Gale Merged DEM 1m v3 → CostGrid + hillshade for the site (CLAUDE.md §8, elevation slot).

    python -m pipeline gale-dem            # site bounds from data/config.json, output data/processed/gale/

The source GeoTIFF is 3.6 GB. Only the rows covering the site (plus a margin) are read over HTTP (GDAL /vsicurl/),
saved as a small GeoTIFF in data/raw/, then converted by pipeline.build exactly like any other DEM.
"""

import json
from pathlib import Path

import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import Window, from_bounds

from pipeline import config as C
from pipeline.build import MARS_GEOGRAPHIC, build
from pipeline.costgrid import read_costgrid
from pipeline.habitat import place_habitat

SOURCE = (
    "USGS MSL Gale Merged DEM 1m v3 (Parker & Calef 2016; HiRISE, CTX and HRSC DEMs tied to MOLA), "
    "via planetarymaps.usgs.gov; see data/SOURCES.md"
)


def site_bbox(config_json: Path = C.DATA_DIR / "config.json") -> tuple[float, float, float, float]:
    """(lonmin, latmin, lonmax, latmax) of the site in data/config.json."""
    b = json.loads(Path(config_json).read_text(encoding="utf-8"))["site"]["bounds"]
    return b["lonMin"], b["latMin"], b["lonMax"], b["latMax"]


def clip(src_path: str, bbox: tuple[float, float, float, float], out_tif: Path, margin_m: float = C.GALE_DEM_CLIP_MARGIN_M) -> dict:
    """Copy the part of a (local or remote) DEM covering bbox plus margin_m into out_tif, unchanged pixels."""
    remote = src_path.startswith("http")
    path = f"/vsicurl/{src_path}" if remote else src_path
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"), rasterio.open(path) as src:
        left, bottom, right, top = transform_bounds(MARS_GEOGRAPHIC, src.crs, *bbox, densify_pts=21)
        win = from_bounds(left - margin_m, bottom - margin_m, right + margin_m, top + margin_m, src.transform)
        win = win.round_offsets().round_lengths().intersection(Window(0, 0, src.width, src.height))
        data = src.read(1, window=win)
        profile = src.profile | {
            "width": int(win.width),
            "height": int(win.height),
            "transform": src.window_transform(win),
            "compress": "deflate",
            "tiled": True,
            "blockxsize": 256,
            "blockysize": 256,
        }
    out_tif = Path(out_tif)
    out_tif.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(out_tif, "w", **profile) as dst:
        dst.write(data, 1)
    return {"window": [int(win.col_off), int(win.row_off), int(win.width), int(win.height)], "file": str(out_tif)}


def convert(
    out_dir: Path = C.DATA_DIR / "processed" / "gale",
    raw_tif: Path = C.DATA_DIR / "raw" / "gale_dem_1m_site.tif",
    bbox: tuple[float, float, float, float] | None = None,
    src: str = C.GALE_DEM_URL,
    refresh: bool = False,
    science: tuple[float, float] = C.GALE_SCIENCE_CENTER,
    sand: str | None = None,
    boulders: str | None = None,
) -> dict:
    """Clip (cached in data/raw/ unless refresh), build the CostGrid at the app's 2 m cells, place the habitat.
    `sand` / `boulders`: optional mask rasters with a rule, as for `python -m pipeline build`."""
    bbox = bbox or site_bbox()
    clipped = None
    if refresh or not Path(raw_tif).exists():
        clipped = clip(src, bbox, raw_tif)
    source = SOURCE + ("; sand and boulders from the HiRISE orthophoto (pipeline/surface.py, MODELED)" if sand or boulders else "")
    summary = build(Path(raw_tif), bbox, out_dir, C.MOCK_CELL_SIZE_M, sand=sand, boulders=boulders, source=source)
    # The habitat must stand on this terrain: place it by the MODELED rule in pipeline/habitat.py.
    waypoints = place_habitat(read_costgrid(Path(out_dir) / "costgrid.json"), science)
    (Path(out_dir) / "waypoints.json").write_text(json.dumps(waypoints, indent=2) + "\n", encoding="utf-8")
    return summary | {"clip": clipped or "cached", "waypoints": waypoints}


def convert_surface(
    out_dir: Path = C.DATA_DIR / "processed" / "gale",
    ortho_tif: Path = C.DATA_DIR / "raw" / "gale_ortho_25cm_site.tif",
    mask_dir: Path = C.DATA_DIR / "raw",
) -> dict:
    """Sand and boulder masks from the HiRISE orthophoto, then the CostGrid rebuilt with them (habitat re-placed)."""
    from pipeline.surface import classify, features, write_mask

    if not Path(ortho_tif).exists():
        clip(C.GALE_ORTHO_URL, site_bbox(), ortho_tif, margin_m=20)  # ~50 MB over HTTP, a few minutes
    plain = convert(out_dir)  # the grid without masks fixes the cells and gives the slope for the sand rule
    grid = read_costgrid(Path(out_dir) / "costgrid.json")
    f = features(ortho_tif, grid)
    sand, boulders = classify(f["brightness"], f["speckle"], grid["slopeDeg"])
    write_mask(sand, grid["bounds"], Path(mask_dir) / "gale_sand_mask.tif")
    write_mask(boulders, grid["bounds"], Path(mask_dir) / "gale_boulder_mask.tif")
    summary = convert(out_dir, sand=str(Path(mask_dir) / "gale_sand_mask.tif"), boulders=str(Path(mask_dir) / "gale_boulder_mask.tif"))
    return summary | {"withoutMasks": plain["fraction"]}
