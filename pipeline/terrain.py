"""Terrain derivatives shared by the mock generator and the real-DEM pipeline. Horn (1981) 3x3 gradients, as in gdaldem."""

import numpy as np


def gradients(elevation: np.ndarray, cell_size_m: float) -> tuple[np.ndarray, np.ndarray]:
    """dz/deast and dz/dnorth (m/m). Row 0 is north. Edges are padded by repetition."""
    z = np.pad(elevation.astype(np.float64), 1, mode="edge")
    a, b, c = z[:-2, :-2], z[:-2, 1:-1], z[:-2, 2:]
    d, f = z[1:-1, :-2], z[1:-1, 2:]
    g, h, i = z[2:, :-2], z[2:, 1:-1], z[2:, 2:]
    dz_east = ((c + 2 * f + i) - (a + 2 * d + g)) / (8 * cell_size_m)
    dz_north = ((a + 2 * b + c) - (g + 2 * h + i)) / (8 * cell_size_m)
    return dz_east, dz_north


def slope_deg(elevation: np.ndarray, cell_size_m: float) -> np.ndarray:
    """Steepest slope of each cell, degrees."""
    dz_east, dz_north = gradients(elevation, cell_size_m)
    return np.degrees(np.arctan(np.hypot(dz_east, dz_north))).astype(np.float32)


def hillshade(elevation: np.ndarray, cell_size_m: float, azimuth_deg: float = 315.0, altitude_deg: float = 45.0) -> np.ndarray:
    """Lambertian shading in [0, 1]. Azimuth clockwise from north (315 = light from the north-west)."""
    dz_east, dz_north = gradients(elevation, cell_size_m)
    az, alt = np.radians(azimuth_deg), np.radians(altitude_deg)
    light = np.array([np.sin(az) * np.cos(alt), np.cos(az) * np.cos(alt), np.sin(alt)])
    norm = np.sqrt(dz_east**2 + dz_north**2 + 1)
    shade = (-dz_east * light[0] - dz_north * light[1] + light[2]) / norm
    return np.clip(shade, 0, 1)
