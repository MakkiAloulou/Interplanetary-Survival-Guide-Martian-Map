import { useMemo, useState } from 'react'
import type { Health } from './api'
import './copilot.css'
import { CopilotCard } from './CopilotCard'
import { PushToTalk } from './PushToTalk'
import { useServerHealth, useServerStages } from './stages'
import { useCopilot, type CopilotLive, type CopilotPlan, type Phase } from './useCopilot'
import { speechSupported, whisperPrompt } from './voice'

interface Props {
  plan: CopilotPlan
  live: CopilotLive
  /** the dark visor or the daylight tablet */
  variant: 'hud' | 'tablet'
}

const PHASE_LABEL: Record<Phase, string> = {
  idle: 'Hold to talk, or type',
  listening: 'Listening…',
  transcribing: 'Hearing you…',
  thinking: 'Checking the budget…',
  speaking: 'Answering…',
  error: 'Try again',
}

/** Which understanding path is live, said plainly (judges and crew both see it). */
function serverLine(h: Health | null): string {
  if (!h) return 'offline mode: typed questions, rules and templates (copilot server not running)'
  if (!h.ollama || !h.model_available) return `rules mode: ${h.model} not available in Ollama`
  if (!h.llm_ready) return `rules mode while ${h.model} loads`
  return `${h.model} on this laptop · numbers from the planner's engine`
}

/**
 * The what-if copilot docked in the HUD or the tablet: ask by voice (push-to-talk) or by typing, get one short answer
 * computed by the planner's own engine. It never changes the plan without an explicit Apply.
 */
export function Copilot({ plan, live, variant }: Props) {
  const health = useServerHealth()
  const [speakAnswers, setSpeakAnswers] = useState(speechSupported())
  // Off by default: the deterministic template is the answer; LLM wording is optional polish.
  const [llmWording, setLlmWording] = useState(false)
  const stages = useServerStages(health, speakAnswers, llmWording)
  const copilot = useCopilot(plan, live, stages)
  const [text, setText] = useState('')
  const prompt = useMemo(() => whisperPrompt(plan.ctx), [plan.ctx])
  const { phase, answer, timing, error } = copilot
  return (
    <div className={`copilot is-${variant}`} role="region" aria-label="What-if copilot">
      {answer && <CopilotCard answer={answer} timing={timing} canApply={copilot.canApply} onApply={copilot.apply} onDismiss={copilot.dismiss} />}
      {error && <p className="copilot-error">{error}</p>}
      <div className="copilot-bar">
        {health && <PushToTalk copilot={copilot} prompt={prompt} ready={health.whisper_loaded} />}
        <form
          className="copilot-form"
          onSubmit={(e) => {
            e.preventDefault()
            void copilot.ask(text)
            setText('')
          }}
        >
          <input
            className="copilot-input"
            value={text}
            placeholder={'Type: "Can we stay 20 more minutes?"'}
            aria-label="Ask the copilot"
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
          />
          <button type="submit" className="copilot-ask" disabled={!text.trim() || phase === 'thinking' || phase === 'transcribing'}>
            Ask
          </button>
        </form>
      </div>
      <p className={`copilot-phase phase-${phase}`} aria-live="polite">
        {PHASE_LABEL[phase]}
        <span className="copilot-mode"> · {serverLine(health)}</span>
        {speechSupported() && (
          <label className="copilot-speak">
            <input type="checkbox" checked={speakAnswers} onChange={(e) => setSpeakAnswers(e.target.checked)} /> speak answers
          </label>
        )}
        {health?.llm_ready && (
          <label className="copilot-speak" title="The LLM rewords the answer; any changed number or verdict falls back to the template">
            <input type="checkbox" checked={llmWording} onChange={(e) => setLlmWording(e.target.checked)} /> LLM wording
          </label>
        )}
      </p>
    </div>
  )
}
