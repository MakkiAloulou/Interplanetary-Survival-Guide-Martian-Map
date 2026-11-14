import { findSunset, sunElevationAt } from '../stats/conditions'
import type { Conditions } from '../types'
import { CloseIcon } from '../ui/icons'
import { StatusBadge } from '../ui/StatusBadge'

interface Props {
  conditions: Conditions[]
  startTime: string
  endTime: string | null
  storm: boolean
  onStormChange: (on: boolean) => void
  onClose: () => void
}

const hhmm = (ms: number) => new Date(ms).toISOString().slice(11, 16)

/** Weather, daylight and space weather for the EVA window, plus the solar-storm drill. */
export function ConditionsPanel({ conditions, startTime, endTime, storm, onStormChange, onClose }: Props) {
  const startMs = Date.parse(startTime)
  const endMs = endTime ? Date.parse(endTime) : null
  const at = conditions.reduce((best, c) => (Math.abs(Date.parse(c.time) - startMs) < Math.abs(Date.parse(best.time) - startMs) ? c : best), conditions[0])
  const sunNow = sunElevationAt(conditions, startMs)
  const sunset = findSunset(conditions, startMs)
  const status = at?.status ?? 'MOCK'

  // Sun elevation over the sol, with the EVA window shaded.
  const t0 = Date.parse(conditions[0].time)
  const t1 = Date.parse(conditions[conditions.length - 1].time)
  const W = 308
  const H = 84
  const x = (t: number) => ((t - t0) / (t1 - t0)) * W
  const y = (e: number) => H / 2 - (e / 90) * (H / 2 - 4)
  const line = conditions.map((c, i) => `${i ? 'L' : 'M'}${x(Date.parse(c.time)).toFixed(1)},${y(c.sunElevationDeg).toFixed(1)}`).join('')

  return (
    <section className="card side-panel" aria-label="Conditions">
      <header className="layers-head">
        <h2>Conditions</h2>
        <button type="button" className="icon-btn" aria-label="Close conditions" onClick={onClose}>
          <CloseIcon size={16} />
        </button>
      </header>
      <p className="panel-sub">
        At the planned start, {hhmm(startMs)} UTC <StatusBadge status={status} />
      </p>

      <dl className="readouts">
        <div>
          <dt>Air temperature</dt>
          <dd>{at.tempC.toFixed(0)} °C</dd>
        </div>
        <div>
          <dt>Pressure</dt>
          <dd>{at.pressurePa.toFixed(0)} Pa</dd>
        </div>
        <div>
          <dt>Dust opacity τ</dt>
          <dd>{at.dustTau.toFixed(2)}</dd>
        </div>
        <div>
          <dt>Sun elevation</dt>
          <dd>{sunNow !== null ? `${sunNow.toFixed(0)}°` : '—'}</dd>
        </div>
        <div>
          <dt>Sunset</dt>
          <dd>{sunset !== null ? `${hhmm(sunset)} UTC` : '—'}</dd>
        </div>
        <div>
          <dt>Radiation</dt>
          <dd className={storm ? 'is-alert' : ''}>{storm ? 'Storm alert' : 'Background'}</dd>
        </div>
      </dl>

      <figure className="sunchart">
        <figcaption>Sun over the sol, EVA window shaded</figcaption>
        <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Sun elevation through the sol">
          {endMs && <rect x={x(startMs)} y={0} width={Math.max(2, x(endMs) - x(startMs))} height={H} className="sun-window" />}
          <line x1={0} x2={W} y1={H / 2} y2={H / 2} className="sun-horizon" />
          <path d={line} className="sun-line" />
        </svg>
      </figure>

      <label className="switch">
        <input type="checkbox" role="switch" checked={storm} onChange={(e) => onStormChange(e.target.checked)} />
        <span>
          <strong>Simulate solar storm</strong>
          <small>Raises a radiation alert over the EVA window to rehearse the shelter call. SIMULATED, not a forecast.</small>
        </span>
      </label>
    </section>
  )
}
