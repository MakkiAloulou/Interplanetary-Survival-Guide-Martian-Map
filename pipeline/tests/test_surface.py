"""Sand and boulder rules (pipeline/surface.py) on synthetic cell grids."""

import numpy as np
import pytest
import rasterio

from pipeline import config as C
from pipeline.costgrid import bounds_from_center
from pipeline.surface import block_stats, box_mean, classify, neighbour_count, write_mask

N = 60


def test_box_mean_uses_the_part_of_the_box_inside_the_array():
    a = np.arange(9, dtype=float).reshape(3, 3)
    m = box_mean(a, 1)
    assert m[1, 1] == pytest.approx(a.mean())
    assert m[0, 0] == pytest.approx(a[:2, :2].mean())


def test_block_stats():
    fine = np.zeros((4, 4))
    fine[:2, :2] = [[0, 2], [0, 2]]
    mean, std = block_stats(fine, 2)
    assert mean[0, 0] == 1 and std[0, 0] == 1 and std[1, 1] == 0


def test_neighbour_count_counts_the_3x3_box_and_the_edges_right():
    m = np.zeros((4, 4), bool)
    m[0, 0] = m[0, 1] = m[1, 0] = True
    n = neighbour_count(m)
    assert n[0, 0] == 3 and n[1, 1] == 3 and n[3, 3] == 0


def scene():
    """Medium grey, mildly speckled bedrock with: a dark smooth patch (sand), one dark smooth cell (speck), a strongly
    speckled 4x4 cluster (boulders), one strongly speckled cell (a lone fracture), a dark smooth patch on a steep face."""
    rng = np.random.default_rng(1)
    brightness = 120 + rng.normal(0, 2, (N, N))
    speckle = 10 + rng.uniform(0, 4, (N, N))
    slope = np.full((N, N), 5.0)
    brightness[10:16, 10:16], speckle[10:16, 10:16] = 90, 2  # sand patch
    brightness[30, 30], speckle[30, 30] = 90, 2  # single dark smooth cell
    speckle[40:44, 40:44] = 60  # boulder cluster
    speckle[50, 10] = 60  # lone speckled cell
    brightness[10:16, 45:51], speckle[10:16, 45:51], slope[10:16, 45:51] = 90, 2, 30  # dark smooth but steep
    return brightness, speckle, slope


def test_sand_is_a_dark_smooth_gentle_patch():
    sand, _ = classify(*scene())
    assert sand[11:15, 11:15].all()
    assert not sand[30, 30]  # a single cell is not a patch
    assert not sand[10:16, 45:51].any()  # too steep for sand
    assert not sand[40:44, 40:44].any()


def test_boulders_are_clusters_of_strong_speckle():
    sand, boulders = classify(*scene())
    assert boulders[41:43, 41:43].all()
    assert not boulders[50, 10]  # a lone fracture is not a boulder field
    assert not (sand & boulders).any()
    assert boulders.mean() <= (100 - C.BOULDER_SPECKLE_PERCENTILE) / 100 + 1e-9


def test_mask_file_sits_exactly_on_the_grid_cells(tmp_path):
    bounds = bounds_from_center(-4.80, 137.38, 40.0, 20.0)
    mask = np.zeros((10, 20), bool)
    mask[2, 3] = True
    write_mask(mask, bounds, tmp_path / "m.tif")
    with rasterio.open(tmp_path / "m.tif") as s:
        assert (s.width, s.height) == (20, 10)
        assert s.read(1)[2, 3] == 1 and s.read(1).sum() == 1
        assert s.bounds.left == pytest.approx(bounds["lonMin"]) and s.bounds.top == pytest.approx(bounds["latMax"])
