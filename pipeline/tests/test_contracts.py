"""Keep the Python side of the data contracts in step with app/src/types.ts and data/config.json."""

import json
import re

from pipeline import config


def test_terrain_codes_match_types_ts():
    types_ts = (config.REPO_ROOT / "app" / "src" / "types.ts").read_text(encoding="utf-8")
    block = re.search(r"export const TERRAIN = \{(.*?)\}", types_ts, re.S).group(1)
    ts_codes = {name: int(code) for name, code in re.findall(r"(\w+):\s*(\d+)", block)}
    assert ts_codes == {
        "BEDROCK": config.TERRAIN_BEDROCK,
        "SAND": config.TERRAIN_SAND,
        "BOULDERS": config.TERRAIN_BOULDERS,
        "NO_GO": config.TERRAIN_NO_GO,
    }


def test_statuses_match_types_ts():
    types_ts = (config.REPO_ROOT / "app" / "src" / "types.ts").read_text(encoding="utf-8")
    line = re.search(r"export type DataStatus = (.*)", types_ts).group(1)
    assert tuple(re.findall(r"'(\w+)'", line)) == config.DATA_STATUSES


def test_data_config_statuses_are_valid():
    cfg = json.loads((config.DATA_DIR / "config.json").read_text(encoding="utf-8"))
    statuses = [cfg["site"]["boundsStatus"]] + [layer["status"] for layer in cfg["layers"]]
    statuses += [cfg[key]["status"] for key in ("scienceTargets", "povImages", "conditions")]
    assert all(s in config.DATA_STATUSES for s in statuses)
