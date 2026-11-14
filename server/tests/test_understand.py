"""Understand endpoint with Ollama mocked at the HTTP layer (no Ollama in CI)."""

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings

CONTEXT = {
    "targets": [
        {"id": "msl-first-ridge", "name": "First boxwork ridge close-up"},
        {"id": "msl-altadena", "name": "Altadena drill site"},
        {"id": "msl-nevado-sajama", "name": "Nevado Sajama (ridge drill site)"},
    ],
    "stops": [{"id": "msl-altadena", "name": "Altadena drill site", "state": "current"}],
    "current_stop_id": "msl-altadena",
    "eva_clock": "T+1:10",
}


def client_with(handler) -> TestClient:
    app = create_app(Settings(warmup=False), transport=httpx.MockTransport(handler))
    return TestClient(app)


def ollama_reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"model": "qwen3:8b", "message": {"role": "assistant", "content": content}, "done": True})


def ask(c: TestClient, transcript: str = "Can we stay 20 more minutes?") -> dict:
    r = c.post("/api/copilot/understand", json={"transcript": transcript, "context": CONTEXT})
    assert r.status_code == 200
    return r.json()


def test_valid_output_and_the_request_sent_to_ollama():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["body"] = json.loads(request.content)
        return ollama_reply('{"intent": "extend_stay", "minutes": 20, "target_id": null, "clarify_question": null}')

    out = ask(client_with(handler))
    assert out["ok"] and out["source"] == "llm"
    assert out["understood"] == {"intent": "extend_stay", "minutes": 20, "target_id": None, "clarify_question": None}
    body = seen["body"]
    assert body["think"] is False and body["stream"] is False
    assert body["options"]["temperature"] == 0
    # target ids are an enum built from the request's context, not a fixed list
    enum = body["format"]["properties"]["target_id"]["anyOf"][0]["enum"]
    assert set(enum) == {"msl-first-ridge", "msl-altadena", "msl-nevado-sajama"}
    assert "Can we stay 20 more minutes?" in body["messages"][1]["content"]


def test_clarifying_question_passes_through():
    reply = '{"intent": "add_stop", "minutes": null, "target_id": null, "clarify_question": "Which ridge: First boxwork ridge or Nevado Sajama?"}'
    out = ask(client_with(lambda r: ollama_reply(reply)), "Can we also visit the ridge?")
    assert out["ok"] and out["understood"]["clarify_question"].startswith("Which ridge")


def test_unknown_target_is_dropped_not_trusted():
    reply = '{"intent": "add_stop", "minutes": null, "target_id": "olympus-mons", "clarify_question": null}'
    out = ask(client_with(lambda r: ollama_reply(reply)))
    assert out["ok"] and out["understood"]["target_id"] is None


def test_minutes_only_for_extend_stay():
    reply = '{"intent": "time_left", "minutes": 20, "target_id": null, "clarify_question": null}'
    assert ask(client_with(lambda r: ollama_reply(reply)))["understood"]["minutes"] is None


def test_think_tags_are_stripped():
    reply = '<think>\n\n</think>\n{"intent": "go_home", "minutes": null, "target_id": null, "clarify_question": null}'
    assert ask(client_with(lambda r: ollama_reply(reply)))["understood"]["intent"] == "go_home"


@pytest.mark.parametrize(
    "content",
    [
        "Sure! You can stay 20 minutes.",  # not JSON
        '{"intent": "dance", "minutes": null, "target_id": null, "clarify_question": null}',  # intent not in the set
        '{"intent": "extend_stay", "minutes": 999, "target_id": null, "clarify_question": null}',  # out of range
        '{"minutes": 20}',  # intent missing
    ],
)
def test_invalid_output_means_fallback(content):
    out = ask(client_with(lambda r: ollama_reply(content)))
    assert out == {**out, "ok": False, "source": "unavailable", "understood": None}
    assert "did not validate" in out["error"]


def test_timeout_means_fallback():
    def handler(request):
        raise httpx.ReadTimeout("slow", request=request)

    out = ask(client_with(handler))
    assert not out["ok"] and "timed out" in out["error"]


def test_ollama_down_means_fallback():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    out = ask(client_with(handler))
    assert not out["ok"] and "unavailable" in out["error"]


def test_ollama_http_error_means_fallback():
    out = ask(client_with(lambda r: httpx.Response(500, text="model not found")))
    assert not out["ok"]


def test_while_the_model_loads_questions_go_to_the_rules_at_once():
    calls = []
    app = create_app(Settings(warmup=True), transport=httpx.MockTransport(lambda r: calls.append(r) or ollama_reply("{}")))
    out = TestClient(app).post("/api/copilot/understand", json={"transcript": "Can we stay?", "context": CONTEXT}).json()  # lifespan not run: still warming up
    assert not out["ok"] and "loading" in out["error"]
    assert calls == []  # nothing queued in Ollama


def test_bad_request_is_rejected():
    c = client_with(lambda r: ollama_reply("{}"))
    assert c.post("/api/copilot/understand", json={"transcript": "", "context": CONTEXT}).status_code == 422
    assert c.post("/api/copilot/understand", json={"transcript": "x" * 600, "context": CONTEXT}).status_code == 422


def test_health_reports_ollama_and_model():
    def handler(request):
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "qwen3:8b"}]})
        return ollama_reply("{}")

    h = client_with(handler).get("/api/copilot/health").json()
    assert h["ollama"] and h["model_available"] and h["model"] == "qwen3:8b"

    down = client_with(lambda r: (_ for _ in ()).throw(httpx.ConnectError("refused", request=r))).get("/api/copilot/health").json()
    assert down["ok"] and not down["ollama"] and not down["model_available"]
