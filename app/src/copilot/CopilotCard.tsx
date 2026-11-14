import { formatDistance, formatDuration } from '../stats/format'
import { StatusBadge } from '../ui/StatusBadge'
import type { Answer, Timing } from './useCopilot'
import type { Binding, WhatIfResult } from './whatIf'

/** The binding limit, as a label. */
const LIMIT_LABEL: Record<Binding, string> = {
  O2_BUDGET: 'O₂ reserve',
  POINT_OF_NO_RETURN: 'Point of no return',
  SUNSET: 'Sunset margin',
  RADIATION: 'Radiation alert',
  DARK_START: 'Daylight',
  NO_PATH: 'No walkable path',
  NO_GO_CELLS: 'Impassable ground',
  NO_CONDITIONS: 'Conditions data',
  DOSE: 'Radiation dose',
  STEEP_SECTIONS: 'Steep ground',
  SAND: 'Loose sand',
  BOULDERS: 'Boulders',
  NO_HAVEN: 'No safe haven',
  ALREADY_LEFT: 'Already left',
  ALREADY_PLANNED: 'Already on the plan',
  ALREADY_VISITED: 'Already visited',
  NOT_ON_PLAN: 'Not on the plan',
  UNKNOWN_PLACE: 'Unknown place',
  NO_PATH_TO_TARGET: 'Cut off',
  WALK_DONE: 'Walk complete',
}

const VERDICT_LABEL = { GO: 'GO', PARTIAL: 'PARTLY', NO_GO: 'NO-GO' } as const

const min = (m: number) => formatDuration(m * 60)

/** The one number that answers the question, and what it means. */
function headline(r: WhatIfResult): { value: string; label: string } {
  const n = r.numbers
  switch (r.intent) {
    case 'extend_stay':
      return { value: min(r.allowed_min ?? 0), label: r.requested_min !== null ? `you can stay (asked ${r.requested_min} min)` : 'you can stay' }
    case 'add_stop':
      return { value: `+${min(n.extra_min ?? 0)}`, label: 'added to the walk (and O₂)' }
    case 'skip_stop':
      return { value: `−${min(n.saved_min ?? 0)}`, label: 'saved (time and O₂)' }
    case 'time_left':
      return { value: min(n.head_back_in_min ?? 0), label: 'until you must turn back' }
    case 'go_home':
      return { value: min(n.to_safety_min ?? 0), label: `to ${r.subject ?? 'safety'}${n.distance_m ? ` · ${formatDistance(n.distance_m)}` : ''}` }
    default:
      return { value: '—', label: '' }
  }
}

interface Props {
  answer: Answer
  timing: Timing
  canApply: boolean
  onApply: () => void
  onDismiss: () => void
}

/** The answer card: what was asked, the verdict, the one number, the limit that binds, then the supporting numbers. */
export function CopilotCard({ answer, timing, canApply, onApply, onDismiss }: Props) {
  const r = answer.result
  const head = r ? headline(r) : null
  const n = r?.numbers
  return (
    <section className={`copilot-card ${r ? `is-${r.verdict.toLowerCase()}` : 'is-info'}`} aria-live="polite" aria-label="Copilot answer">
      <header className="copilot-card-head">
        <p className="copilot-question" title="What you asked">
          “{answer.question}”
        </p>
        <button type="button" className="copilot-x" aria-label="Dismiss answer" onClick={onDismiss}>
          ×
        </button>
      </header>

      {r && head && (
        <div className="copilot-headline">
          <span className={`copilot-verdict verdict-${r.verdict.toLowerCase()}`}>{VERDICT_LABEL[r.verdict]}</span>
          <strong className="copilot-big">{head.value}</strong>
          <span className="copilot-big-label">{head.label}</span>
        </div>
      )}

      <p className="copilot-text">{answer.text}</p>

      {answer.clarify && (
        <ul className="copilot-options" aria-label="Say or type one of these">
          {answer.clarify.map((o) => (
            <li key={o.id}>{o.name}</li>
          ))}
        </ul>
      )}

      {r && n && (
        <dl className="copilot-numbers">
          {r.binding && (
            <div>
              <dt>Limit</dt>
              <dd>{LIMIT_LABEL[r.binding]}</dd>
            </div>
          )}
          {n.head_back_by && (
            <div>
              <dt>{r.intent === 'skip_stop' ? 'Back by' : r.next_is_home || r.intent === 'time_left' ? 'Head back by' : 'Move on by'}</dt>
              <dd>
                {n.head_back_by}
                {n.head_back_in_min !== null && <small> in {min(n.head_back_in_min)}</small>}
              </dd>
            </div>
          )}
          <div>
            <dt>O₂ left</dt>
            <dd>{min(n.o2_left_min)}</dd>
          </div>
          {r.intent === 'go_home' && n.spare_o2_min !== undefined ? (
            <div>
              <dt>Spare O₂ on arrival</dt>
              <dd>{n.spare_o2_min < 0 ? `short ${min(-n.spare_o2_min)}` : min(n.spare_o2_min)}</dd>
            </div>
          ) : (
            <div>
              <dt>Point of no return</dt>
              <dd>{Number.isFinite(n.pnr_in_min) ? (n.pnr_in_min < 0 ? 'passed' : `in ${min(n.pnr_in_min)}`) : 'no way back'}</dd>
            </div>
          )}
          {n.sunset_margin_min !== null && r.intent !== 'go_home' && (
            <div>
              <dt>Back before sunset</dt>
              <dd>{n.sunset_margin_min < 0 ? `${min(-n.sunset_margin_min)} late` : min(n.sunset_margin_min)}</dd>
            </div>
          )}
          {r.intent !== 'go_home' && (
            <div>
              <dt>EVA dose</dt>
              <dd>{n.dose_msv.toFixed(2)} mSv</dd>
            </div>
          )}
        </dl>
      )}

      <footer className="copilot-card-foot">
        {r && <StatusBadge status={r.status} />}
        {canApply && (
          <button type="button" className="copilot-apply" onClick={onApply}>
            {r?.apply?.kind === 'go_home' ? 'Start abort' : 'Apply'}
          </button>
        )}
        {answer.applied && <span className="copilot-applied">Applied</span>}
        {r?.apply && !canApply && !answer.applied && r.apply.kind !== 'go_home' && <span className="copilot-note">Answer only: change the plan in the planner.</span>}
        {answer.wording?.source === 'llm' && <small className="copilot-note" title="Reworded by the LLM; every number checked against the engine's result">LLM wording, numbers checked</small>}
        {timing.totalMs !== undefined && (
          <small className="copilot-timing" title="Time per stage">
            {timing.sttMs !== undefined && `voice ${(timing.sttMs / 1000).toFixed(1)} s · `}
            {timing.source ?? 'rules'} {((timing.understandMs ?? 0) / 1000).toFixed(1)} s · total {(timing.totalMs / 1000).toFixed(1)} s
          </small>
        )}
      </footer>
    </section>
  )
}
