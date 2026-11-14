import { useEffect, useMemo, useRef, useState } from 'react'
import { loadCostGrid, loadJson, type LoadedGrid } from './data/load'
import { MapView, type LayerState } from './map/MapView'
import type { GridOverlayMode } from './map/overlays'
import { ConditionsPanel } from './panels/ConditionsPanel'
import { Directions } from './panels/Directions'
import { Hud } from './panels/Hud'
import { MapControls } from './panels/MapControls'
import { StopDetail } from './panels/StopDetail'
import { Timeline } from './panels/Timeline'
import { createRouteClient, type RouteClient } from './route/client'
import { DEFAULT_ROUTE_PARAMS, isPassable, prepareGrid } from './route/cost'
import type { Message } from './panels/Directions'
import type { AbortPlan } from './panels/Hud'
import { bestOrder, nearestHaven, tourTime } from './route/optimize'
import { cellAt, cellCenter, type RouteResult } from './route/route'
import { findPath } from './route/search'
import { sphericalDistanceM } from './stats/stats'
import { buildTimeline, crewAtStop, initialBearingDeg, nearestPov, withSimulatedStorm } from './stats/eva'
import { DEFAULT_EVA_PARAMS, evaluateEva } from './stats/goNoGo'
import type { Conditions, DataConfig, PovImage, ScienceTarget, Waypoint } from './types'

interface Loaded {
  config: DataConfig
  grid: LoadedGrid
  base: Waypoint
  targets: ScienceTarget[]
  conditions: Conditions[]
  povs: PovImage[]
}

async function loadAll(): Promise<Loaded> {
  const config = await loadJson<DataConfig>('config.json')
  const [grid, waypoints, targets, conditions, povs] = await Promise.all([
    loadCostGrid(config),
    loadJson<Waypoint[]>(config.waypoints.path),
    loadJson<ScienceTarget[]>(config.scienceTargets.path),
    loadJson<Conditions[]>(config.conditions.path),
    loadJson<PovImage[]>(config.povImages.path),
  ])
  const base = waypoints.find((w) => w.kind === 'base')
  if (!base) throw new Error(`${config.waypoints.path} has no waypoint of kind "base"`)
  return { config, grid, base, targets, conditions, povs }
}

export default function App() {
  const [loaded, setLoaded] = useState<Loaded | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadAll().then(setLoaded, (e: unknown) => setError(e instanceof Error ? e.message : String(e)))
  }, [])

  if (error)
    return (
      <main className="boot">
        <p className="boot-title">Site data could not load</p>
        <p>{error}</p>
      </main>
    )
  if (!loaded)
    return (
      <main className="boot">
        <p className="boot-title">Loading the site</p>
        <p>Terrain grid, stations and conditions…</p>
      </main>
    )
  return <Planner {...loaded} />
}

/** Planned EVA start: the first conditions sample with the sun at least 20° up (mock conditions until Phase 7). */
function defaultStart(conditions: Conditions[]): string {
  return (conditions.find((c) => c.sunElevationDeg >= 20) ?? conditions[0]).time
}

