"""Ollama calls for the copilot. The LLM only classifies questions (Understand) and rephrases answers (Explain); it
never computes or decides a number. Every failure raises LLMError so the caller can fall back to the deterministic path.
"""

import json
import logging
import re
import time

import httpx
from pydantic import ValidationError

from server.config import Settings
from server.models import INTENTS, MAX_MINUTES, UnderstandContext, Understood

log = logging.getLogger("copilot.llm")


class LLMError(Exception):
    """Ollama unreachable, too slow, or its output did not validate."""


UNDERSTAND_SYSTEM = f"""You classify one question an astronaut asks during a walk on Mars. Reply with JSON only.

intent is one of:
- extend_stay: they want to stay or work longer, here or at a named stop. minutes = how many more minutes they ask for (integer, "half an hour" = 30), or null if they ask how long they can stay.
- add_stop: they want to also visit a place that is not on the plan. target_id = that place.
- skip_stop: they want to skip or drop a stop of the plan. target_id = that stop.
- time_left: they ask how long until they must turn back, or how much time or oxygen is left.
- go_home: they ask for the fastest or safest way back, or want to abort.
- unknown: anything else.

Rules:
- target_id must be one of the listed ids, or null. "here" or "this stop" means the current stop.
- If the place they name could be more than one listed place, set target_id to null and put a short question in clarify_question naming the options. Otherwise clarify_question is null.
- minutes is null unless the intent is extend_stay. Never more than {MAX_MINUTES}.
- Do not answer the question. Only classify it."""


def understand_schema(ids: list[str]) -> dict:
    """JSON schema for Ollama's structured output, with the target ids as an enum (built from the live context)."""
    target = {"anyOf": [{"type": "string", "enum": ids}, {"type": "null"}]} if ids else {"type": "null"}
    return {
        "type": "object",
        "properties": {
            "intent": {"type": "string", "enum": list(INTENTS)},
            "minutes": {"anyOf": [{"type": "integer", "minimum": 1, "maximum": MAX_MINUTES}, {"type": "null"}]},
            "target_id": target,
            "clarify_question": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        },
        "required": ["intent", "minutes", "target_id", "clarify_question"],
    }


def understand_prompt(transcript: str, ctx: UnderstandContext) -> str:
    stops = "\n".join(f"- {s.id}: {s.name} ({s.state})" for s in ctx.stops) or "- none"
    on_plan = {s.id for s in ctx.stops}
    others = "\n".join(f"- {t.id}: {t.name}" for t in ctx.targets if t.id not in on_plan) or "- none"
    current = ctx.current_stop_id or "none (walking between stops)"
    return (
        f"Stops on the plan:\n{stops}\n\nOther places that could be added:\n{others}\n\n"
        f"Current stop: {current}\nWalk clock: {ctx.eva_clock}\n\nQuestion: {transcript}"
    )


_THINK = re.compile(r"<think>.*?</think>", re.S)


class OllamaClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self._http = httpx.AsyncClient(base_url=settings.ollama_url, transport=transport, timeout=settings.llm_timeout_s)
        # False while the warm-up loads the model: questions then go to the app's rules at once instead of queueing
        # behind the load (Ollama keeps working on abandoned requests, which delays every later one).
        self.ready = not settings.warmup

    async def aclose(self) -> None:
        await self._http.aclose()

    async def chat(self, system: str, user: str, schema: dict | None, timeout_s: float, max_tokens: int = 160) -> str:
        body = {
            "model": self.settings.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "think": False,
            "keep_alive": "1h",
            "options": {"temperature": 0, "num_predict": max_tokens},
        }
        if schema is not None:
            body["format"] = schema
        try:
            r = await self._http.post("/api/chat", json=body, timeout=timeout_s)
            r.raise_for_status()
            content = r.json()["message"]["content"]
        except httpx.TimeoutException as e:
            raise LLMError(f"Ollama timed out after {timeout_s:.0f} s") from e
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise LLMError(f"Ollama unavailable: {e.__class__.__name__}: {e}") from e
        return _THINK.sub("", content).strip()

    async def understand(self, transcript: str, ctx: UnderstandContext) -> Understood:
        if not self.ready:
            raise LLMError("model still loading")
        ids = ctx.ids()
        t0 = time.perf_counter()
        content = await self.chat(UNDERSTAND_SYSTEM, understand_prompt(transcript, ctx), understand_schema(ids), self.settings.llm_timeout_s)
        try:
            u = Understood.model_validate(json.loads(content))
        except (json.JSONDecodeError, ValidationError) as e:
            raise LLMError(f"LLM output did not validate: {e.__class__.__name__}") from e
        if u.target_id is not None and u.target_id not in ids:
            # Not a place in the current data: drop it; the app resolves places from the words.
            log.warning("LLM picked unknown target %r; dropped", u.target_id)
            u = u.model_copy(update={"target_id": None})
        if u.intent != "extend_stay" and u.minutes is not None:
            u = u.model_copy(update={"minutes": None})
        log.info("understand %.0f ms: %s", (time.perf_counter() - t0) * 1000, u.model_dump())
        return u

    async def tags(self) -> list[str]:
        """Model names Ollama has pulled ([] when Ollama is down)."""
        try:
            r = await self._http.get("/api/tags", timeout=2.0)
            r.raise_for_status()
            return [m["name"] for m in r.json().get("models", [])]
        except (httpx.HTTPError, KeyError, ValueError):
            return []

    async def warmup(self) -> None:
        """Load the model into memory so the first question is not slow (keep_alive keeps it there)."""
        try:
            t0 = time.perf_counter()
            await self.chat("Reply with OK.", "OK?", None, timeout_s=180.0, max_tokens=2)
            log.info("Ollama %s warm in %.1f s", self.settings.model, time.perf_counter() - t0)
        except LLMError as e:
            log.warning("Ollama warm-up failed (the app will use its rule parser): %s", e)
        finally:
            # Ready either way: if Ollama is down, later calls fail fast and the app falls back.
            self.ready = True
