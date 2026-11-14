import L from 'leaflet'
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type { CopilotLive } from '../copilot/useCopilot'
import { MARS_CRS } from '../map/crs'
import { INK } from '../map/overlays'
import { compassPoint, initialBearingDeg, positionAt } from '../stats/eva'
import { formatDistance, formatDuration } from '../stats/format'
import type { EvaParams, Reason } from '../stats/goNoGo'
import { liveWarnings } from '../stats/live'
import { sphericalDistanceM, type RouteStats } from '../stats/stats'
import type { Conditions, DataConfig, Waypoint } from '../types'
import { AlertSlot } from '../ui/AlertSlot'
import { walkAlerts } from '../ui/alerts'
import { AlertIcon, CheckIcon, CloseIcon, WarningIcon } from '../ui/icons'
import { StatusBadge } from '../ui/StatusBadge'
import type { AbortPlan } from './Hud'
import { PLAYBACK_SPEEDS, usePlayback } from './usePlayback'

interface Props {
  config: DataConfig
  stats: RouteStats
  /** [habitat, ...stops, habitat] */
  stations: Waypoint[]
  /** seconds to the nearest safe haven from every cell */
  walkHome: Float32Array
  params: EvaParams
  /** the plan's own cautions and no-go reasons */
  planReasons: Reason[]
  conditions: Conditions[]
  startTime: string
  planAbort: (cell: number) => AbortPlan | null
  onExit: () => void
  /** the simulated solar-storm drill is on: its alerts are labelled SIMULATED */
  drill?: boolean
  /** optional what-if copilot, given the walk clock and this view's abort */
  copilot?: (live: CopilotLive) => ReactNode
}

const elapsed = (s: number) => `T+${Math.floor(s / 3600)}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}`

/** Arrival and departure times at each station (index into stations). */
function stationTimes(stats: RouteStats): { arriveS: number; departS: number }[] {
  const out = [{ arriveS: 0, departS: 0 }]
  for (const p of stats.track) out[p.leg + 1] = { arriveS: p.arriveS, departS: p.departS }
  return out
}

/** The crew's map: follows them along the route, walked part grey, abort path in red. */
function TabletMap(props: { config: DataConfig; stats: RouteStats; stations: Waypoint[]; index: number; crew: { lat: number; lon: number }; abort: AbortPlan | null; follow: boolean }) {
  const { config, stats, stations, index, crew, abort, follow } = props
  const box = useRef<HTMLDivElement>(null)
  const map = useRef<L.Map | null>(null)
  const parts = useRef<{ walked: L.Polyline; ahead: L.Polyline; crew: L.CircleMarker; abort: L.Polyline } | null>(null)

  useEffect(() => {
    const m = L.map(box.current!, { crs: MARS_CRS, minZoom: config.site.zoom.min, maxZoom: config.site.zoom.max, zoomSnap: 1, zoomControl: false, attributionControl: false })
    for (const layer of config.layers.filter((l) => l.tileUrl && config.initialLayers.includes(l.id))) {
      L.tileLayer(layer.tileUrl!, { maxZoom: config.site.zoom.max, maxNativeZoom: config.site.zoom.max }).addTo(m)
    }
    const pts = stats.track.map((p) => L.latLng(p.lat, p.lon))
    const line = { lineCap: 'round', lineJoin: 'round', interactive: false } as const
    L.polyline(pts, { ...line, color: INK.white, weight: 12 }).addTo(m)
    const ahead = L.polyline(pts, { ...line, color: INK.blue, weight: 7 }).addTo(m)
    const walked = L.polyline([], { ...line, color: INK.walked, weight: 7 }).addTo(m)
    const abortLine = L.polyline([], { ...line, color: INK.red, weight: 7, dashArray: '2 12' }).addTo(m)
    stations.forEach((s, i) => {
      if (i === stations.length - 1) return
      const home = i === 0
      L.marker([s.lat, s.lon], {
        icon: L.divIcon({ className: `map-mark ${home ? 'mark-home' : 'mark-stop'}`, html: home ? '' : String(i), iconSize: [30, 30], iconAnchor: [15, 15] }),
        keyboard: false,
        interactive: false,
      }).addTo(m)
    })
    m.createPane('crew').style.zIndex = '650' // above the stop pins, so the crew stays visible while working at a stop
    const crewDot = L.circleMarker([stats.track[0].lat, stats.track[0].lon], { pane: 'crew', radius: 10, color: INK.white, weight: 4, fillColor: INK.green, fillOpacity: 1, className: 'crew-dot', interactive: false }).addTo(m)
    m.setView([stats.track[0].lat, stats.track[0].lon], config.site.zoom.max - 1)
    map.current = m
    parts.current = { walked, ahead, crew: crewDot, abort: abortLine }
    return () => {
      m.remove()
      map.current = null
      parts.current = null
    }
  }, [config, stats, stations])

  useEffect(() => {
    const p = parts.current
    if (!p) return
    const pts = stats.track.map((q) => L.latLng(q.lat, q.lon))
    p.walked.setLatLngs([...pts.slice(0, index + 1), L.latLng(crew.lat, crew.lon)])
    p.ahead.setLatLngs([L.latLng(crew.lat, crew.lon), ...pts.slice(index + 1)])
    p.crew.setLatLng([crew.lat, crew.lon])
    p.abort.setLatLngs(abort ? abort.points.map((q) => L.latLng(q.lat, q.lon)) : [])
    if (follow) map.current!.panTo([crew.lat, crew.lon], { animate: false })
  }, [stats, index, crew.lat, crew.lon, abort, follow])

  // .map shares the main map's marker, zoom and tooltip styles.
  return <div ref={box} className="map tablet-map" />
}

