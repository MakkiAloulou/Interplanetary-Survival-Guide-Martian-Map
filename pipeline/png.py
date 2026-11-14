"""Minimal PNG writer (stdlib zlib), so mock layers need no imaging dependency."""

import struct
import zlib
from pathlib import Path

import numpy as np

_COLOR_TYPE = {1: 0, 3: 2, 4: 6}  # channels -> PNG colour type (grey, RGB, RGBA)


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))


def write_png(path: Path, pixels: np.ndarray) -> None:
    """pixels: uint8 array (H, W), (H, W, 3) or (H, W, 4). Row 0 is the top of the image."""
    a = np.asarray(pixels, dtype=np.uint8)
    if a.ndim == 2:
        a = a[..., None]
    height, width, channels = a.shape
    rows = a.reshape(height, width * channels)
    # PNG "Up" filter on every row: difference with the row above (compresses smooth rasters well).
    up = rows - np.vstack([np.zeros((1, rows.shape[1]), np.uint8), rows[:-1]])
    raw = np.hstack([np.full((height, 1), 2, np.uint8), up]).tobytes()
    ihdr = struct.pack(">IIBBBBB", width, height, 8, _COLOR_TYPE[channels], 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    Path(path).write_bytes(png)
