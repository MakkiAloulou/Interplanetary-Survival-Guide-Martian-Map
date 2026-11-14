"""360° views from the real terrain (pipeline/sources/gale_panoramas.py): colours and stations, no network."""

import json

import numpy as np

from pipeline.panorama import render_panorama
from pipeline.sources.gale_panoramas import TINT, ground_colours, stations


def test_ground_colours_are_tinted_grey_in_range():
    brightness = np.linspace(60, 200, 100).reshape(10, 10)
    rgb = ground_colours(brightness)
    assert rgb.shape == (10, 10, 3)
    assert rgb.min() >= 0 and rgb.max() <= 1
    # every pixel is the same grey times the tint, so channel ratios equal the tint ratios
    assert np.allclose(rgb[..., 1] / rgb[..., 0], TINT[1] / TINT[0])
    assert rgb[0, 0, 0] < rgb[-1, -1, 0]  # darker ground stays darker


def test_stations_are_the_habitat_then_every_stop(tmp_path):
    (tmp_path / "w.json").write_text(json.dumps([
        {"id": "base", "lat": 1.0, "lon": 2.0, "kind": "base", "name": "Habitat"},
        {"id": "rover", "lat": 1.0, "lon": 2.1, "kind": "rover", "name": "Rover"},
    ]))
    (tmp_path / "t.json").write_text(json.dumps([{"id": "a", "name": "A", "lat": 3.0, "lon": 4.0}]))
    assert [s["id"] for s in stations(tmp_path / "w.json", tmp_path / "t.json")] == ["base", "a"]


def test_a_wall_to_the_east_fills_the_east_of_the_view():
    elev = np.zeros((101, 101))
    elev[:, 70:] = 40.0  # a 40 m wall 40 m east of the centre
    image = render_panorama(elev, np.full((101, 101, 3), 0.5), 1.0, 50, 50, 1.7, 360, 90, 90.0, 200.0)
    above_horizon = image[30]  # a row 15° above the horizon
    sky = above_horizon[0]  # looking north: open
    assert np.abs(above_horizon[90].astype(int) - sky.astype(int)).sum() > 30  # east: the wall, not sky
    assert np.abs(above_horizon[270].astype(int) - sky.astype(int)).sum() < 5  # west: sky