function Planner({ config, grid: { grid, meta, buffer }, base, targets, conditions, povs }: Loaded) {
  const routeParams = DEFAULT_ROUTE_PARAMS
  const evaParams = DEFAULT_EVA_PARAMS
  const prepared = useMemo(() => prepareGrid(grid, routeParams), [grid, routeParams])
  const startTime = useMemo(() => defaultStart(conditions), [conditions])
  const [layerState, setLayerState] = useState<Record<string, LayerState>>(() =>
    Object.fromEntries(config.layers.map((l) => [l.id, { visible: config.initialLayers.includes(l.id), opacity: l.opacity }])),
  )
  const [overlay, setOverlay] = useState<GridOverlayMode>('none')
  const [stops, setStops] = useState<Waypoint[]>([])
  const [route, setRoute] = useState<RouteResult | null>(null)
  const [walkHome, setWalkHome] = useState<Float32Array | null>(null)
  const [routing, setRouting] = useState(false)
  const [notice, setNoticeState] = useState<Message | null>(null)
  const setNotice = (text: string | null, kind: Message['kind'] = 'error') => setNoticeState(text ? { kind, text } : null)
  /** where the rover is staged as a safe haven: 'habitat' or a stop id */
  const [roverAt, setRoverAt] = useState('habitat')
  const [havenFields, setHavenFields] = useState<Record<number, Float32Array>>({})
  const [optimising, setOptimising] = useState(false)
  const [panel, setPanel] = useState<'layers' | 'conditions' | null>(null)
  const [storm, setStorm] = useState(false)
  const [selected, setSelected] = useState<number | null>(null)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const [hud, setHud] = useState(false)
  const client = useRef<{ client: RouteClient; ready: Promise<void> } | null>(null)
  const viaCount = useRef(0)
  const baseCell = cellAt(grid, base.lat, base.lon)

  useEffect(() => {
    const c = createRouteClient()
    const ready = c.init(meta, buffer.slice(0), routeParams)
    client.current = { client: c, ready }
    let alive = true
    ready.then(() => c.walkHome(baseCell)).then((f) => alive && setWalkHome(f))
    return () => {
      alive = false
      c.terminate()
    }
  }, [meta, buffer, routeParams, baseCell])

  // Re-plan habitat → stations → habitat whenever the stations change; ignore answers to outdated requests.
  useEffect(() => {
    if (stops.length === 0) {
      setRoute(null)
      return
    }
    let current = true
    const cells = [base, ...stops, base].map((w) => cellAt(grid, w.lat, w.lon))
    setRouting(true)
    const c = client.current!
    c.ready
      .then(() => c.client.route(cells))
      .then((r) => current && setRoute(r))
      .catch((e: unknown) => current && setNotice(`Route failed: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => current && setRouting(false))
    return () => {
      current = false
    }
  }, [grid, base, stops])

  // The solar-storm drill raises a radiation alert across the whole O₂ span from the planned start.
  const effectiveConditions = useMemo(() => {
    if (!storm) return conditions
    const start = Date.parse(startTime)
    return withSimulatedStorm(conditions, start, start + evaParams.o2DurationS * 1000)
  }, [storm, conditions, startTime, evaParams])

  const roverStop = stops.find((s) => s.id === roverAt) ?? null
  const roverCell = roverStop ? cellAt(grid, roverStop.lat, roverStop.lon) : null
  useEffect(() => {
    if (roverAt !== 'habitat' && !roverStop) setRoverAt('habitat') // its stop was removed
  }, [roverAt, roverStop])
  useEffect(() => {
    if (roverCell === null || havenFields[roverCell]) return
    let alive = true
    const c = client.current!
    c.ready.then(() => c.client.walkHome(roverCell)).then((f) => alive && setHavenFields((all) => ({ ...all, [roverCell]: f })))
    return () => {
      alive = false
    }
  }, [roverCell, havenFields])
  const roverField = roverCell !== null ? (havenFields[roverCell] ?? null) : null
  const safeHaven = useMemo(() => (walkHome && roverField ? nearestHaven([walkHome, roverField]) : walkHome), [walkHome, roverField])

  const verdict = useMemo(
    () =>
      route && safeHaven
        ? evaluateEva({ prepared, route, walkHome: safeHaven, startTime, conditions: effectiveConditions, params: evaParams })
        : null,
    [route, safeHaven, prepared, startTime, effectiveConditions, evaParams],
  )
  // Stats only while the route matches the current stops (the render right after an edit still holds the old route).
  const routeMatches = route?.ok === true && route.legs.length === stops.length + 1
  const stats = stops.length > 0 && !routing && routeMatches ? (verdict?.stats ?? null) : null
  const timeline = useMemo(() => (stats ? buildTimeline(stats, stops, targets) : []), [stats, stops, targets])
  const stations = [base, ...stops, base]

  // Details for the selected stop: target, nearest panorama, arrival, and the heading toward the next stop.
  const detail = (() => {
    if (selected === null || selected > stops.length) return null
    const station = stations[selected]
    const next = stations[selected + 1] ?? base
    let arriveS: number | null = null
    if (stats && selected > 0) for (const p of stats.track) if (p.leg === selected - 1) arriveS = p.arriveS
    return {
      station,
      target: targets.find((t) => t.id === station.id) ?? null,
      pov: nearestPov(povs, station.lat, station.lon),
      arriveS,
      headingDeg: selected === stops.length && selected > 0 ? initialBearingDeg(station, base) : initialBearingDeg(station, next),
    }
  })()
  const hoverPoint = stats && hoverIndex !== null ? stats.track[hoverIndex] : null

  function addStop(w: Waypoint) {
    const cell = cellAt(grid, w.lat, w.lon)
    if (cell < 0) return setNotice('That point is outside the mapped site.')
    if (!isPassable(prepared, cell)) return setNotice('That spot is impassable on foot: no-go terrain or a slope of 25° or more.')
    setNotice(null)
    // Dedupe against the latest list, not this render's copy: two quick clicks must not add a stop twice.
    setStops((s) => (s.some((x) => x.id === w.id) ? s : [...s, w]))
  }

  /** Reorder the stops for the shortest walk, timing every ordered pair in the worker. */
  async function optimiseOrder() {
    if (stops.length < 2) return
    setOptimising(true)
    try {
      const c = client.current!
      await c.ready
      const matrix = await c.client.matrix([base, ...stops].map((w) => cellAt(grid, w.lat, w.lon)))
      const order = bestOrder(matrix)
      if (!order) return setNotice('No order reaches every stop: one of them is cut off.')
      const current = stops.map((_, i) => i + 1)
      const saved = tourTime(matrix, current) - tourTime(matrix, order)
      if (saved < 30) return setNotice('This order is already the quickest.', 'info')
      setStops(order.map((k) => stops[k - 1]))
      setSelected(null)
      setNotice(`Reordered for the quickest walk: ${Math.round(saved / 60)} min less walking.`, 'info')
    } catch (e) {
      setNotice(`Could not optimise: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setOptimising(false)
    }
  }

  /** Fastest way from a cell to the nearer safe haven (habitat, or the staged rover). */
  function planAbort(cell: number): AbortPlan | null {
    const havens = [{ cell: baseCell, name: base.name }]
    if (roverCell !== null && roverStop) havens.push({ cell: roverCell, name: `the rover at ${roverStop.name}` })
    let best: AbortPlan | null = null
    for (const h of havens) {
      const path = findPath(prepared, cell, h.cell)
      if (!path || (best && path.timeS >= best.timeS)) continue
      const pts = path.cells.map((c) => cellCenter(grid, c))
      let distanceM = 0
      for (let i = 1; i < pts.length; i++) distanceM += sphericalDistanceM(pts[i - 1], pts[i])
      best = { haven: h.name, timeS: path.timeS, distanceM, points: pts }
    }
    return best
  }

  function addTarget(t: ScienceTarget) {
    if (!stops.some((s) => s.id === t.id)) addStop({ id: t.id, lat: t.lat, lon: t.lon, kind: 'science', name: t.name })
  }

  return (
    <div className="app">
      <main className="stage">
        <MapView
          config={config}
          grid={grid}
          routeParams={routeParams}
          layerState={layerState}
          overlay={overlay}
          base={base}
          targets={targets}
          stops={stops}
          route={route}
          onMapClick={(lat, lon) => {
            viaCount.current += 1
            addStop({ id: `via-${viaCount.current}`, lat, lon, kind: 'via', name: `Via point ${viaCount.current}` })
          }}
          onTargetClick={addTarget}
          selected={selected}
          onSelectStation={setSelected}
          hoverPoint={hoverPoint}
          walkHome={safeHaven}
          rover={roverStop ? { lat: roverStop.lat, lon: roverStop.lon, name: roverStop.name } : null}
        />
        <MapControls
          config={config}
          baseLon={base.lon}
          gridStatus={meta.status}
          layerState={layerState}
          onLayerChange={(id, s) => setLayerState((all) => ({ ...all, [id]: s }))}
          overlay={overlay}
          onOverlayChange={setOverlay}
          panel={panel}
          onPanel={setPanel}
          stormActive={storm}
          hudEnabled={stats !== null && safeHaven !== null}
          onHud={() => setHud(true)}
          conditionsPanel={
            <ConditionsPanel
              conditions={effectiveConditions}
              startTime={startTime}
              endTime={verdict?.endTime ?? null}
              storm={storm}
              onStormChange={setStorm}
              onClose={() => setPanel(null)}
            />
          }
        />
        {stats && <Timeline segments={timeline.filter((s) => s.actor === 'EV1')} totalS={stats.totalS} selected={selected} onSelect={setSelected} />}
      </main>

      {detail && (
        <StopDetail
          station={detail.station}
          number={selected!}
          target={detail.target}
          pov={detail.pov}
          arriveS={detail.arriveS}
          headingDeg={detail.headingDeg}
          crew={selected ? crewAtStop(detail.station, targets, roverStop?.name ?? null) : null}
          onClose={() => setSelected(null)}
        />
      )}

      {hud && stats && safeHaven && verdict && (
        <Hud
          stats={stats}
          stations={stations}
          walkHome={safeHaven!}
          params={evaParams}
          planAbort={planAbort}
          alerts={verdict.reasons.filter((r) => r.severity !== 'info')}
          onExit={() => setHud(false)}
        />
      )}

      <Directions
        siteName={config.site.name}
        dataStatus={meta.status}
        grid={grid}
        routeParams={routeParams}
        base={base}
        stops={stops}
        targets={targets}
        onAddTarget={addTarget}
        verdict={stops.length > 0 && !routing ? verdict : null}
        routing={routing}
        failedLeg={route && !route.ok ? route.failedLeg : null}
        notice={notice}
        startTime={startTime}
        o2DurationS={evaParams.o2DurationS}
        onRemove={(id) => {
          setStops((all) => all.filter((x) => x.id !== id))
          setSelected(null)
        }}
        roverAt={roverAt}
        onRoverAt={setRoverAt}
        onOptimise={optimiseOrder}
        optimising={optimising}
        onMove={(from, to) => {
          setStops((all) => {
            const next = [...all]
            const [moved] = next.splice(from, 1)
            next.splice(to, 0, moved)
            return next
          })
          setSelected(null)
        }}
        onClear={() => {
          setStops([])
          setNotice(null)
          setSelected(null)
        }}
        selected={selected}
        onSelect={setSelected}
        hoverIndex={hoverIndex}
        onHover={setHoverIndex}
      />
    </div>
  )
}
