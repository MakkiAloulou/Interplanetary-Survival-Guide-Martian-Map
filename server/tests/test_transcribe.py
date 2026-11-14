"""Transcribe endpoint and the whisper model switch, with faster-whisper mocked (not installed in CI)."""

from types import SimpleNamespace

import httpx
from fastapi.testclient import TestClient

from server.app import create_app
from server.config import Settings
from server.stt import STTError, Transcriber, Transcript


class FakeSTT:
    model_name = "small.en"
    loaded = True

    def __init__(self, fail: bool = False):
        self.fail = fail
        self.calls: list[tuple[bytes, str]] = []

    def warmup(self) -> None:
        pass

    def transcribe(self, audio: bytes, prompt: str = "") -> Transcript:
        self.calls.append((audio, prompt))
        if self.fail:
            raise STTError("could not transcribe the audio: InvalidDataError")
        return Transcript(text="Can we stay 20 more minutes?", ms=812.0, model=self.model_name, audio_s=2.4)


def client(stt) -> TestClient:
    return TestClient(create_app(Settings(warmup=False), transport=httpx.MockTransport(lambda r: httpx.Response(500)), stt=stt))


def test_transcribes_and_passes_the_prompt_words():
    stt = FakeSTT()
    r = client(stt).post("/api/copilot/transcribe", files={"audio": ("q.webm", b"\x1aE\xdf\xa3fake-opus", "audio/webm")}, data={"prompt": "Altadena, Nevado Sajama, boxwork"})
    out = r.json()
    assert out["ok"] and out["text"] == "Can we stay 20 more minutes?" and out["model"] == "small.en"
    assert stt.calls[0][1] == "Altadena, Nevado Sajama, boxwork"


def test_prompt_is_capped_and_bad_audio_is_an_answer_not_a_crash():
    stt = FakeSTT(fail=True)
    out = client(stt).post("/api/copilot/transcribe", files={"audio": ("q.webm", b"junk", "audio/webm")}, data={"prompt": "x" * 5000}).json()
    assert not out["ok"] and "transcribe" in out["error"]
    assert len(stt.calls[0][1]) == 800


def test_empty_audio():
    out = client(FakeSTT()).post("/api/copilot/transcribe", files={"audio": ("q.webm", b"", "audio/webm")}).json()
    assert not out["ok"] and out["error"] == "empty audio"


def test_health_reports_whisper():
    h = client(FakeSTT()).get("/api/copilot/health").json()
    assert h["whisper_model"] == "small.en" and h["whisper_loaded"]


def test_slow_small_model_switches_to_base(monkeypatch):
    t = Transcriber(Settings(whisper_slow_s=0.0))
    monkeypatch.setattr(Transcriber, "warmup", lambda self: None)  # do not load a real model in the test
    t._model = SimpleNamespace(transcribe=lambda *a, **k: (iter([SimpleNamespace(text=" Fastest way back? ")]), SimpleNamespace(duration=1.5)))
    out = t.transcribe(b"audio", "boxwork")
    assert out.text == "Fastest way back?" and out.model == "small.en"
    assert t.model_name == "base.en" and not t.loaded  # next clips use the faster model


def test_silence_hallucinations_are_nothing_heard():
    t = Transcriber(Settings())
    t._model = SimpleNamespace(transcribe=lambda *a, **k: (iter([SimpleNamespace(text=" You")]), SimpleNamespace(duration=1.0)))
    assert t.transcribe(b"audio").text == ""


def test_a_long_clip_does_not_trigger_the_switch():
    t = Transcriber(Settings(whisper_slow_s=0.0))
    t._model = SimpleNamespace(transcribe=lambda *a, **k: (iter([SimpleNamespace(text="a long ramble")]), SimpleNamespace(duration=30.0)))
    t.transcribe(b"audio")
    assert t.model_name == "small.en"
