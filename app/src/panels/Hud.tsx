import { useEffect, useRef, useState } from 'react'
import { compassPoint, initialBearingDeg, positionAt } from '../stats/eva'
import { formatDistance, formatDuration } from '../stats/format'
import type { EvaParams, Reason } from '../stats/goNoGo'
import { sphericalDistanceM, type RouteStats } from '../stats/stats'
import type { Waypoint } from '../types'
import { AlertIcon, CloseIcon } from '../ui/icons'

/** Fastest way from the crew's position to the nearer safe haven. */
export interface AbortPlan {
  haven: string
  timeS: number
  distanceM: number
  points: { lat: number; lon: number }[]
}

interface Props {
  stats: RouteStats
  /** [habitat, ...stops, habitat] */
  stations: Waypoint[]
  /** seconds to the nearest safe haven (habitat or staged rover) from every cell */
  walkHome: Float32Array
  params: EvaParams
  alerts: Reason[]
  planAbort: (cell: number) => AbortPlan | null
  onExit: () => void
}

const elapsed = (s: number) => `T+${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`
const SPEEDS = [60, 300, 900]
/** The abort arrow points along the escape path this far ahead (in path cells), not at the haven as the crow flies. */
const LOOK_AHEAD_CELLS = 15

function Compass({ bearing, big, sub }: { bearing: number; big: string; sub: string }) {
  return (
    <div className="hud-compass" aria-label={`Bearing ${Math.round(bearing)} degrees ${compassPoint(bearing)}`}>
      <svg viewBox="-60 -60 120 120" aria-hidden="true">
        <circle r="52" className="hud-ring" />
        {['N', 'E', 'S', 'W'].map((c, i) => (
          <text key={c} x={Math.sin((i * Math.PI) / 2) * 42} y={-Math.cos((i * Math.PI) / 2) * 42 + 4} className="hud-cardinal">
            {c}
          </text>
        ))}
        <g transform={`rotate(${bearing})`}>
          <path d="M0,-34 L9,4 L0,-3 L-9,4 Z" className="hud-arrow" />
        </g>
      </svg>
      <div>
        <strong>{big}</strong>
        <span>{sub}</span>
      </div>
    </div>
  )
}

/**
 * Helmet-visor view: only what a suited astronaut needs at a glance. The EVA plays on the plan's clock (or is
 * scrubbed by hand), so the demo can walk the route. Abort switches to the fastest way to the nearest safe haven.
 */
