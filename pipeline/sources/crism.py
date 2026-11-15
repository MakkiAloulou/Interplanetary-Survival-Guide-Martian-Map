"""MRO CRISM summary parameters → a mineral overlay cut exactly to the site (CLAUDE.md §8).

    python -m pipeline crism      # writes data/processed/gale/crism_minerals.png

Source: one CRISM map-projected targeted observation (MTRDR, summary-parameter file SU, PDS Geosciences Node),
already on the app's sphere (equirectangular, R = 3396190 m, centre lat 0), 18 m pixels, ENVI BSQ float32 with 60
bands. Only the bands used are downloaded, with HTTP range requests, and cached in data/raw/crism/.

Processing: per-column striping removed (each column shifted to the scene median), 5 x 5 box mean (~90 m), then each
site pixel of the overlay is interpolated (bilinear) from the smoothed CRISM pixels. Colours: blue where the 1.9 µm
water band is strongest (hydrated minerals), green where the olivine index is (dark basaltic sand); each from its
75th percentile inside the site (transparent) to its 98th (full). Relative within the site, not abundances.
"""

import json
import re
import urllib.request
import warnings
from pathlib import Path

import numpy as np

from pipeline import config as C
from pipeline.png import write_png

NODATA = 65535.0
# Display colours (RGB 0-255): water-bearing minerals blue, olivine sand green.
HYDRATION_RGB = (30, 120, 255)
OLIVINE_RGB = (40, 170, 70)
MAX_ALPHA = 0.85


def parse_header(text: str) -> dict:
    """The ENVI header fields we need: size, map origin and pixel size (m), band names."""
    num = lambda k: int(re.search(rf"^{k}\s*=\s*(\d+)", text, re.M).group(1))  # noqa: E731
    info = re.search(r"map info\s*=\s*\{([^}]*)\}", text).group(1).split(",")
    names = re.search(r"band names\s*=\s*\{([^}]*)\}", text, re.S).group(1)
    return {
        "samples": num("samples"),
        "lines": num("lines"),
        "x0": float(info[3]),
        "y0": float(info[4]),
        "pixel_m": float(info[5]),
        "bands": [n.strip() for n in names.replace("\n", " ").split(",") if n.strip()],
    }


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "martian-map-pipeline", **(headers or {})})
    return urllib.request.urlopen(req, timeout=180).read()


def fetch_band(url: str, header: dict, name: str, cache_dir: Path) -> np.ndarray:
    """One band (lines, samples) float32 from the BSQ image, by byte range; cached. NODATA becomes NaN."""
    size = header["samples"] * header["lines"] * 4
    k = header["bands"].index(name)
    path = Path(cache_dir) / f"{C.CRISM_OBSERVATION}_{name}.f32"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _get(url + ".img", {"Range": f"bytes={k * size}-{(k + 1) * size - 1}"})
        if len(data) != size:
            raise RuntimeError(f"CRISM band {name}: got {len(data)} bytes, expected {size}")
        path.write_bytes(data)
    a = np.frombuffer(path.read_bytes(), "<f4").reshape(header["lines"], header["samples"]).astype(np.float64)
    a[(a >= NODATA - 1) | ~np.isfinite(a)] = np.nan
    return a


