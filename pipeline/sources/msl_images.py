"""Curiosity raw images → PovImage[] for the science stops (CLAUDE.md §8, POV slot).

    python -m pipeline msl-images        # writes data/processed/gale/pov_images.json and pov/*.jpg

Images are taken only at a stop's exact rover position: raw image ids carry the rover motion counter
(`_F<site:3><drive:4>`, e.g. F1190486 = site 119, drive 486), which must equal the MMGIS waypoint the stop was placed
on. Per stop: up to POV_NAVCAM_PER_STOP left-Navcam frames looking out over the terrain, spread around the compass,
plus one Front Hazcam frame of the drill workspace when the stop has a `workspaceSol`. The viewing direction is the
rover heading (waypoint yaw) plus the mast azimuth; it is approximate and labelled so.
"""

import json
import re
import urllib.parse
import urllib.request
import warnings
from pathlib import Path

import rasterio
from rasterio.enums import Resampling
from rasterio.errors import NotGeoreferencedWarning

from pipeline import config as C
from pipeline.sources.msl_targets import CURATED, load_waypoints, position_on_sol

RMC_RE = re.compile(r"_F(\d{3})(\d{4})")
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def rmc_of(imageid: str) -> tuple[int, int] | None:
    """(site, drive) from a raw image id, or None."""
    m = RMC_RE.search(imageid)
    return (int(m.group(1)), int(m.group(2))) if m else None


def compass(az: float) -> str:
    return COMPASS[round((az % 360) / 22.5) % 16]


def _get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "martian-map-pipeline"})
    return urllib.request.urlopen(req, timeout=timeout).read()


def fetch_sol(sol: int, instrument: str, cache_dir: Path) -> list[dict]:
    """All raw image items of one camera on one sol (cached as JSON)."""
    cache = Path(cache_dir) / f"{sol}_{instrument}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    items, page = [], 0
    while True:
        query = urllib.parse.urlencode({
            "order": "sol desc", "per_page": 200, "page": page,
            "condition_1": "msl:mission", "condition_2": f"{sol}:sol:gte", "condition_3": f"{sol}:sol:lte",
            "condition_4": f"{instrument}:instrument",
        })
        data = json.loads(_get(f"{C.MSL_RAW_IMAGES_API}?{query}"))
        items += data["items"]
        page += 1
        if not data.get("more"):
            break
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps(items), encoding="utf-8")
    return items


