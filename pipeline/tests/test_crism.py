import json

import numpy as np
import pytest

from pipeline import config as C
from pipeline.sources import crism

HEADER = """ENVI
samples = 6
lines   = 4
bands   = 3
map info = {MRO Mars Equirectangular [IAU 2000] [0.00N; 0.00E], 1.0000, 1.0000, 1000.0, -2000.0, 1.8000000000e+01, 1.8000000000e+01, D_Mars, units=Meters}
band names = {
 R770, BD1900R2,
 OLINDEX3}
"""


def test_header_fields():
    h = crism.parse_header(HEADER)
    assert (h["samples"], h["lines"], h["x0"], h["y0"], h["pixel_m"]) == (6, 4, 1000.0, -2000.0, 18.0)
    assert h["bands"] == ["R770", "BD1900R2", "OLINDEX3"]


def test_destripe_removes_column_offsets():
    rng = np.random.default_rng(0)
    scene = rng.normal(0.01, 0.001, (200, 5))
    striped = scene + np.array([0.005, -0.003, 0.0, 0.01, -0.01])[None, :]
    out = crism.destripe(striped)
    assert np.ptp(np.median(out, axis=0)) < 1e-3  # stripes gone
    assert np.allclose(out - out.mean(axis=0), scene - scene.mean(axis=0))  # pattern inside each column kept


def test_box_mean_ignores_nodata():
    a = np.ones((5, 5))
    a[2, 2] = np.nan
    m = crism.box_mean(a, 3)
    assert np.allclose(m, 1.0)


def test_sample_site_interpolates_between_pixels_and_refuses_partial_cover():
    r = C.MARS_EQUATORIAL_RADIUS_M
    h = {"x0": 0.0, "y0": 0.0, "pixel_m": 18.0}
    a = np.arange(100 * 100, dtype=float).reshape(100, 100)
    # a site 180 m square starting 360 m east and 360 m south of the origin: pixels 20-29
    deg = lambda m: np.degrees(m / r)  # noqa: E731
    bounds = {"latMax": -deg(360), "latMin": -deg(540), "lonMin": deg(360), "lonMax": deg(540)}
    s = crism.sample_site(a, h, bounds, 10)
    # output pixel centres sit on CRISM pixel centres here, so values are exact; a plane stays a plane
    assert s[0, 0] == pytest.approx(a[20, 20]) and s[-1, -1] == pytest.approx(a[29, 29])
    half = crism.sample_site(a, h, bounds, 20)
    # a[r, c] = 100 r + c; the 2nd of 20 output pixels is centred a quarter pixel past CRISM pixel 20's centre
    assert half[1, 1] == pytest.approx(100 * 20.25 + 20.25)
    with pytest.raises(ValueError):
        crism.sample_site(a, h, {**bounds, "lonMax": deg(2000)}, 10)


def test_strength_and_compose():
    v = np.linspace(0, 1, 101)
    s = crism.strength(v, 50, 98)
    assert s[0] == 0 and s[50] == 0 and s[98] == pytest.approx(1) and s[100] == 1
    h = np.array([[0.0, 1.0, 0.2]])
    o = np.array([[0.0, 0.5, 0.6]])
    rgba = crism.compose(h, o)
    assert rgba[0, 0, 3] == 0  # nothing: transparent
    assert tuple(rgba[0, 1, :3]) == crism.HYDRATION_RGB and rgba[0, 1, 3] == round(crism.MAX_ALPHA * 255)
    assert tuple(rgba[0, 2, :3]) == crism.OLIVINE_RGB


def test_convert_end_to_end_with_a_fake_download(tmp_path, monkeypatch):
    r = C.MARS_EQUATORIAL_RADIUS_M
    n = 60
    bounds = {"latMax": -np.degrees(180 / r), "latMin": -np.degrees(720 / r), "lonMin": np.degrees(180 / r), "lonMax": np.degrees(720 / r)}
    (tmp_path / "config.json").write_text(json.dumps({"site": {"bounds": bounds}}))
    header = HEADER.replace("samples = 6", f"samples = {n}").replace("lines   = 4", f"lines   = {n}").replace("1000.0, -2000.0", "0.0, 0.0")
    rng = np.random.default_rng(1)
    cube = rng.normal(0.01, 0.002, (3, n, n)).astype("<f4")
    cube[1, :, :30] += 0.01  # more water in the west half
    cube[2, :, 30:] += 0.05  # more olivine in the east half

    def fake_get(url, headers=None):
        if url.endswith(".hdr"):
            return header.encode()
        a, b = (int(x) for x in headers["Range"].split("=")[1].split("-"))
        return cube.tobytes()[a : b + 1]

    monkeypatch.setattr(crism, "_get", fake_get)
    monkeypatch.setattr(C, "OVERLAY_PX", 30)
    out = tmp_path / "m.png"
    info = crism.convert(out_png=out, cache_dir=tmp_path / "raw", config_json=tmp_path / "config.json", get=fake_get)
    assert out.exists() and info["pixelM"] == 18.0
    assert info["hydrationRange"][2] > info["hydrationRange"][0]