/**
 * The tablet a crew member carries on the walk: where am I going next, what is wrong right now, what comes after.
 * High contrast for daylight, large targets for gloved hands. Plays the EVA on the plan's clock for the demo.
 */
export function Tablet({ config, stats, stations, walkHome, params, planReasons, conditions, startTime, planAbort, onExit, drill = false, copilot }: Props) {
  const clock = usePlayback(stats.totalS)
  const { t } = clock
  const [follow, setFollow] = useState(true)
  const [abort, setAbort] = useState<{ atT: number; plan: AbortPlan | null } | null>(null)
  const times = useMemo(() => stationTimes(stats), [stats])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onExit()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onExit])

  const pos = positionAt(stats.track, abort ? abort.atT : t)
  const cell = stats.track[pos.index].cell
  const nextIndex = Math.min(pos.nextStation, stations.length - 1)
  const next = stations[nextIndex]
  const isHomeNext = nextIndex === stations.length - 1
  const bearing = initialBearingDeg(pos, next)
  const distance = sphericalDistanceM(pos, next)
  const emergencyHomeS = params.walkHomeContingency * walkHome[cell]
  const margin = params.o2DurationS - params.o2ReserveS - (t + emergencyHomeS)
  const live = liveWarnings({ t, startTime, emergencyHomeS, conditions, params })
  const o2Left = params.o2DurationS - t
  const alerts = walkAlerts(live, planReasons, { marginS: margin, o2LeftS: o2Left }, drill)
  const liveAlerts = alerts.filter((a) => a.live)
  const planNotes = alerts.filter((a) => !a.live)
  const gauge = (codes: string[]) => {
    const hit = live.filter((w) => codes.includes(w.code))
    return hit.some((w) => w.severity === 'no-go') ? 'warning' : hit.length ? 'caution' : 'ok'
  }
  const o2State = gauge(['O2_LOW'])
  const pnrState = gauge(['NO_RETURN', 'MARGIN_LOW'])
  const done = t >= stats.totalS

  return (
    <div className="tablet" role="dialog" aria-modal="true" aria-label="Tablet view for the walk">
      <TabletMap config={config} stats={stats} stations={stations} index={pos.index} crew={pos} abort={abort?.plan ?? null} follow={follow} />

      <aside className="tablet-side">
        <header className="tablet-head">
          <div>
            <span className="tablet-kick">Marswalk clock</span>
            <strong>{elapsed(abort ? abort.atT : t)}</strong>
          </div>
          <button type="button" className="tablet-btn" onClick={onExit}>
            <CloseIcon size={20} /> Exit
          </button>
        </header>

        {drill && (
          <p className="tablet-drill">
            Storm drill running <StatusBadge status="SIMULATED" />
          </p>
        )}

        {abort ? (
          <section className="tablet-next is-abort" aria-live="assertive">
            <h2>
              <span className="tablet-state">
                <WarningIcon size={18} /> Abort
              </span>
              {abort.plan ? `Head to ${abort.plan.haven}` : 'No walkable way to a safe haven'}
            </h2>
            {abort.plan && (
              <p>
                {formatDistance(abort.plan.distanceM)} along the red path · {formatDuration(abort.plan.timeS)} (
                {formatDuration(params.walkHomeContingency * abort.plan.timeS)} at the slow pace)
              </p>
            )}
            <button type="button" className="tablet-btn" onClick={() => setAbort(null)}>
              Cancel abort
            </button>
          </section>
        ) : (
          <section className="tablet-next" aria-live="polite">
            <h2>
              <span className="tablet-state">{done ? 'Done' : pos.atStop ? 'At stop' : 'Next'}</span>
              {!isHomeNext && !done && <span className="tablet-num">{nextIndex}</span>}
              {done ? 'Back at the habitat' : next.name}
            </h2>
            {!done && (
              <p>
                {pos.atStop
                  ? `Leave at ${elapsed(times[nextIndex]?.departS ?? 0)}`
                  : `${formatDistance(distance)} straight line · ${compassPoint(bearing)} ${Math.round(bearing)}° · arrive ${elapsed(times[nextIndex]?.arriveS ?? 0)}`}
              </p>
            )}
          </section>
        )}

        <div className="tablet-gauges">
          <div className={`is-${o2State}`}>
            <span>O₂ left</span>
            <strong>{formatDuration(o2Left)}</strong>
            {o2State !== 'ok' && <em className="tablet-gauge-state">{o2State === 'warning' ? 'Warning' : 'Caution'}</em>}
          </div>
          <div className={`is-${pnrState}`}>
            <span>Point of no return</span>
            <strong>{margin < 0 ? 'Passed' : `in ${formatDuration(margin)}`}</strong>
            {pnrState !== 'ok' && <em className="tablet-gauge-state">{pnrState === 'warning' ? 'Warning' : 'Caution'}</em>}
          </div>
        </div>

        <section className="tablet-warnings" aria-label="Warnings">
          <h3>Right now</h3>
          {liveAlerts.length === 0 ? (
            <p className="tablet-ok">
              <CheckIcon size={20} /> All clear right now.
            </p>
          ) : (
            <AlertSlot alerts={liveAlerts} variant="tablet" />
          )}
          {planNotes.length > 0 && (
            <>
              <h3 className="tablet-plan-head">Plan notes</h3>
              <ul className="tablet-plan">
                {planNotes.map((a) => (
                  <li key={a.key} className={`is-${a.level}`}>
                    {a.level === 'warning' ? <WarningIcon size={18} /> : <AlertIcon size={18} />}
                    <span>
                      <strong>{a.level === 'warning' ? 'No-go' : 'Caution'}:</strong> {a.detail}
                    </span>
                    {a.drill && <StatusBadge status="SIMULATED" />}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="tablet-upcoming" aria-label="Upcoming stops">
          <h3>Coming up</h3>
          <ol>
            {stations.slice(nextIndex + 1).map((s, k) => {
              const i = nextIndex + 1 + k
              const home = i === stations.length - 1
              return (
                <li key={`${s.id}-${i}`}>
                  {home ? <span className="pin pin-home" aria-hidden="true" /> : <span className="pin">{i}</span>}
                  <span>{s.name}</span>
                  <span className="tablet-eta">{elapsed(times[i]?.arriveS ?? 0)}</span>
                </li>
              )
            })}
          </ol>
        </section>

        <footer className="tablet-controls">
          <button type="button" className="tablet-btn is-primary" onClick={clock.toggle} disabled={!!abort}>
            {clock.playing ? 'Pause' : done ? 'Replay' : 'Play walk'}
          </button>
          <input type="range" min={0} max={stats.totalS} step={10} value={t} aria-label="Marswalk time" disabled={!!abort} onChange={(e) => clock.seek(Number(e.target.value))} />
          <select value={clock.speed} aria-label="Playback speed" onChange={(e) => clock.setSpeed(Number(e.target.value))}>
            {PLAYBACK_SPEEDS.map((s) => (
              <option key={s} value={s}>
                {s}× speed
              </option>
            ))}
          </select>
          <button type="button" className="tablet-btn" aria-pressed={follow} onClick={() => setFollow((v) => !v)}>
            {follow ? 'Following crew' : 'Follow crew'}
          </button>
          <button
            type="button"
            className="tablet-btn is-danger"
            disabled={!!abort}
            onClick={() => {
              clock.pause()
              setAbort({ atT: t, plan: planAbort(cell) })
            }}
          >
            <WarningIcon size={20} /> Abort
          </button>
        </footer>
      </aside>
      {!abort && copilot?.({ t, index: pos.index, cell, drill, onAbort: () => (clock.pause(), setAbort({ atT: t, plan: planAbort(cell) })) })}
    </div>
  )
}
