import numpy as np
import pytest

from pipeline.terrain import gradients, hillshade, slope_deg


def plane(dz_east: float, dz_north: float, cell: float = 2.0, n: int = 5) -> np.ndarray:
    x = np.arange(n) * cell
    y = np.arange(n)[::-1] * cell  # row 0 = north
    return dz_east * x[None, :] + dz_north * y[:, None]


def test_slope_of_tilted_plane_uses_metre_cell_size():
    s = slope_deg(plane(0.5, 0.0), 2.0)  # 1 m rise per 2 m cell
    assert s[2, 2] == pytest.approx(np.degrees(np.arctan(0.5)), abs=1e-4)


def test_gradient_signs_follow_east_and_north():
    dz_east, dz_north = gradients(plane(0.1, -0.2), 2.0)
    assert dz_east[2, 2] == pytest.approx(0.1)
    assert dz_north[2, 2] == pytest.approx(-0.2)


def test_flat_ground_has_zero_slope():
    assert slope_deg(np.full((4, 4), -3700.0), 2.0).max() == 0


def test_hillshade_lights_slopes_facing_the_sun():
    flat = hillshade(np.zeros((5, 5)), 2.0)[2, 2]
    facing_nw = hillshade(plane(0.3, -0.3), 2.0)[2, 2]  # ground rises to the south-east, faces north-west
    facing_se = hillshade(plane(-0.3, 0.3), 2.0)[2, 2]
    assert flat == pytest.approx(np.sin(np.radians(45)))
    assert facing_nw > flat > facing_se