export function Hud({ stats, stations, walkHome, params, alerts, planAbort, onExit }: Props) {
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(300)
  const [abort, setAbort] = useState<{ atT: number; plan: AbortPlan | null } | null>(null)
  const last = useRef<number | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onExit()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onExit])

  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = (now: number) => {
      if (last.current !== null) {
        setT((v) => {
          const next = v + ((now - last.current!) / 1000) * speed
          if (next >= stats.totalS) setPlaying(false)
          return Math.min(next, stats.totalS)
        })
      }
      last.current = now
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(raf)
      last.current = null
    }
  }, [playing, speed, stats.totalS])

  const pos = positionAt(stats.track, t)
  const cell = stats.track[pos.index].cell
  const o2Left = params.o2DurationS - t
  const usable = params.o2DurationS - params.o2ReserveS

  if (abort) {
    const plan = abort.plan
    const ahead = plan ? plan.points[Math.min(LOOK_AHEAD_CELLS, plan.points.length - 1)] : null
    const bearing = plan && ahead ? initialBearingDeg(pos, ahead) : 0
    const worstCase = plan ? params.walkHomeContingency * plan.timeS : Infinity
    const spare = usable - (abort.atT + worstCase)
    return (
      <div className="hud is-abort" role="dialog" aria-modal="true" aria-label="Helmet HUD: abort">
        <button type="button" className="hud-exit" onClick={onExit}>
          <CloseIcon size={18} /> Exit HUD
        </button>
        <div className="hud-next">
          <span className="hud-label">Abort · return to safety</span>
          <strong>{plan ? `Head to ${plan.haven}` : 'No walkable way to a safe haven'}</strong>
        </div>
        {plan && <Compass bearing={bearing} big={formatDistance(plan.distanceM)} sub={`${compassPoint(bearing)} ${Math.round(bearing)}° · follow the path`} />}
        <div className="hud-gauges">
          <div>
            <span className="hud-label">Time to safety</span>
            <strong>{plan ? formatDuration(plan.timeS) : '—'}</strong>
            <small>{plan ? `${formatDuration(worstCase)} if ${params.walkHomeContingency}× slower` : ''}</small>
          </div>
          <div className={o2Left < params.o2ReserveS ? 'is-alert' : ''}>
            <span className="hud-label">O₂ left</span>
            <strong>{formatDuration(params.o2DurationS - abort.atT)}</strong>
          </div>
          <div className={spare < 0 ? 'is-alert' : spare < 1800 ? 'is-caution' : ''}>
            <span className="hud-label">Spare O₂ at arrival</span>
            <strong>{plan ? (spare < 0 ? `Short ${formatDuration(-spare)}` : formatDuration(spare)) : '—'}</strong>
            <small>above the reserve, at the slow pace</small>
          </div>
        </div>
        <div className="hud-controls">
          <button type="button" onClick={() => setAbort(null)}>
            Cancel abort, resume plan
          </button>
          <span className="hud-clock">Aborted at {elapsed(abort.atT)}</span>
        </div>
      </div>
    )
  }

  const next = stations[Math.min(pos.nextStation, stations.length - 1)]
  const nextNumber = pos.nextStation >= stations.length - 1 ? null : pos.nextStation
  const bearing = initialBearingDeg(pos, next)
  const distance = sphericalDistanceM(pos, next)
  const home = params.walkHomeContingency * walkHome[cell]
  const margin = usable - (t + home)
  const done = t >= stats.totalS

  return (
    <div className="hud" role="dialog" aria-modal="true" aria-label="Helmet HUD view">
      <button type="button" className="hud-exit" onClick={onExit}>
        <CloseIcon size={18} /> Exit HUD
      </button>

      <div className="hud-next">
        <span className="hud-label">{done ? 'Walk complete' : pos.atStop ? 'Working at' : 'Next'}</span>
        <strong>
          {nextNumber !== null && <span className="hud-num">{nextNumber}</span>}
          {done ? 'Back at the habitat' : next.name}
        </strong>
      </div>

      <Compass bearing={bearing} big={pos.atStop || done ? '—' : formatDistance(distance)} sub={`${compassPoint(bearing)} ${Math.round(bearing)}°`} />

      <div className="hud-gauges">
        <div className={o2Left < params.o2ReserveS ? 'is-alert' : ''}>
          <span className="hud-label">O₂ left</span>
          <strong>{formatDuration(o2Left)}</strong>
        </div>
        <div className={margin < 0 ? 'is-alert' : margin < 3600 ? 'is-caution' : ''}>
          <span className="hud-label">Walk-home margin</span>
          <strong>{margin < 0 ? 'Past the limit' : formatDuration(margin)}</strong>
        </div>
        <div>
          <span className="hud-label">EVA clock</span>
          <strong>{elapsed(t)}</strong>
        </div>
      </div>

      <ul className="hud-alerts" aria-live="polite">
        {alerts.map((r) => (
          <li key={r.code} className={`sev-${r.severity}`}>
            {r.message}
          </li>
        ))}
      </ul>

      <div className="hud-controls">
        <button type="button" onClick={() => (done ? (setT(0), setPlaying(true)) : setPlaying((v) => !v))}>
          {playing ? 'Pause' : done ? 'Replay' : 'Play walk'}
        </button>
        <input
          type="range"
          min={0}
          max={stats.totalS}
          step={10}
          value={t}
          aria-label="EVA time"
          onChange={(e) => {
            setPlaying(false)
            setT(Number(e.target.value))
          }}
        />
        <select value={speed} aria-label="Playback speed" onChange={(e) => setSpeed(Number(e.target.value))}>
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}× speed
            </option>
          ))}
        </select>
        <button
          type="button"
          className="hud-abort"
          onClick={() => {
            setPlaying(false)
            setAbort({ atT: t, plan: planAbort(cell) })
          }}
        >
          <AlertIcon size={16} /> Abort
        </button>
      </div>
    </div>
  )
}
