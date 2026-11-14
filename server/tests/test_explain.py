"""Explain: the LLM may reword, never change a number or the verdict (Ollama mocked)."""

import httpx
import pytest
from fastapi.testclient import TestClient

from server import guard
from server.app import create_app
from server.config import Settings

TEMPLATE = "Partly. You can stay 15 minutes, not 20: after that you would get back too close to sunset. Head back by 16:36."
RESULT = {
    "intent": "extend_stay",
    "verdict": "PARTIAL",
    "requested_min": 20,
    "allowed_min": 15,
    "binding": "SUNSET",
    "numbers": {"o2_left_min": 365, "pnr_in_min": 245, "head_back_by": "16:36", "head_back_in_min": 15, "sunset_margin_min": 30, "dose_msv": 0.09, "o2_at_return_min": 300},
}


@pytest.mark.parametrize(
    "text",
    [
        TEMPLATE,
        "Partly. Stay 15 minutes, not 20, or you will be back too close to sunset. Leave by 16:36.",
        "Partly: 15 minutes is the most, not 20, because of sunset. Head back by 16:36.",
    ],
)
def test_rewordings_that_keep_the_facts_pass(text):
    assert guard.check(text, TEMPLATE, RESULT).ok


@pytest.mark.parametrize(
    ("text", "why"),
    [
        ("Partly. You can stay 18 minutes, not 20. Head back by 16:36.", "18"),  # a changed number
        ("Partly. Stay 15 minutes, then head back by 16:40.", "16:40"),  # a changed clock time
        ("Partly. Stay fifteen minutes, not twenty. Head back by 16:36.", "spelled"),  # spelled numbers slip past digits
        ("Yes. You can stay 15 minutes. Head back by 16:36.", "lead word"),  # verdict flipped
        ("Partly. " + "really " * 30 + "15 minutes.", "words"),  # too long
        ("Partly. Stay 15 minutes, and you will have 365 minutes of oxygen and 12 to spare.", "12"),  # an invented number
    ],
)
def test_rewordings_that_change_facts_fail(text, why):
    g = guard.check(text, TEMPLATE, RESULT)
    assert not g.ok
    assert why in " ".join(g.reasons)


def test_numbers_from_the_result_are_allowed_even_if_not_in_the_template():
    assert guard.check("Partly. Stay 15 minutes; your O₂ is 365 minutes. Head back by 16:36.", TEMPLATE, RESULT).ok


def client(reply):
    def handler(request: httpx.Request) -> httpx.Response:
        if isinstance(reply, Exception):
            raise reply
        return httpx.Response(200, json={"message": {"role": "assistant", "content": reply}, "done": True})

    return TestClient(create_app(Settings(warmup=False), transport=httpx.MockTransport(handler)))


def explain(c):
    r = c.post("/api/copilot/explain", json={"template": TEMPLATE, "result": RESULT})
    assert r.status_code == 200
    return r.json()


def test_good_rewording_is_used():
    out = explain(client("Partly. Stay 15 minutes, not 20, or you will be back too close to sunset. Leave by 16:36."))
    assert out["source"] == "llm" and out["text"].startswith("Partly. Stay 15 minutes")


def test_guard_failure_falls_back_to_the_template():
    out = explain(client("Yes! You have plenty of time, stay 20 minutes."))
    assert out["source"] == "template" and out["text"] == TEMPLATE
    assert out["guard_reasons"]


def test_timeout_falls_back_to_the_template():
    out = explain(client(httpx.ReadTimeout("slow")))
    assert out["source"] == "template" and out["text"] == TEMPLATE
