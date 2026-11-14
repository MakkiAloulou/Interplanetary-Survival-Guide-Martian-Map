import type { TrackPoint } from '../stats/stats'
import { formatDistance } from '../stats/format'

interface Props {
  track: TrackPoint[]
  hoverIndex: number | null
  onHover: (index: number | null) => void
}

const W = 368
const H = 92
const PAD_Y = 8

/** Elevation along the walk. Hover shows distance and elevation and marks the spot on the map. */
export function ElevationProfile({ track, hoverIndex, onHover }: Props) {
  const total = track[track.length - 1].distanceM || 1
  let min = Infinity
  let max = -Infinity
  for (const p of track) {
    min = Math.min(min, p.elevationM)
    max = Math.max(max, p.elevationM)
  }
  const span = Math.max(max - min, 1)
  const x = (d: number) => (d / total) * W
  const y = (e: number) => PAD_Y + (1 - (e - min) / span) * (H - 2 * PAD_Y)

  const step = Math.max(1, Math.floor(track.length / 240))
  const pts = track.filter((_, i) => i % step === 0 || i === track.length - 1)
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${x(p.distanceM).toFixed(1)},${y(p.elevationM).toFixed(1)}`).join('')
  const stops = track.map((p, i) => ({ p, i })).filter(({ p }) => p.departS > p.arriveS)
  const hover = hoverIndex !== null ? track[hoverIndex] : null

  function indexAt(clientX: number, rect: DOMRect): number {
    const d = ((clientX - rect.left) / rect.width) * total
    let lo = 0
    let hi = track.length - 1
    while (lo < hi) {
      const mid = (lo + hi) >> 1
      if (track[mid].distanceM < d) lo = mid + 1
      else hi = mid
    }
    return lo
  }

  return (
    <figure className="profile">
      <figcaption>
        <span>Elevation</span>
        <span>
          {hover ? `${formatDistance(hover.distanceM)} · ${hover.elevationM.toFixed(0)} m` : `${min.toFixed(0)} to ${max.toFixed(0)} m`}
        </span>
      </figcaption>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="none"
        role="img"
        aria-label={`Elevation profile from ${min.toFixed(0)} to ${max.toFixed(0)} metres over ${formatDistance(total)}`}
        onPointerMove={(e) => onHover(indexAt(e.clientX, e.currentTarget.getBoundingClientRect()))}
        onPointerLeave={() => onHover(null)}
      >
        <path d={`${line}L${W},${H}L0,${H}Z`} className="profile-fill" />
        <path d={line} className="profile-line" vectorEffect="non-scaling-stroke" />
        {stops.map(({ p, i }) => (
          <line key={i} x1={x(p.distanceM)} x2={x(p.distanceM)} y1={0} y2={H} className="profile-stop" vectorEffect="non-scaling-stroke" />
        ))}
        {hover && <line x1={x(hover.distanceM)} x2={x(hover.distanceM)} y1={0} y2={H} className="profile-cursor" vectorEffect="non-scaling-stroke" />}
      </svg>
      <div className="profile-axis" aria-hidden="true">
        <span>0</span>
        {stops.map(({ p }, k) => (
          <span key={k} className="profile-pin" style={{ left: `${(p.distanceM / total) * 100}%` }}>
            {k + 1}
          </span>
        ))}
        <span>{formatDistance(total)}</span>
      </div>
    </figure>
  )
}
