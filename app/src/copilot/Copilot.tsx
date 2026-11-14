import { useMemo, useState } from 'react'
import { KeyboardIcon, OfflineIcon, SpeakerIcon, SpeakerOffIcon } from '../ui/icons'
import './copilot.css'
import { CopilotCard } from './CopilotCard'
import { PushToTalk } from './PushToTalk'
import { OLLAMA_MODEL } from './ollama'
import { useDirectOllama, useServerHealth, useServerStages } from './stages'
import { useCopilot, type CopilotLive, type CopilotPlan } from './useCopilot'
import { speechSupported, whisperPrompt } from './voice'

interface Props {
  plan: CopilotPlan
  live: CopilotLive
  /** the dark visor or the daylight tablet */
  variant: 'hud' | 'tablet'
}

/**
 * The what-if copilot in its slot (bottom right of the visor, bottom left of the tablet map): hold to talk, or type.
 * One short answer computed by the planner's own engine; it never changes the plan without Apply or "confirm".
 * When the language model is off, it says so (rules mode) and still answers.
 */
export function Copilot({ plan, live, variant }: Props) {
  const health = useServerHealth()
  const [speakAnswers, setSpeakAnswers] = useState(speechSupported())
  // Off by default: the deterministic template is the answer; LLM wording is optional polish.
  const [llmWording, setLlmWording] = useState(false)
  const [typing, setTyping] = useState(false)
  const direct = useDirectOllama(!!health)
  const stages = useServerStages(health, speakAnswers, llmWording, direct)
  const copilot = useCopilot(plan, live, stages)
  const [text, setText] = useState('')
  const prompt = useMemo(() => whisperPrompt(plan.ctx), [plan.ctx])
  const { phase, answer, timing, error } = copilot
  const busy = phase === 'thinking' || phase === 'transcribing'
  // Fallback states, said in words: no server → typed only (with the remote model, or rules); server without the
  // model → rules.
  const fallback = !health
    ? direct
      ? `Typed questions: ${OLLAMA_MODEL} on the crew laptop (remote)`
      : 'Typed only, rules mode: language model not reachable'
    : !health.llm_ready
      ? 'Rules mode: language model off'
      : null
  const showInput = typing || !health

  return (
    <div className={`copilot is-${variant}`} role="region" aria-label="What-if copilot">
      {answer && (
        <CopilotCard
          answer={answer}
          timing={timing}
          variant={variant}
          canApply={copilot.canApply}
          drill={live.drill}
          onApply={copilot.apply}
          onDismiss={copilot.dismiss}
          onPick={(name) => void copilot.ask(name)}
        />
      )}
      {error && (
        <p className="copilot-error" role="status">
          <OfflineIcon size={20} /> {error}
        </p>
      )}

      {showInput && (
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
            placeholder="Can we stay 20 more minutes?"
            aria-label="Ask the copilot"
            autoFocus={typing}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.stopPropagation()}
          />
          <button type="submit" className="copilot-btn is-primary" disabled={!text.trim() || busy}>
            Ask
          </button>
        </form>
      )}

      <div className="copilot-bar">
        {health && <PushToTalk copilot={copilot} prompt={prompt} ready={health.whisper_loaded} />}
        {health && (
          <button type="button" className="copilot-btn is-toggle" aria-pressed={typing} aria-label="Type a question" onClick={() => setTyping((v) => !v)}>
            <KeyboardIcon size={24} />
            <span>Type</span>
          </button>
        )}
        {speechSupported() && (
          <button
            type="button"
            className="copilot-btn is-toggle"
            aria-pressed={speakAnswers}
            aria-label="Speak answers"
            onClick={() => {
              if (speakAnswers) copilot.stopSpeaking()
              setSpeakAnswers((v) => !v)
            }}
          >
            {speakAnswers ? <SpeakerIcon size={24} /> : <SpeakerOffIcon size={24} />}
            <span>{speakAnswers ? 'Voice on' : 'Voice off'}</span>
          </button>
        )}
        {variant === 'tablet' && typing && health?.llm_ready && (
          <button type="button" className="copilot-btn is-toggle" aria-pressed={llmWording} onClick={() => setLlmWording((v) => !v)}>
            <span>LLM wording {llmWording ? 'on' : 'off'}</span>
          </button>
        )}
      </div>

      <p className="copilot-mode">
        {fallback && (
          <span className="copilot-fallback">
            <OfflineIcon size={18} /> {fallback}
          </span>
        )}
        <span>Numbers come from the planner’s engine{variant === 'tablet' && health?.llm_ready ? `; ${health.model} only reads the question` : ''}.</span>
      </p>
    </div>
  )
}
