"""Curiosity raw-image selection (pipeline/sources/msl_images.py) on hand-made API items, no network."""

import numpy as np
import rasterio

from pipeline.sources.msl_images import compass, describe, rmc_of, save_resized, select_frames, spread_by_azimuth


def item(imageid, az=None, el=None, sample="full", taken="2025-10-01T12:00:00.000Z", sol=4687):
    return {
        "id": 42, "imageid": imageid, "sol": sol, "date_taken": taken, "image_credit": "NASA/JPL-Caltech",
        "extended": {"mast_az": None if az is None else str(az), "mast_el": None if el is None else str(el),
                     "sample_type": sample, "lmst": "Sol-04687M13:13:57.447"},
    }


def test_rover_position_comes_from_the_image_id():
    assert rmc_of("NLB_812160487EDR_F1190486NCAM00294M_") == (119, 486)
    assert rmc_of("FLB_816332976EDR_F1200082FHAZ00337M_") == (120, 82)
    assert rmc_of("4671ML1083980061406551C00_DXXX") is None


def test_compass_points():
    assert [compass(a) for a in (0, 44, 46, 180, 350)] == ["N", "NE", "NE", "S", "N"]


def test_frames_spread_around_the_compass_and_skip_views_over_the_deck():
    frames = [item(f"NLB_{az}_F1190486NCAM", az=az, el=-15) for az in (0, 10, 120, 190, 240)]
    chosen = [float(f["extended"]["mast_az"]) for f in spread_by_azimuth(frames, 3)]
    assert 190.0 not in chosen  # straight back over the rover deck
    assert sorted(chosen) == [0.0, 120.0, 240.0]


def test_only_the_rear_view_is_used_when_nothing_else_exists():
    assert len(spread_by_azimuth([item("NLB_F1190486", az=185, el=-15)], 3)) == 1


def test_select_frames_keeps_this_position_and_terrain_views_only():
    nav = [
        item("NLB_a_F1191722NCAM", az=10, el=-15),  # this stop, looking out: yes
        item("NLB_b_F1191722NCAM", az=100, el=-47),  # looking at the ground next to the wheels: no
        item("NLB_c_F1191722NCAM", az=200, el=-15, sample="thumbnail"),  # thumbnail: no
        item("NLB_d_F1190486NCAM", az=250, el=-15),  # taken from another rover position: no
    ]
    haz = [
        item("FLB_x_F1191722FHAZ", taken="2025-10-01T10:00:00.000Z"),
        item("FLB_y_F1191722FHAZ", taken="2025-10-01T15:00:00.000Z"),  # the latest of the day
        item("FLB_z_F1190486FHAZ", taken="2025-10-01T18:00:00.000Z"),  # other position
    ]
    picked = select_frames(nav, haz, 119, 1722)
    assert [(i["imageid"], kind) for i, kind in picked] == [("NLB_a_F1191722NCAM", "navcam"), ("FLB_y_F1191722FHAZ", "hazcam")]


def test_description_gives_direction_credit_and_a_link():
    camera, source = describe(item("NLB_a_F1191722NCAM_", az=287.17, el=-11.3), "navcam", yaw=118.99)
    assert camera == "Navcam, looking NE"  # 118.99 + 287.17 = 46.16°
    assert source.startswith("NASA/JPL-Caltech: Curiosity raw image NLB_a_F1191722NCAM, sol 4687, 13:13 Mars local time.")
    assert "approximate" in source and source.endswith("https://mars.nasa.gov/raw_images/42")


def test_resized_copy_keeps_the_aspect(tmp_path):
    src = tmp_path / "frame.tif"
    with rasterio.open(src, "w", driver="GTiff", width=200, height=100, count=1, dtype="uint8") as d:
        d.write(np.arange(200 * 100, dtype=np.uint32).reshape(1, 100, 200).astype(np.uint8))
    save_resized(src, tmp_path / "out.jpg", 50)
    with rasterio.open(tmp_path / "out.jpg") as s:
        assert (s.width, s.height, s.driver) == (50, 25, "JPEG")
