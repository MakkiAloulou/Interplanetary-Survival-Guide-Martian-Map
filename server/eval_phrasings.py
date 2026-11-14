"""Score the LLM's understanding on server/tests/phrasings.json against the real Ollama, and time it.

    python -m server.eval_phrasings            # one pass
    python -m server.eval_phrasings --runs 3   # repeat (temperature 0, so mostly for latency)

A case counts as correct when the intent is right, the minutes are right (extend_stay), and target_id is one of the
accepted ids. Ambiguous cases ("the ridge") are scored on intent only; whether the LLM itself asked is reported, but
in the app the deterministic place matcher asks anyway.
"""

import argparse
import asyncio
import json
import statistics
import time
from pathlib import Path

from server.config import Settings
from server.llm import LLMError, OllamaClient
from server.models import UnderstandContext

PHRASINGS = Path(__file__).parent / "tests" / "phrasings.json"


def score(case: dict, u: dict | None) -> dict:
    if u is None:
        return {"intent": False, "minutes": None, "target": None, "ok": False}
    intent_ok = u["intent"] == case["intent"]
    minutes_ok = None
    if case["intent"] == "extend_stay":
        minutes_ok = u.get("minutes") == case.get("minutes")
    target_ok = None
    if "targets" in case and not case.get("clarify"):
        target_ok = u.get("target_id") in case["targets"]
    ok = intent_ok and minutes_ok is not False and target_ok is not False
    return {"intent": intent_ok, "minutes": minutes_ok, "target": target_ok, "ok": ok}


async def run(runs: int) -> dict:
    data = json.loads(PHRASINGS.read_text(encoding="utf-8"))
    ctx = UnderstandContext.model_validate(data["context"])
    settings = Settings.from_env()
    llm = OllamaClient(settings)
    await llm.warmup()
    rows = []
    for _ in range(runs):
        for case in data["cases"]:
            t0 = time.perf_counter()
            try:
                u = (await llm.understand(case["text"], ctx)).model_dump()
                err = None
            except LLMError as e:
                u, err = None, str(e)
            ms = (time.perf_counter() - t0) * 1000
            rows.append({"case": case, "u": u, "err": err, "ms": ms, "score": score(case, u)})
    await llm.aclose()
    return {"model": settings.model, "rows": rows}


def report(out: dict) -> None:
    rows = out["rows"]
    print(f"model {out['model']}, {len(rows)} questions\n")
    for r in rows:
        c, u, s = r["case"], r["u"], r["score"]
        mark = "ok " if s["ok"] else "BAD"
        got = r["err"] or f"{u['intent']} min={u['minutes']} target={u['target_id']}" + (f" clarify={u['clarify_question']!r}" if u["clarify_question"] else "")
        print(f"{mark} {r['ms']:6.0f} ms  [{c['style']}] {c['text']!r}\n          → {got}")

    def rate(key: str) -> str:
        vals = [r["score"][key] for r in rows if r["score"][key] is not None]
        return f"{sum(vals)}/{len(vals)} ({100 * sum(vals) / len(vals):.0f}%)" if vals else "n/a"

    ms = sorted(r["ms"] for r in rows)
    clar = [r for r in rows if r["case"].get("clarify")]
    asked = sum(1 for r in clar if r["u"] and (r["u"]["clarify_question"] or r["u"]["target_id"] is None))
    print("\nSummary")
    print(f"  fully correct  {rate('ok')}")
    print(f"  intent         {rate('intent')}")
    print(f"  minutes        {rate('minutes')}   (extend_stay cases)")
    print(f"  target         {rate('target')}   (cases naming one place)")
    print(f"  ambiguous      LLM left the place open or asked in {asked}/{len(clar)} (the app's matcher asks in every case)")
    print(f"  errors         {sum(1 for r in rows if r['err'])}")
    print(f"  latency ms     mean {statistics.mean(ms):.0f} · p50 {ms[len(ms) // 2]:.0f} · p90 {ms[int(len(ms) * 0.9)]:.0f} · max {ms[-1]:.0f}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--runs", type=int, default=1)
    p.add_argument("--json", type=Path, help="also write the raw results here")
    args = p.parse_args()
    out = asyncio.run(run(args.runs))
    report(out)
    if args.json:
        args.json.write_text(json.dumps(out, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
