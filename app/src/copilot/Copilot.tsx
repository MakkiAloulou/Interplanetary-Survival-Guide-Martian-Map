import { useState } from 'react'
import type { Health } from './api'
import './copilot.css'
import { CopilotCard } from './CopilotCard'
import { useServerHealth, useServerStages } from './stages'
import { useCopilot, type CopilotLive, type CopilotPlan, type Phase } from './useCopilot'

interface Props {
  plan: CopilotPlan
  live: CopilotLive
  /** the dark visor or the daylight tablet */
  variant: 'hud' | 'tablet'
}

/** Which understanding path is live, said plainly (judges and crew both see it). */
function serverLine(h: Health | null): string {
  if (!h) return 'Offline mode: rules and templates (copilot server not running)'
  if (!h.ollama || !h.model_available) return `Rules mode: ${h.model} not available in Ollama`
  if (!h.llm_ready) return `Rules mode while ${h.model} loads`
  return `Understanding: ${h.model} on this laptop · numbers from the planner's engine`
}

const PHASE_LABEL: Record<Phase, string> = {
  idle: 'Ask a what-if',
  listening: 'Listening…',
  transcribing: 'Hearing you…',
  thinking: 'Checking the budget…',
  speaking: 'Answering…',
  error: 'Something went wrong',
}

/**
 * The what-if copilot docked in the HUD or the tablet: ask by voice (push-to-talk) or by typing, get one short answer
 * computed by the planner's own engine. It never changes the plan without an explicit Apply.
 */
export function Copilot({ plan, live, variant }: Props) {
  const health = useServerHealth()
  const stages = useServerStages(health)
  const copilot = useCopilot(plan, live, stages)
  const [text, setText] = useState('')
  const { phase, answer, timing, error } = copilot
  return (
    <div className={`copilot is-${variant}`} role="region" aria-label="What-if copilot">
      {answer && <CopilotCard answer={answer} timing={timing} canApply={copilot.canApply} onApply={copilot.apply} onDismiss={copilot.dismiss} />}
      {error && <p className="copilot-error">{error}</p>}
      <div className="copilot-bar">
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
          <button type="submit" className="copilot-ask" disabled={!text.trim() || (phase !== 'idle' && phase !== 'error')}>
            Ask
          </button>
        </form>
      </div>
      <p className={`copilot-phase phase-${phase}`} aria-live="polite">
        {PHASE_LABEL[phase]}
        <span className="copilot-mode"> · {serverLine(health)}</span>
      </p>
    </div>
  )
}
