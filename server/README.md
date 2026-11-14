# Copilot server

Speech-to-text and the LLM stages of the what-if copilot in the HUD and the tablet. The answers themselves (every
number, GO / PARTIAL / NO-GO, the limit that binds) come from the planner's engine in the browser
(`app/src/copilot/whatIf.ts`). The LLM only turns a question into `{intent, minutes, target_id}` and may rephrase the
answer. It never decides safety.

Everything still works with this server off, or with Ollama off. The app then uses its rule parser
(`app/src/copilot/understand.ts`) and its spoken-answer templates (`app/src/copilot/templates.ts`).

## Run

From the repo root, in the `marswalk` conda env (Windows miniconda, next to Ollama):

```bash
conda activate marswalk
pip install -r server/requirements.txt       # once
ollama pull qwen3:8b                         # once, ~5 GB
python -m server                             # http://127.0.0.1:8787, model warm-up ~20 s
```

Then run the app (`cd app && npm run dev`). Vite proxies `/api` to the server.

## The deployed app (Vercel) with the laptop's model

The static site has no copilot server, so its browser asks Ollama directly (`app/src/copilot/ollama.ts`). It sends the
same prompt and schema as `server/llm.py` and applies the same checks, with the rules as fallback. Voice stays
laptop-only. Browsers need **https**, so the laptop's Ollama is reached through a Cloudflare quick tunnel:

```powershell
winget install Cloudflare.cloudflared            # once
powershell -ExecutionPolicy Bypass -File server\start-llm-tunnel.ps1
```

The script:

1. allows the app's origins in `OLLAMA_ORIGINS`;
2. restarts Ollama and warms `qwen3:8b`;
3. opens the tunnel, with the Host header rewritten to localhost, which Ollama requires;
4. prints `https://…vercel.app/?ollama=https://<name>.trycloudflare.com`.

Open that link once per browser; the address is remembered there, and `?ollama=off` forgets it. A fixed address can
also be built in with `VITE_OLLAMA_URL` (and `VITE_OLLAMA_MODEL`) in the Vercel project settings.

The tunnel has no password. Browsers from other websites are refused (CORS), but anyone with the address can call
the model directly, so run it only while you need it (Ctrl+C closes it). The address changes on every run.

## Endpoints (`/api/copilot/…`)

| Method | Path | What |
|---|---|---|
| GET | `/health` | Ollama reachable, model pulled, `llm_ready` (false while the model loads), whisper loaded |
| POST | `/transcribe` | multipart `audio` (the push-to-talk clip, WebM/Opus from MediaRecorder) + `prompt` (place names to expect) → `{ok, text, ms, model}` |
| POST | `/understand` | `{transcript, context}` → `{ok, source, understood: {intent, minutes, target_id, clarify_question}}`. `ok: false` means "use the rules". |
| POST | `/explain` | `{template, result}` → `{text, source}`: the LLM's rewording if it passes the number guard, otherwise the template |

**Number guard** (`server/guard.py`; the app runs the same check again in `app/src/copilot/guard.ts`). A rewording
is used only if:

- every number in it appears in the `WhatIfResult` or the template;
- it spells out no number;
- it keeps the template's lead word (Yes / No / Partly);
- it is at most 30 words.

Otherwise the template is said. In the app, LLM wording is off by default; the deterministic template is the answer.

Speech-to-text is faster-whisper on the CPU, int8, beam 5, with VAD. Silence hallucinations ("you", "thank you")
count as nothing heard. `initial_prompt` is the app's list of current place names plus the walk vocabulary. On this
laptop, `small.en` takes 1.2–1.6 s per 3–5 s clip. If a short clip ever takes more than 3 s, the server switches to
`base.en` and loads it in the background.

Understand uses Ollama structured output. The JSON schema's `target_id` enum is built from the **context of each
request** (the current targets and stops), so nothing is hard-coded. Settings: `think: false`, temperature 0, 8 s
timeout. The reply is validated with Pydantic, and a target ID that isn't in the context is dropped. While the model
is still loading, questions go straight to the rules instead of queueing in Ollama.

## Settings (environment variables)

| Variable | Default |
|---|---|
| `COPILOT_OLLAMA_URL` | `http://127.0.0.1:11434` |
| `COPILOT_MODEL` | `qwen3:8b` |
| `COPILOT_LLM_TIMEOUT_S` | `8` |
| `COPILOT_EXPLAIN_TIMEOUT_S` | `4` |
| `COPILOT_WHISPER_MODEL` / `COPILOT_WHISPER_FALLBACK_MODEL` | `small.en` / `base.en` |
| `COPILOT_WHISPER_SLOW_S` | `3` (switch to the fallback model above this) |
| `COPILOT_WHISPER_DEVICE` / `COPILOT_WHISPER_COMPUTE_TYPE` | `cpu` / `int8` |
| `COPILOT_HOST` / `COPILOT_PORT` | `127.0.0.1` / `8787` |
| `COPILOT_WARMUP` | `1` |
| `COPILOT_API_URL` (read by `app/vite.config.ts`) | `http://127.0.0.1:8787` |

## Tests

```bash
python -m pytest server/tests -q      # Ollama and whisper mocked; this is what CI runs
```

## Eval

`server/tests/phrasings.json` holds 34 crew questions, each with its expected intent, minutes and place:

- fillers ("uh", "um") and long radio calls;
- accents ("tventy", "skeep Nevado Sahama") and real ASR errors ("I will long until we must turn back");
- the ambiguous "ridge".

The same file scores the LLM against the real Ollama, and the app's rule parser in
`app/src/copilot/phrasings.test.ts`, which runs in CI with a floor.

```bash
python -m server.eval_phrasings --runs 2     # needs Ollama with the model pulled
```

Measured 2026-11-14 on qwen3:8b, RTX 5050 Laptop (8 GB), 2 runs × 34:

| | LLM (raw) | Rules (fallback) |
|---|---|---|
| fully correct | 64/68 (94%) | 32/34 (94%) |
| intent | 68/68 (100%) | 33/34 |
| place, when one is named | 42/42 (100%) | — |
| minutes (extend_stay) | 18/22 (82%) | — |
| latency | mean 687 ms · p90 758 ms · max 861 ms | < 1 ms |

The LLM's four misses are all invented minutes. It answers 30 for "can we stay longer?" when no number was said.
The app drops LLM minutes unless the words contain a number cue (`hasNumberCue`, unit-tested on exactly these
phrasings). The LLM never asked a clarifying question on its own (0/2); the app's place matcher asks for "the
ridge" every time. The rules miss the two accented phrasings, which is where the LLM helps.
