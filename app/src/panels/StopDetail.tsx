import { dataUrl } from '../data/load'
import type { CrewTasks } from '../stats/eva'
import type { PovImage, ScienceTarget, Waypoint } from '../types'
import { CloseIcon } from '../ui/icons'
import { Panorama } from '../ui/Panorama'
import { StatusBadge } from '../ui/StatusBadge'
import { sourceParts } from '../ui/sourceLinks'

interface Props {
  station: Waypoint
  /** 0 = habitat, otherwise the stop number */
  number: number
  target: ScienceTarget | null
  pov: PovImage | null
  arriveS: number | null
  /** heading toward the next stop, so the panorama opens facing the way ahead */
  headingDeg: number
  /** crew plan at this stop; null for the habitat */
  crew: CrewTasks | null
  onClose: () => void
}

const elapsed = (s: number) => `T+${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`

/** What the astronaut should expect at a stop: why it matters, what to bring, and what it looks like. */
export function StopDetail({ station, number, target, pov, arriveS, headingDeg, crew, onClose }: Props) {
  return (
    <aside className="card detail" aria-label={`${station.name} details`}>
      <header className="detail-head">
        {number === 0 ? <span className="pin pin-home" aria-hidden="true" /> : <span className="pin">{number}</span>}
        <div className="detail-title">
          <h2>{station.name}</h2>
          <p>
            {number === 0 ? 'Habitat · start and end of the walk' : station.kind === 'science' ? 'Science stop' : 'Via point'}
            {arriveS !== null && number !== 0 && ` · arrive ${elapsed(arriveS)}`}
          </p>
        </div>
        <button type="button" className="icon-btn" aria-label="Close details" onClick={onClose}>
          <CloseIcon size={18} />
        </button>
      </header>

      {pov ? (
        <>
          <Panorama src={dataUrl(pov.url)} aspect={4} initialHeadingDeg={headingDeg} label={station.name} />
          <p className="detail-meta">
            {pov.camera} <StatusBadge status={pov.status ?? 'MOCK'} />
          </p>
        </>
      ) : (
        <p className="detail-empty">No surface image near this point yet.</p>
      )}

      {crew && (
        <section className="detail-body">
          <h3>
            Who does what <StatusBadge status="MODELED" />
          </h3>
          <dl className="crew">
            <dt>EV1</dt>
            <dd>{crew.ev1}</dd>
            <dt>EV2</dt>
            <dd>{crew.ev2}</dd>
            <dt>Rover</dt>
            <dd>{crew.rover}</dd>
          </dl>
        </section>
      )}

      {target && (
        <section className="detail-body">
          <h3>Why stop here</h3>
          <p>{target.why}</p>
          <p className="detail-meta">
            <span>
              {sourceParts(target.source).map((part, i) =>
                'href' in part ? (
                  <a key={i} className="source-link" href={part.href} target="_blank" rel="noopener noreferrer">
                    ({part.label})
                  </a>
                ) : (
                  <span key={i}>{part.text}</span>
                ),
              )}
            </span>{' '}
            <StatusBadge status={target.status} />
          </p>
        </section>
      )}
    </aside>
  )
}
