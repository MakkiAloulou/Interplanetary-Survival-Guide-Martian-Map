"""360° views at the habitat and every science stop, rendered from the real terrain (CLAUDE.md §8, POV slot).

    python -m pipeline gale-panoramas      # adds panoramas to data/processed/gale/pov_images.json

pipeline/panorama.py ray-marches the Gale elevation model (2 m cells) from eye height at the station and paints the
ground with the HiRISE orthophoto brightness of each cell (grey, with a light warm tint so it reads as Mars). Terrain
outside the 2 km site is not in the grid and shows as distant haze. DERIVED: computed from observations, not a photo.
Re-running replaces earlier panoramas and keeps the Curiosity photos in the same file.
"""

import json
import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from pipeline import config as C
from pipeline.costgrid import read_costgrid
from pipeline.habitat import rc_of
from pipeline.panorama import render_panorama
from pipeline.surface import features

TINT = np.array([1.0, 0.87, 0.74])  # light butterscotch tint on the grey HiRISE brightness (display choice)


def ground_colours(brightness: np.ndarray) -> np.ndarray:
    """(H, W, 3) colours in [0, 1] from per-cell orthophoto brightness, stretched 1st-99th percentile and tinted."""
    lo, hi = np.percentile(brightness, [1, 99])
    grey = np.clip((brightness - lo) / max(hi - lo, 1e-9), 0, 1) * 0.8 + 0.15
    return grey[..., None] * TINT


def save_jpeg(image: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(path, "w", driver="JPEG", width=image.shape[1], height=image.shape[0], count=3, dtype="uint8", QUALITY=88) as d:
            d.write(np.moveaxis(image, -1, 0))


def stations(waypoints_json: Path, targets_json: Path) -> list[dict]:
    """The habitat and every science stop: id, name, lat, lon."""
    base = next(w for w in json.loads(Path(waypoints_json).read_text(encoding="utf-8")) if w["kind"] == "base")
    targets = json.loads(Path(targets_json).read_text(encoding="utf-8"))
    return [{"id": "base", "name": base["name"], "lat": base["lat"], "lon": base["lon"]}] + [
        {"id": t["id"], "name": t["name"], "lat": t["lat"], "lon": t["lon"]} for t in targets
    ]


def convert(
    out_dir: Path = C.DATA_DIR / "processed" / "gale",
    ortho_tif: Path = C.DATA_DIR / "raw" / "gale_ortho_25cm_site.tif",
) -> dict:
    out_dir = Path(out_dir)
    grid = read_costgrid(out_dir / "costgrid.json")
    colours = ground_colours(features(ortho_tif, grid)["brightness"])
    url_prefix = (out_dir / "pov").resolve().relative_to(C.DATA_DIR.resolve()).as_posix()
    shape = grid["elevation"].shape
    panoramas = []
    for s in stations(out_dir / "waypoints.json", out_dir / "science_targets.json"):
        r, c = rc_of(grid["bounds"], shape, s["lat"], s["lon"])
        image = render_panorama(grid["elevation"], colours, grid["cellSizeM"], r, c, C.POV_EYE_HEIGHT_M,
                                C.POV_WIDTH_PX, C.POV_HEIGHT_PX, C.POV_VFOV_DEG, C.PANORAMA_MAX_DISTANCE_M)  # fmt: skip
        name = f"pano_{s['id']}"
        save_jpeg(image, out_dir / "pov" / f"{name}.jpg")
        save_jpeg(image[::4, ::4], out_dir / "pov" / f"{name}_thumb.jpg")
        panoramas.append({
            "lat": s["lat"], "lon": s["lon"],
            "url": f"{url_prefix}/{name}.jpg", "thumbnailUrl": f"{url_prefix}/{name}_thumb.jpg",
            "source": (
                f"Rendered by pipeline/panorama.py from the USGS Gale elevation model (2 m cells) at {C.POV_EYE_HEIGHT_M} m "
                f"eye height, ground painted with HiRISE orthophoto brightness (warm tint added); terrain beyond the 2 km "
                f"site is not modelled and shows as haze. Not a photo."
            ),
            "sol": 0, "camera": "360° view rendered from the elevation model", "isPanorama": True, "status": "DERIVED",
        })
    pov_json = out_dir / "pov_images.json"
    photos = [p for p in json.loads(pov_json.read_text(encoding="utf-8")) if not p["isPanorama"]] if pov_json.exists() else []
    pov_json.write_text(json.dumps(photos + panoramas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"panoramas": [p["url"] for p in panoramas], "photosKept": len(photos)}
