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

## Endpoints (`/api/copilot/…`)

| Method | Path | What |
|---|---|---|
| GET | `/health` | Ollama reachable, model pulled, `llm_ready` (false while the model loads), whisper loaded |
| POST | `/understand` | `{transcript, context}` → `{ok, source, understood: {intent, minutes, target_id, clarify_question}}`. `ok: false` means "use the rules". |

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
