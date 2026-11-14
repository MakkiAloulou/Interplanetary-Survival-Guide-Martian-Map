"""Trek tile layer → site overlay (pipeline/sources/trek_overlay.py), with a fake tile source instead of the network."""

import numpy as np
import pytest

from pipeline.sources.trek_overlay import sample_site, stretch, tile_index


def test_tile_index_matches_the_trek_grid():
    # Level 0 is 2 x 1 tiles of 180°; the top-left corner is -180 / 90.
    assert tile_index(90, -180, 0) == (0, 0)
    assert tile_index(0, 0, 0) == (0.5, 1.0)
    row, col = tile_index(-4.80, 137.38, 9)  # our site at level 9: tile row 269, column 902
    assert (int(row), int(col)) == (269, 902)


def test_each_output_pixel_takes_the_nearest_tile_pixel():
    z = 9
    calls = []

    def fake(layer, zz, row, col, cache_dir):
        calls.append((row, col))
        # every tile pixel holds its own column index, so the sampled column can be read back
        return np.tile(np.arange(256, dtype=np.uint8), (256, 1))

    span = 180 / 2**z / 256  # degrees per tile pixel
    lon0 = -180 + 902 * 256 * span + 10 * span  # starts exactly at pixel column 10 of tile 902
    bounds = {"latMin": -4.80, "latMax": -4.80 + 4 * span, "lonMin": lon0, "lonMax": lon0 + 4 * span}
    out = sample_site("layer", z, bounds, 8, cache_dir=None, fetch=fake)
    assert out.shape == (8, 8)
    assert list(out[0]) == [10, 10, 11, 11, 12, 12, 13, 13]  # two output pixels per source pixel
    assert set(calls) == {(269, 902)}  # one tile fetched once


def test_stretch_uses_the_2nd_to_98th_percentile():
    v = np.arange(101, dtype=np.uint8)  # 0..100
    s = stretch(v)
    assert s[2] == pytest.approx(0) and s[98] == pytest.approx(1)
    assert s.min() == 0 and s.max() == 1  # outliers clipped
