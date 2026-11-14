"""Request and response models. Field names mirror app/src/copilot (understand.ts, whatIf.ts)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Intent = Literal["extend_stay", "add_stop", "skip_stop", "time_left", "go_home", "unknown"]
INTENTS: tuple[str, ...] = ("extend_stay", "add_stop", "skip_stop", "time_left", "go_home", "unknown")
StopState = Literal["done", "current", "next", "ahead"]

# Longest extra stay the app searches, minutes (MAX_EXTRA_MIN in whatIf.ts).
MAX_MINUTES = 240


class PlaceRef(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)


class StopRef(PlaceRef):
    state: StopState


class UnderstandContext(BaseModel):
    """What the copilot knows about the walk: the current targets and stops (read live from the site data)."""

    targets: list[PlaceRef] = Field(default_factory=list, max_length=200)
    stops: list[StopRef] = Field(default_factory=list, max_length=50)
    current_stop_id: str | None = None
    eva_clock: str = Field(default="", max_length=16)

    def ids(self) -> list[str]:
        seen: dict[str, None] = {}
        for p in [*self.stops, *self.targets]:
            seen.setdefault(p.id, None)
        return list(seen)


class UnderstandRequest(BaseModel):
    transcript: str = Field(min_length=1, max_length=500)
    context: UnderstandContext


class Understood(BaseModel):
    """The LLM's reading of one question. Invalid output (bad JSON, unknown intent, minutes out of range) is rejected."""

    model_config = ConfigDict(extra="ignore")

    intent: Intent
    minutes: int | None = Field(default=None, ge=1, le=MAX_MINUTES)
    target_id: str | None = Field(default=None, max_length=80)
    clarify_question: str | None = Field(default=None, max_length=200)


class UnderstandResponse(BaseModel):
    """ok=false means: use the app's rule parser (Ollama down, too slow, or its answer did not validate)."""

    ok: bool
    source: Literal["llm", "unavailable"]
    understood: Understood | None = None
    error: str | None = None
    ms: float


class HealthResponse(BaseModel):
    ok: bool
    ollama: bool
    model: str
    model_available: bool
    #: the model is loaded and Understand will be tried (false during warm-up)
    llm_ready: bool
    whisper_model: str | None
    whisper_loaded: bool
