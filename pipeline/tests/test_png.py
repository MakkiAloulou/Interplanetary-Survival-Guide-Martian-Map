import struct
import zlib

import numpy as np
import pytest

from pipeline.png import write_png


def decode(path):
    """Tiny decoder for what write_png produces (one IDAT, 8-bit, Up filter on every row)."""
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height, _, color_type = struct.unpack(">IIBB", data[16:26])
    idat_len = struct.unpack(">I", data[33:37])[0]
    raw = np.frombuffer(zlib.decompress(data[41 : 41 + idat_len]), np.uint8).reshape(height, -1)
    assert (raw[:, 0] == 2).all()
    rows = np.cumsum(raw[:, 1:], axis=0, dtype=np.uint8)  # undo Up filter (mod 256)
    return width, height, color_type, rows


@pytest.mark.parametrize("channels,color_type", [(None, 0), (3, 2), (4, 6)])
def test_png_round_trip(tmp_path, channels, color_type):
    rng = np.random.default_rng(0)
    shape = (7, 5) if channels is None else (7, 5, channels)
    pixels = rng.integers(0, 256, shape, dtype=np.uint8)
    write_png(tmp_path / "x.png", pixels)
    width, height, ct, rows = decode(tmp_path / "x.png")
    assert (width, height, ct) == (5, 7, color_type)
    np.testing.assert_array_equal(rows, pixels.reshape(7, -1))
