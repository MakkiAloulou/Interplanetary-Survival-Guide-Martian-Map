import { useState } from 'react'
import { dataUrl } from '../data/load'
import type { CrewTasks } from '../stats/eva'
import { sphericalDistanceM } from '../stats/stats'
import type { PovImage, ScienceTarget, Waypoint } from '../types'
import { CloseIcon } from '../ui/icons'
import { Panorama } from '../ui/Panorama'
import { StatusBadge } from '../ui/StatusBadge'
import { SourceLine } from '../ui/SourceLine'

interface Props {
  station: Waypoint
  /** 0 = habitat, otherwise the stop number */
  number: number
  target: ScienceTarget | null
  /** Curiosity photos taken at (or next to) this station */
  photos: PovImage[]
  /** a 360° view at this station, or null */
  panorama: PovImage | null
  arriveS: number | null
  /** heading toward the next stop, so a panorama opens facing the way ahead */
  headingDeg: number
  /** crew plan at this stop; null for the habitat */
  crew: CrewTasks | null
  onClose: () => void
}

const elapsed = (s: number) => `T+${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`

/** "at the stop" or "N m from the stop": where a photo was taken, relative to the station. */
function offset(pov: PovImage, station: Waypoint): string {
  const m = Math.round(sphericalDistanceM(pov, station))
  return m < 1 ? 'at the stop' : `${m} m from the stop`
}

/** Photos taken at this spot: one large, the others as thumbnails to switch to. */
function PhotoGallery({ povs, station }: { povs: PovImage[]; station: Waypoint }) {
  const [index, setIndex] = useState(0)
  const pov = povs[Math.min(index, povs.length - 1)]
  return (
    <figure className="photos">
      <img className="photo-main" src={dataUrl(pov.url)} alt={`${station.name}: ${pov.camera}, sol ${pov.sol}`} />
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
          {pov.camera} · Curiosity sol {pov.sol} · {offset(pov, station)}
        </span>
        <StatusBadge status={pov.status ?? 'MOCK'} />
      </figcaption>
      <p className="detail-meta photo-source">
        <SourceLine source={pov.source} />
      </p>
    </figure>
  )
}

/** The station's views: real photos and a rendered 360° view, with a switch when both exist. */
function StopViews({ station, photos, panorama, headingDeg }: { station: Waypoint; photos: PovImage[]; panorama: PovImage | null; headingDeg: number }) {
  const [view, setView] = useState<'photos' | 'panorama'>(photos.length > 0 ? 'photos' : 'panorama')
  if (photos.length === 0 && !panorama) return <p className="detail-empty">No surface image near this point yet.</p>
  const show = view === 'photos' && photos.length > 0 ? 'photos' : panorama ? 'panorama' : 'photos'
  return (
    <>
      {photos.length > 0 && panorama && (
        <div className="segmented view-switch" role="radiogroup" aria-label="Views at this stop">
          <button type="button" role="radio" aria-checked={show === 'photos'} onClick={() => setView('photos')}>
            Photos
          </button>
          <button type="button" role="radio" aria-checked={show === 'panorama'} onClick={() => setView('panorama')}>
            360° view
          </button>
        </div>
      )}
      {show === 'photos' ? (
        <PhotoGallery povs={photos} station={station} />
      ) : (
        panorama && (
          <figure className="photos">
            <Panorama src={dataUrl(panorama.url)} aspect={4} initialHeadingDeg={headingDeg} label={station.name} />
            <figcaption className="detail-meta">
              <span className="photo-camera">{panorama.camera}, facing the way ahead</span>
              <StatusBadge status={panorama.status ?? 'MOCK'} />
            </figcaption>
            <p className="detail-meta photo-source">
              <SourceLine source={panorama.source} />
            </p>
          </figure>
        )
      )}
    </>
  )
}

/** What the astronaut should expect at a stop: why it matters, what to bring, and what it looks like. */
export function StopDetail({ station, number, target, photos, panorama, arriveS, headingDeg, crew, onClose }: Props) {
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

      <StopViews key={station.id} station={station} photos={photos} panorama={panorama} headingDeg={headingDeg} />

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
