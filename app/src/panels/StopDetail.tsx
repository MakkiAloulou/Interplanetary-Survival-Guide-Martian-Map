import { useState } from 'react'
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
  /** surface images near this station, nearest first */
  povs: PovImage[]
  arriveS: number | null
  /** heading toward the next stop, so a panorama opens facing the way ahead */
  headingDeg: number
  /** crew plan at this stop; null for the habitat */
  crew: CrewTasks | null
  onClose: () => void
}

const elapsed = (s: number) => `T+${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`

/** A provenance line with its URLs shown as short "(source)" links. */
function SourceLine({ source }: { source: string }) {
  return (
    <span>
      {sourceParts(source).map((part, i) =>
        'href' in part ? (
          <a key={i} className="source-link" href={part.href} target="_blank" rel="noopener noreferrer">
            ({part.label})
          </a>
        ) : (
          <span key={i}>{part.text}</span>
        ),
      )}
    </span>
  )
}

/** Photos taken at this spot: one large, the others as thumbnails to switch to. */
function PhotoGallery({ povs, label }: { povs: PovImage[]; label: string }) {
  const [index, setIndex] = useState(0)
  const pov = povs[Math.min(index, povs.length - 1)]
  return (
    <figure className="photos">
      <img className="photo-main" src={dataUrl(pov.url)} alt={`${label}: ${pov.camera}, sol ${pov.sol}`} />
      {povs.length > 1 && (
        <div className="photo-thumbs" role="group" aria-label="Surface images at this stop">
          {povs.map((p, i) => (
            <button
              key={p.url}
              type="button"
              className="photo-thumb"
              aria-pressed={i === index}
              aria-label={`${p.camera}, sol ${p.sol}`}
              onClick={() => setIndex(i)}
            >
              <img src={dataUrl(p.thumbnailUrl)} alt="" />
            </button>
          ))}
        </div>
      )}
      <figcaption className="detail-meta">
        <span className="photo-camera">
          {pov.camera} · sol {pov.sol}
        </span>
        <StatusBadge status={pov.status ?? 'MOCK'} />
      </figcaption>
      <p className="detail-meta photo-source">
        <SourceLine source={pov.source} />
      </p>
    </figure>
  )
}

/** What the astronaut should expect at a stop: why it matters, what to bring, and what it looks like. */
export function StopDetail({ station, number, target, povs, arriveS, headingDeg, crew, onClose }: Props) {
  const panorama = povs[0]?.isPanorama ? povs[0] : null
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

      {panorama ? (
        <>
          <Panorama src={dataUrl(panorama.url)} aspect={4} initialHeadingDeg={headingDeg} label={station.name} />
          <p className="detail-meta">
            {panorama.camera} <StatusBadge status={panorama.status ?? 'MOCK'} />
          </p>
        </>
      ) : povs.length > 0 ? (
        <PhotoGallery key={station.id} povs={povs} label={station.name} />
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
            <SourceLine source={target.source} /> <StatusBadge status={target.status} />
          </p>
        </section>
      )}
    </aside>
  )
}
