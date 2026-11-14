"""FastAPI app for the copilot. Run from the repo root:  python -m server   (or: python -m uvicorn server.app:app --port 8787)

Endpoints (all under /api/copilot):
  GET  /health      what is up: Ollama, the model, whisper
  POST /understand  transcript + context → {intent, minutes, target_id, clarify_question}, or ok=false → app uses rules
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from server.config import Settings
from server.llm import LLMError, OllamaClient
from server.models import HealthResponse, UnderstandRequest, UnderstandResponse

log = logging.getLogger("copilot")


def create_app(settings: Settings | None = None, transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    llm = OllamaClient(settings, transport)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        tasks = []
        if settings.warmup:
            tasks.append(asyncio.create_task(llm.warmup()))
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
            whisper_model=None,
            whisper_loaded=False,
        )

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
