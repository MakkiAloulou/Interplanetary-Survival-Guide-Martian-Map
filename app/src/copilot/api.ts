// Calls to the copilot server (server/, reached through the Vite proxy at /api). Every call has a timeout and returns
// null on any failure, so the copilot carries on with its deterministic path.

import type { UnderstandContext, Understood } from './understand'

const BASE = `${import.meta.env.BASE_URL}api/copilot`

export interface Health {
  ok: boolean
  ollama: boolean
  model: string
  model_available: boolean
  llm_ready: boolean
  whisper_model: string | null
  whisper_loaded: boolean
}

async function call<T>(path: string, init: RequestInit, timeoutMs: number): Promise<T | null> {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const r = await fetch(BASE + path, { ...init, signal: ctrl.signal })
    if (!r.ok) return null
    return (await r.json()) as T
  } catch {
    return null
  } finally {
    clearTimeout(timer)
  }
}

const json = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export function fetchHealth(timeoutMs = 2000): Promise<Health | null> {
  return call<Health>('/health', {}, timeoutMs)
}

export interface Transcribed {
  text: string
  /** whisper time on the server, ms */
  ms: number
  model: string | null
}

/** Speech to text on the server (faster-whisper), or null. `prompt` lists the words to expect (place names). */
export async function transcribeRemote(audio: Blob, prompt: string, timeoutMs = 15_000): Promise<Transcribed | null> {
  const form = new FormData()
  form.append('audio', audio, audio.type.includes('ogg') ? 'question.ogg' : audio.type.includes('mp4') ? 'question.m4a' : 'question.webm')
  form.append('prompt', prompt)
  const r = await call<{ ok: boolean; text: string; ms: number; model: string | null }>('/transcribe', { method: 'POST', body: form }, timeoutMs)
  return r?.ok ? { text: r.text, ms: r.ms, model: r.model } : null
}

/** The LLM's understanding, or null (server down, LLM down / slow / invalid): then use the rule parser. */
export async function understandRemote(transcript: string, context: UnderstandContext, timeoutMs = 9000): Promise<Understood | null> {
  const r = await call<{ ok: boolean; understood: Understood | null }>('/understand', json({ transcript, context }), timeoutMs)
  return r?.ok && r.understood ? r.understood : null
}
