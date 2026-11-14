// The copilot's server-backed stages, each falling back to the deterministic path: LLM understanding → rule parser.

import { useEffect, useMemo, useState } from 'react'
import { fetchHealth, understandRemote, type Health } from './api'
import { forSpeech } from './templates'
import { resolve } from './understand'
import { understandByRules, type Stages } from './useCopilot'
import { speak, stopSpeaking } from './voice'

/** How often the dock re-checks the server, ms (it may be started after the app, or the model may still load). */
const HEALTH_EVERY_MS = 15_000

/** Server health, polled while the dock is open; null while the server is unreachable. */
export function useServerHealth(): Health | null {
  const [health, setHealth] = useState<Health | null>(null)
  useEffect(() => {
    let alive = true
    const check = () => fetchHealth().then((h) => alive && setHealth(h))
    check()
    const id = setInterval(check, HEALTH_EVERY_MS)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])
  return health
}

/**
 * Stages for the current server state: the LLM is only asked when it is loaded (otherwise rules, at once); answers are
 * spoken by the browser's speech synthesis when `speakAnswers` is on.
 */
export function useServerStages(health: Health | null, speakAnswers: boolean): Stages {
  return useMemo<Stages>(
    () => ({
      understand: async (text, uctx) => {
        if (health?.llm_ready) {
          const u = await understandRemote(text, uctx)
          if (u) return { resolution: resolve(text, u, uctx), source: 'llm' }
        }
        return understandByRules(text, uctx)
      },
      speak: speakAnswers ? (text) => speak(forSpeech(text)) : undefined,
      stopSpeaking,
    }),
    [health?.llm_ready, speakAnswers],
  )
}
