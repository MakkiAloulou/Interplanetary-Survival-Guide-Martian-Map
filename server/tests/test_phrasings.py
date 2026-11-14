"""The eval set itself stays valid: known intents, target ids that exist in its context, and the scorer's rules."""

import json

from server.eval_phrasings import PHRASINGS, score
from server.models import INTENTS, UnderstandContext


def test_phrasings_file_is_consistent():
    data = json.loads(PHRASINGS.read_text(encoding="utf-8"))
    ctx = UnderstandContext.model_validate(data["context"])
    ids = set(ctx.ids())
    assert len(data["cases"]) >= 25
    for c in data["cases"]:
        assert c["intent"] in INTENTS, c
        assert all(t is None or t in ids for t in c.get("targets", [])), c
        assert c.get("clarify") or c["intent"] in ("time_left", "go_home", "unknown") or c.get("targets"), c
    assert {c["intent"] for c in data["cases"]} == set(INTENTS)


def test_scoring():
    case = {"intent": "extend_stay", "minutes": 20, "targets": ["msl-nodules", None]}
    assert score(case, {"intent": "extend_stay", "minutes": 20, "target_id": None})["ok"]
    assert not score(case, {"intent": "extend_stay", "minutes": 15, "target_id": None})["ok"]
    assert not score(case, {"intent": "extend_stay", "minutes": 20, "target_id": "msl-panorama"})["ok"]
    ambiguous = {"intent": "extend_stay", "minutes": None, "clarify": True}
    assert score(ambiguous, {"intent": "extend_stay", "minutes": None, "target_id": "msl-nodules"})["ok"]
    assert not score({"intent": "time_left"}, None)["ok"]