def _gap(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def spread_by_azimuth(frames: list[dict], n: int) -> list[dict]:
    """Up to n frames facing directions as far apart as possible (greedy, starting with the one nearest mid-range
    elevation), skipping views back over the rover deck when others exist; stops early when every remaining frame is
    within 20° of one already chosen."""
    if not frames:
        return []
    az = lambda f: float(f["extended"]["mast_az"])
    outward = [f for f in frames if _gap(az(f), 180.0) > C.POV_SKIP_REAR_HALF_ANGLE_DEG]
    frames = outward or frames  # views back over the rover deck only as a last resort
    el_mid = sum(C.POV_NAVCAM_EL_RANGE_DEG) / 2
    chosen = [min(frames, key=lambda f: abs(float(f["extended"]["mast_el"]) - el_mid))]
    while len(chosen) < n:
        rest = [f for f in frames if f not in chosen]
        if not rest:
            break
        best = max(rest, key=lambda f: min(_gap(az(f), az(c)) for c in chosen))
        if min(_gap(az(best), az(c)) for c in chosen) < 20:
            break
        chosen.append(best)
    return chosen


def select_frames(items_nav: list[dict], items_haz: list[dict], site: int, drive: int) -> list[tuple[dict, str]]:
    """(item, kind) pairs taken at this rover position; kind is 'navcam' or 'hazcam'."""
    lo, hi = C.POV_NAVCAM_EL_RANGE_DEG
    nav = [
        i for i in items_nav
        if i["extended"]["sample_type"] == "full" and rmc_of(i["imageid"]) == (site, drive)
        and i["extended"]["mast_el"] is not None and lo <= float(i["extended"]["mast_el"]) <= hi
    ]
    picked = [(i, "navcam") for i in spread_by_azimuth(nav, C.POV_NAVCAM_PER_STOP)]
    haz = [i for i in items_haz if i["extended"]["sample_type"] == "full" and rmc_of(i["imageid"]) == (site, drive)]
    if haz:
        picked.append((max(haz, key=lambda i: i["date_taken"]), "hazcam"))
    return picked


def save_resized(src: Path, out: Path, px: int) -> None:
    """Write a px-wide JPEG copy of the image file src."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(src) as s:
            h = round(s.height * px / s.width)
            data = s.read(out_shape=(s.count, h, px), resampling=Resampling.average)
        out.parent.mkdir(parents=True, exist_ok=True)
        with rasterio.open(out, "w", driver="JPEG", width=px, height=h, count=data.shape[0], dtype="uint8", QUALITY=85) as d:
            d.write(data)


def describe(item: dict, kind: str, yaw: float) -> tuple[str, str]:
    """(camera label, source text) for one frame."""
    e = item["extended"]
    lmst = (e.get("lmst") or "").split("M")[-1][:5]
    when = f"sol {item['sol']}" + (f", {lmst} Mars local time" if lmst else "")
    if kind == "navcam":
        heading = (yaw + float(e["mast_az"])) % 360
        camera = f"Navcam, looking {compass(heading)}"
        view = f"Looking {compass(heading)} (about {heading:.0f}°: rover heading + mast azimuth, approximate), {abs(float(e['mast_el'])):.0f}° below level."
    else:
        camera = "Front Hazcam: drill workspace"
        view = f"Front hazard camera looking down at the rock in front of the rover (rover facing {compass(yaw)})."
    source = f"{item['image_credit']}: Curiosity raw image {item['imageid'].rstrip('_')}, {when}. {view} {C.MSL_RAW_IMAGE_PAGE}{item['id']}"
    return camera, source


def convert(
    out_json: Path = C.DATA_DIR / "processed" / "gale" / "pov_images.json",
    pov_dir: Path = C.DATA_DIR / "processed" / "gale" / "pov",
    raw_dir: Path = C.DATA_DIR / "raw" / "msl_raw",
    curated: Path = CURATED,
) -> dict:
    waypoints = load_waypoints(C.DATA_DIR / "raw" / "MSL_waypoints.json")
    stops = json.loads(Path(curated).read_text(encoding="utf-8"))["targets"]
    url_prefix = Path(pov_dir).resolve().relative_to(C.DATA_DIR.resolve()).as_posix()
    povs, report = [], {}
    for t in stops:
        w = position_on_sol(waypoints, t["sol"])
        nav = fetch_sol(w["sol"], "NAV_LEFT_B", raw_dir)
        haz = fetch_sol(t["workspaceSol"], "FHAZ_LEFT_B", raw_dir) if "workspaceSol" in t else []
        frames = select_frames(nav, haz, w["site"], w["drive"])
        report[t["id"]] = [i["imageid"] for i, _ in frames]
        for item, kind in frames:
            name = item["imageid"].rstrip("_")
            original = Path(raw_dir) / Path(urllib.parse.urlparse(item["https_url"]).path).name
            if not original.exists():
                original.write_bytes(_get(item["https_url"], timeout=120))
            save_resized(original, Path(pov_dir) / f"{name}.jpg", C.POV_IMAGE_PX)
            save_resized(original, Path(pov_dir) / f"{name}_thumb.jpg", C.POV_THUMB_PX)
            camera, source = describe(item, kind, float(w["yaw"]))
            povs.append({
                "lat": round(w["lat"], 7), "lon": round(w["lon"], 7),
                "url": f"{url_prefix}/{name}.jpg", "thumbnailUrl": f"{url_prefix}/{name}_thumb.jpg",
                "source": source, "sol": item["sol"], "camera": camera, "isPanorama": False, "status": "OBSERVED",
            })
    # Keep the rendered panoramas (pipeline/sources/gale_panoramas.py) that share this file.
    kept = [p for p in json.loads(Path(out_json).read_text(encoding="utf-8")) if p["isPanorama"]] if Path(out_json).exists() else []
    Path(out_json).write_text(json.dumps(povs + kept, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {"images": len(povs), "perStop": report}
