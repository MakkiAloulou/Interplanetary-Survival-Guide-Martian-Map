"""Speech-to-text with faster-whisper on the CPU (int8). small.en first; if a short clip takes longer than
settings.whisper_slow_s, later clips use the fallback model (base.en). Loaded lazily, so the tests and CI never need it.
"""

import io
import logging
import threading
import time
from dataclasses import dataclass

from server.config import Settings

log = logging.getLogger("copilot.stt")

# Clips up to this long count toward the "too slow" check (a long ramble is allowed to take longer).
SHORT_CLIP_S = 8.0

# What whisper says for silence or breathing (well-known hallucinations): treated as "nothing heard".
HALLUCINATIONS = {"you", "thank you", "thanks for watching", "thank you for watching", "bye", "okay", "."}


def clean(text: str) -> str:
    t = text.strip()
    return "" if t.lower().strip(" .!?,") in HALLUCINATIONS else t


class STTError(Exception):
    """faster-whisper missing, the audio could not be decoded, or transcription failed."""


@dataclass
class Transcript:
    text: str
    ms: float
    model: str
    audio_s: float


class Transcriber:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.whisper_model
        self._model = None
        self._lock = threading.Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def _ensure(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:
                raise STTError("faster-whisper is not installed (pip install -r server/requirements.txt)") from e
            t0 = time.perf_counter()
            self._model = WhisperModel(self.model_name, device=self.settings.whisper_device, compute_type=self.settings.whisper_compute_type)
            log.info("whisper %s loaded in %.1f s", self.model_name, time.perf_counter() - t0)
        return self._model

    def warmup(self) -> None:
        try:
            import numpy as np

            with self._lock:
                model = self._ensure()
                list(model.transcribe(np.zeros(16000, dtype=np.float32), language="en", beam_size=1)[0])
        except Exception as e:  # noqa: BLE001 - warm-up must never take the server down
            log.warning("whisper warm-up failed (voice unavailable until fixed): %s", e)

    def transcribe(self, audio: bytes, prompt: str = "") -> Transcript:
        t0 = time.perf_counter()
        switched = False
        with self._lock:
            model = self._ensure()
            try:
                segments, info = model.transcribe(
                    io.BytesIO(audio),
                    language="en",
                    beam_size=self.settings.whisper_beam_size,
                    initial_prompt=prompt or None,
                    vad_filter=True,
                    condition_on_previous_text=False,
                    without_timestamps=True,
                )
                text = clean(" ".join(s.text.strip() for s in segments))
            except Exception as e:  # noqa: BLE001 - decoding errors come in many types (av, ctranslate2)
                raise STTError(f"could not transcribe the audio: {e.__class__.__name__}: {e}") from e
            name = self.model_name
            ms = (time.perf_counter() - t0) * 1000
            if ms / 1000 > self.settings.whisper_slow_s and info.duration <= SHORT_CLIP_S and name != self.settings.whisper_fallback_model:
                log.warning("whisper %s took %.1f s for %.1f s of audio: switching to %s", name, ms / 1000, info.duration, self.settings.whisper_fallback_model)
                self.model_name = self.settings.whisper_fallback_model
                self._model = None
                switched = True
        if switched:
            # Load the faster model now, not on the next question.
            threading.Thread(target=self.warmup, daemon=True).start()
        log.info("transcribe %.0f ms (%s, %.1f s audio): %r", ms, name, info.duration, text)
        return Transcript(text=text, ms=ms, model=name, audio_s=round(info.duration, 2))
