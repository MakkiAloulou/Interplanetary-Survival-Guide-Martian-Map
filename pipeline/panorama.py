"""Render a 360° ground-level panorama from a DEM (front-to-back ray marching, "voxel space").

Used for MOCK point-of-view images until real Curiosity Mastcam/Navcam images replace them.
Output is equirectangular: column 0 looks north, azimuth increases clockwise; rows are linear in elevation angle.
"""

import numpy as np

SKY_HORIZON = np.array([0.82, 0.67, 0.52])  # butterscotch dusty sky near the horizon
SKY_ZENITH = np.array([0.55, 0.45, 0.38])
HAZE_LENGTH_M = 2500.0  # distance at which dust haze reaches ~63%


def _bilinear(z: np.ndarray, r: np.ndarray, c: np.ndarray) -> np.ndarray:
    r0 = np.clip(np.floor(r).astype(int), 0, z.shape[0] - 2)
    c0 = np.clip(np.floor(c).astype(int), 0, z.shape[1] - 2)
    fr, fc = np.clip(r - r0, 0, 1), np.clip(c - c0, 0, 1)
    top = z[r0, c0] * (1 - fc) + z[r0, c0 + 1] * fc
    bottom = z[r0 + 1, c0] * (1 - fc) + z[r0 + 1, c0 + 1] * fc
    return top * (1 - fr) + bottom * fr


def render_panorama(
    elevation: np.ndarray,
    colors: np.ndarray,
    cell_size_m: float,
    row: int,
    col: int,
    eye_height_m: float,
    width: int,
    height: int,
    vfov_deg: float,
    max_distance_m: float,
) -> np.ndarray:
    """elevation (H, W) m; colors (H, W, 3) in [0, 1]. Returns a uint8 (height, width, 3) image."""
    angle_per_row = np.radians(vfov_deg) / height
    elevation_angle = (height / 2 - (np.arange(height) + 0.5)) * angle_per_row  # +up, row 0 = top
    t = np.clip(elevation_angle / (np.radians(vfov_deg) / 2), 0, 1)[:, None, None]
    image = np.broadcast_to(SKY_HORIZON * (1 - t) + SKY_ZENITH * t, (height, width, 3)).copy()

    azimuth = (np.arange(width) + 0.5) / width * 2 * np.pi
    step_r, step_c = -np.cos(azimuth) / cell_size_m, np.sin(azimuth) / cell_size_m  # north = row decreasing
    eye_z = elevation[row, col] + eye_height_m
    rows = np.arange(height)[:, None]
    unpainted_from = np.full(width, height)  # per column: rows >= this are already ground

    distance = 0.5
    while distance < max_distance_m:
        r, c = row + step_r * distance, col + step_c * distance
        inside = (r >= 0) & (r <= elevation.shape[0] - 1) & (c >= 0) & (c <= elevation.shape[1] - 1)
        if not inside.any():
            break
        z = _bilinear(elevation, r, c)
        angle = np.arctan2(z - eye_z, distance)
        top = np.clip(np.ceil(height / 2 - angle / angle_per_row - 0.5), 0, height).astype(int)
        top = np.where(inside, top, height)
        paint = (rows >= top) & (rows < unpainted_from)
        if paint.any():
            haze = 1 - np.exp(-distance / HAZE_LENGTH_M)
            color = np.stack([_bilinear(colors[..., k], r, c) for k in range(3)], axis=-1) * (1 - haze) + SKY_HORIZON * haze
            image = np.where(paint[..., None], color[None, :, :], image)
            unpainted_from = np.minimum(unpainted_from, top)
        distance += max(0.25, distance * 0.012)

    # Beyond the grid: distant hazy ground up to the horizon.
    far = (rows >= height // 2) & (rows < unpainted_from)
    image = np.where(far[..., None], SKY_HORIZON * 0.85, image)
    return (np.clip(image, 0, 1) * 255).astype(np.uint8)