def destripe(a: np.ndarray) -> np.ndarray:
    """Removes per-column offsets (CRISM's vertical striping): each column moved to the scene median."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-nodata columns at the image edges
        col = np.nanmedian(a, axis=0)
    return a - (col - np.nanmedian(a))[None, :]


def box_mean(a: np.ndarray, k: int) -> np.ndarray:
    """k x k mean ignoring NaN (edges use the pixels that exist)."""
    p = k // 2
    v = np.where(np.isnan(a), 0.0, a)
    n = (~np.isnan(a)).astype(np.float64)
    vp, npad = np.pad(v, p), np.pad(n, p)
    sv = np.zeros_like(v)
    sn = np.zeros_like(n)
    for i in range(k):
        for j in range(k):
            sv += vp[i : i + a.shape[0], j : j + a.shape[1]]
            sn += npad[i : i + a.shape[0], j : j + a.shape[1]]
    with np.errstate(invalid="ignore"):
        return np.where(sn > 0, sv / np.maximum(sn, 1), np.nan)


def sample_site(a: np.ndarray, header: dict, bounds: dict, out_px: int) -> np.ndarray:
    """out_px x out_px values over bounds, interpolated bilinearly between CRISM pixel centres."""
    r = C.MARS_EQUATORIAL_RADIUS_M
    t = (np.arange(out_px) + 0.5) / out_px
    lats = bounds["latMax"] - t * (bounds["latMax"] - bounds["latMin"])
    lons = bounds["lonMin"] + t * (bounds["lonMax"] - bounds["lonMin"])
    # fractional pixel coordinates, 0 = centre of the first pixel
    fr = (header["y0"] - np.radians(lats) * r) / header["pixel_m"] - 0.5
    fc = (np.radians(lons) * r - header["x0"]) / header["pixel_m"] - 0.5
    if fr.min() < 0 or fc.min() < 0 or fr.max() > a.shape[0] - 1 or fc.max() > a.shape[1] - 1:
        raise ValueError("the CRISM observation does not cover the whole site")
    r0 = np.minimum(np.floor(fr).astype(np.int64), a.shape[0] - 2)
    c0 = np.minimum(np.floor(fc).astype(np.int64), a.shape[1] - 2)
    wr = (fr - r0)[:, None]
    wc = (fc - c0)[None, :]
    g = lambda dr, dc: a[np.ix_(r0 + dr, c0 + dc)]  # noqa: E731
    return (1 - wr) * ((1 - wc) * g(0, 0) + wc * g(0, 1)) + wr * ((1 - wc) * g(1, 0) + wc * g(1, 1))


def strength(v: np.ndarray, lo_pct: float, hi_pct: float) -> np.ndarray:
    """0 at the lo percentile of v (and below), 1 at the hi percentile (and above); NaN → 0."""
    lo, hi = np.nanpercentile(v, [lo_pct, hi_pct])
    return np.nan_to_num(np.clip((v - lo) / max(hi - lo, 1e-12), 0, 1))


def compose(hydration: np.ndarray, olivine: np.ndarray) -> np.ndarray:
    """RGBA uint8: each pixel takes the colour of the stronger signal, opacity growing with it."""
    use_h = hydration >= olivine
    s = np.where(use_h, hydration, olivine)
    rgba = np.zeros(hydration.shape + (4,), np.uint8)
    rgba[..., :3] = np.where(use_h[..., None], np.array(HYDRATION_RGB, np.uint8), np.array(OLIVINE_RGB, np.uint8))
    rgba[..., 3] = np.round(s * MAX_ALPHA * 255).astype(np.uint8)
    return rgba


def convert(
    out_png: Path = C.DATA_DIR / "processed" / "gale" / "crism_minerals.png",
    cache_dir: Path = C.DATA_DIR / "raw" / "crism",
    config_json: Path = C.DATA_DIR / "config.json",
    get=_get,
) -> dict:
    bounds = json.loads(Path(config_json).read_text(encoding="utf-8"))["site"]["bounds"]
    hdr_path = Path(cache_dir) / f"{C.CRISM_OBSERVATION}_07_su165j_mtr3.hdr"
    if not hdr_path.exists():
        hdr_path.parent.mkdir(parents=True, exist_ok=True)
        hdr_path.write_bytes(get(C.CRISM_SU_URL + ".hdr"))
    header = parse_header(hdr_path.read_text(encoding="utf-8", errors="replace"))
    site = {}
    for key, band in (("hydration", C.CRISM_HYDRATION_BAND), ("olivine", C.CRISM_OLIVINE_BAND)):
        smooth = box_mean(destripe(fetch_band(C.CRISM_SU_URL, header, band, cache_dir)), C.CRISM_SMOOTH_PX)
        site[key] = sample_site(smooth, header, bounds, C.OVERLAY_PX)
    h = strength(site["hydration"], C.CRISM_SHOW_FROM_PERCENTILE, C.CRISM_FULL_AT_PERCENTILE)
    o = strength(site["olivine"], C.CRISM_SHOW_FROM_PERCENTILE, C.CRISM_FULL_AT_PERCENTILE)
    write_png(out_png, compose(h, o))
    return {
        "file": str(out_png),
        "observation": C.CRISM_OBSERVATION.upper(),
        "pixelM": header["pixel_m"],
        "smoothedOverM": header["pixel_m"] * C.CRISM_SMOOTH_PX,
        "hydrationRange": [round(float(x), 4) for x in np.nanpercentile(site["hydration"], [2, 50, 98])],
        "olivineRange": [round(float(x), 4) for x in np.nanpercentile(site["olivine"], [2, 50, 98])],
        "shownHydrationPct": round(float(np.mean((h >= o) & (h > 0)) * 100), 1),
        "shownOlivinePct": round(float(np.mean((o > h)) * 100), 1),
    }
