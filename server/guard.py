"""Number guard for LLM-reworded answers: the wording may change, the facts may not.

A rewording passes only if:
- every number in it appears in the WhatIfResult or in the deterministic template built from it,
- it spells out no number ("fifteen", "half an hour"), which would slip past the check,
- it keeps the template's lead word (Yes / No / Partly), so a NO-GO can never be reworded into a GO,
- it is still at most 30 words.
"""

import re
from dataclasses import dataclass, field
from typing import Any

MAX_WORDS = 30
LEADS = ("Yes", "No", "Partly")

_NUMBER = re.compile(r"\d+(?:[.:]\d+)?")
_SPELLED = re.compile(
    r"\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|"
    r"seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|half|quarter|"
    r"dozen|couple)\b",
    re.I,
)


@dataclass
class GuardResult:
    ok: bool
    reasons: list[str] = field(default_factory=list)


def _numbers_in(value: Any, out: set[str]) -> set[str]:
    """Every number in a JSON value, as text (ints, floats, and digits inside strings such as "14:35")."""
    if isinstance(value, bool) or value is None:
        return out
    if isinstance(value, (int, float)):
        out.add(_canon(str(value)))
        if isinstance(value, float) and value.is_integer():
            out.add(str(int(value)))
    elif isinstance(value, str):
        out.update(_canon(n) for n in _NUMBER.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            _numbers_in(v, out)
    elif isinstance(value, (list, tuple)):
        for v in value:
            _numbers_in(v, out)
    return out


def _canon(n: str) -> str:
    """'15.0' → '15', '0.120' → '0.12'; clock times unchanged."""
    if ":" in n:
        return n
    if "." in n:
        n = n.rstrip("0").rstrip(".")
    return n


def lead(text: str) -> str | None:
    m = re.match(r"\s*(Yes|No|Partly)\b", text)
    return m.group(1) if m else None


def check(text: str, template: str, result: dict) -> GuardResult:
    reasons: list[str] = []
    allowed = _numbers_in(result, set()) | {_canon(n) for n in _NUMBER.findall(template)}
    bad = [n for n in _NUMBER.findall(text) if _canon(n) not in allowed]
    if bad:
        reasons.append(f"numbers not in the result: {', '.join(bad)}")
    spelled = _SPELLED.findall(text)
    if spelled:
        reasons.append(f"spelled-out numbers: {', '.join(spelled)}")
    if lead(template) and lead(text) != lead(template):
        reasons.append(f"lead word changed from {lead(template)!r} to {lead(text)!r}")
    words = len(text.split())
    if words > MAX_WORDS:
        reasons.append(f"{words} words (max {MAX_WORDS})")
    if not text.strip():
        reasons.append("empty")
    return GuardResult(ok=not reasons, reasons=reasons)
