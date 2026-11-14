"""Server settings, from environment variables with working defaults. Nothing secret lives in the repo."""

import os
from dataclasses import dataclass


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


@dataclass(frozen=True)
class Settings:
    # Ollama, running on the same machine (localhost). The copilot works without it (rules + templates).
    ollama_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3:8b"
    # Understand must answer within this, or the app falls back to its rule parser. Spec: 8 s.
    llm_timeout_s: float = 8.0
    # Explain is optional polish: a short wait, then the deterministic template is used.
    explain_timeout_s: float = 4.0
    # faster-whisper on the CPU, int8. small.en first; base.en once a short clip takes longer than whisper_slow_s.
    whisper_model: str = "small.en"
    whisper_fallback_model: str = "base.en"
    whisper_slow_s: float = 3.0
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    # Beam 5 with the place-name prompt fixed "fastest way back to the habitat" (beam 1: "first story back to the
    # Avatar") at ~2% more time on this laptop (1.48 vs 1.46 s per clip, small.en CPU int8).
    whisper_beam_size: int = 5
    # Load the models at start-up so the first question is not slow.
    warmup: bool = True
    host: str = "127.0.0.1"
    port: int = 8787

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            ollama_url=_env("COPILOT_OLLAMA_URL", cls.ollama_url),
            model=_env("COPILOT_MODEL", cls.model),
            llm_timeout_s=float(_env("COPILOT_LLM_TIMEOUT_S", str(cls.llm_timeout_s))),
            explain_timeout_s=float(_env("COPILOT_EXPLAIN_TIMEOUT_S", str(cls.explain_timeout_s))),
            whisper_model=_env("COPILOT_WHISPER_MODEL", cls.whisper_model),
            whisper_fallback_model=_env("COPILOT_WHISPER_FALLBACK_MODEL", cls.whisper_fallback_model),
            whisper_slow_s=float(_env("COPILOT_WHISPER_SLOW_S", str(cls.whisper_slow_s))),
            whisper_device=_env("COPILOT_WHISPER_DEVICE", cls.whisper_device),
            whisper_compute_type=_env("COPILOT_WHISPER_COMPUTE_TYPE", cls.whisper_compute_type),
            whisper_beam_size=int(_env("COPILOT_WHISPER_BEAM_SIZE", str(cls.whisper_beam_size))),
            warmup=_env("COPILOT_WARMUP", "1") not in ("0", "false", "no"),
            host=_env("COPILOT_HOST", cls.host),
            port=int(_env("COPILOT_PORT", str(cls.port))),
        )
