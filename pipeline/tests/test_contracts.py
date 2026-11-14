"""Keep the Python side of the data contracts in step with app/src/types.ts and data/config.json."""

import json
import re

import pytest

from pipeline import config

TYPES_TS = (config.REPO_ROOT / "app" / "src" / "types.ts").read_text(encoding="utf-8")
CONFIG_JSON = config.DATA_DIR / "config.json"
# data/ is git-ignored, so config checks run only where it exists (not in CI).
needs_data = pytest.mark.skipif(not CONFIG_JSON.exists(), reason="data/ not present")


def test_terrain_codes_match_types_ts():
    block = re.search(r"export const TERRAIN = \{(.*?)\}", TYPES_TS, re.S).group(1)
    ts_codes = {name: int(code) for name, code in re.findall(r"(\w+):\s*(\d+)", block)}
    assert ts_codes == {
        "BEDROCK": config.TERRAIN_BEDROCK,
        "SAND": config.TERRAIN_SAND,
        "BOULDERS": config.TERRAIN_BOULDERS,
        "NO_GO": config.TERRAIN_NO_GO,
    }


def test_statuses_match_types_ts():
    line = re.search(r"export type DataStatus = (.*)", TYPES_TS).group(1)
    assert tuple(re.findall(r"'(\w+)'", line)) == config.DATA_STATUSES


@needs_data
def test_data_config_statuses_are_valid():
    cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    statuses = [cfg["site"]["boundsStatus"]] + [layer["status"] for layer in cfg["layers"]]
    statuses += [cfg[key]["status"] for key in ("scienceTargets", "povImages", "conditions", "waypoints")]
    assert all(s in config.DATA_STATUSES for s in statuses)


@needs_data
def test_site_bounds_match_the_cost_grid():
    cfg = json.loads(CONFIG_JSON.read_text(encoding="utf-8"))
    grid = json.loads((config.DATA_DIR / cfg["costGrid"]).read_text(encoding="utf-8"))
    for key, value in grid["bounds"].items():
        assert cfg["site"]["bounds"][key] == pytest.approx(value, abs=1e-6)
