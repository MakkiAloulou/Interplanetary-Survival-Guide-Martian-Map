"""FastAPI app for the copilot. Run from the repo root:  python -m server   (or: python -m uvicorn server.app:app --port 8787)

Endpoints (all under /api/copilot):
  GET  /health      what is up: Ollama, the model, whisper
  POST /transcribe  audio (push-to-talk clip) + prompt words → text (faster-whisper, CPU)
  POST /understand  transcript + context → {intent, minutes, target_id, clarify_question}, or ok=false → app uses rules
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from typing import Protocol

import httpx
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from server.config import Settings
from server.llm import LLMError, OllamaClient
from server.models import HealthResponse, TranscribeResponse, UnderstandRequest, UnderstandResponse
from server.stt import STTError, Transcriber, Transcript

log = logging.getLogger("copilot")

# A push-to-talk clip: a few seconds of opus is a few tens of kB; anything far bigger is not a question.
MAX_AUDIO_BYTES = 5_000_000
MAX_PROMPT_CHARS = 800


class SpeechToText(Protocol):
    model_name: str

    @property
    def loaded(self) -> bool: ...

    def warmup(self) -> None: ...

    def transcribe(self, audio: bytes, prompt: str = "") -> Transcript: ...


def create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None, stt: SpeechToText | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    llm = OllamaClient(settings, transport)
    speech: SpeechToText = stt or Transcriber(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        tasks = []
        if settings.warmup:
            tasks.append(asyncio.create_task(llm.warmup()))
            tasks.append(asyncio.create_task(asyncio.to_thread(speech.warmup)))
        yield
        for t in tasks:
            t.cancel()
        await llm.aclose()

    app = FastAPI(title="Martian Map copilot", lifespan=lifespan)
    app.state.settings = settings
    app.state.llm = llm
    # The app reaches the server through the Vite proxy (same origin); this allows direct calls from the dev server too.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/api/copilot/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        tags = await llm.tags()
        available = any(t == settings.model or t.startswith(settings.model + ":") for t in tags)
        return HealthResponse(
            ok=True,
            ollama=bool(tags),
            model=settings.model,
            model_available=available,
            llm_ready=llm.ready and available,
            whisper_model=speech.model_name,
            whisper_loaded=speech.loaded,
        )

    @app.post("/api/copilot/transcribe", response_model=TranscribeResponse)
    async def transcribe(audio: UploadFile = File(...), prompt: str = Form("")) -> TranscribeResponse:
        data = await audio.read(MAX_AUDIO_BYTES + 1)
        if not data:
            return TranscribeResponse(ok=False, error="empty audio")
        if len(data) > MAX_AUDIO_BYTES:
            return TranscribeResponse(ok=False, error="audio too long")
        try:
            t = await run_in_threadpool(speech.transcribe, data, prompt[:MAX_PROMPT_CHARS])
        except STTError as e:
            log.warning("transcribe failed: %s", e)
            return TranscribeResponse(ok=False, error=str(e))
        return TranscribeResponse(ok=True, text=t.text, ms=t.ms, model=t.model, audio_s=t.audio_s)

    @app.post("/api/copilot/understand", response_model=UnderstandResponse)
    async def understand(req: UnderstandRequest) -> UnderstandResponse:
        t0 = time.perf_counter()
        try:
            u = await llm.understand(req.transcript, req.context)
            return UnderstandResponse(ok=True, source="llm", understood=u, ms=(time.perf_counter() - t0) * 1000)
        except LLMError as e:
            log.warning("understand fell back to rules: %s", e)
            return UnderstandResponse(ok=False, source="unavailable", error=str(e), ms=(time.perf_counter() - t0) * 1000)

    return app


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
app = create_app()
