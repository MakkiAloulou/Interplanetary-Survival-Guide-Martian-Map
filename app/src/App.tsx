import { useEffect, useMemo, useRef, useState } from 'react'
import { loadCostGrid, loadJson, type LoadedGrid } from './data/load'
import { MapView, type LayerState } from './map/MapView'
import type { GridOverlayMode } from './map/overlays'
import { ConditionsPanel } from './panels/ConditionsPanel'
import { Directions } from './panels/Directions'
import { Hud } from './panels/Hud'
import { MapControls } from './panels/MapControls'
import { StopDetail } from './panels/StopDetail'
import { Tablet } from './panels/Tablet'
import { Timeline } from './panels/Timeline'
import { createRouteClient, type RouteClient } from './route/client'
import { DEFAULT_ROUTE_PARAMS, isPassable, prepareGrid, type RouteProfile } from './route/cost'
import type { Message } from './panels/Directions'
import type { AbortPlan } from './panels/Hud'
import { bestOrder, nearestHaven, tourTime } from './route/optimize'
import { cellAt, cellCenter, type RouteResult } from './route/route'
import { findPath } from './route/search'
import { sphericalDistanceM } from './stats/stats'
import { buildTimeline, crewAtStop, initialBearingDeg, nearestPov, withSimulatedStorm } from './stats/eva'
import { defaultStartOption, describeTime, startOptions, withMarsSun } from './stats/sun'
import { decodePlan, encodePlan, type DecodedPlan } from './share'
import { loadSavedPlans, planLink, storeSavedPlans, withPlanSaved, type SavedPlan } from './saved'
import { SavedPlans } from './panels/SavedPlans'
import { FASTER_ALTERNATIVE_MIN_SAVING_MIN } from './config'
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

/** The notice for a plan opened from a link: what could not be restored, if anything. */
function linkNotice(plan: DecodedPlan | null): Message | null {
  if (!plan || plan.skipped.length === 0) return null
  return { kind: 'error', text: `Part of the plan link could not be restored. ${plan.skipped.join(' ')}` }
}

function Planner({ config, grid: { grid, meta, buffer }, base, targets, conditions, povs }: Loaded) {
  const routeParams = DEFAULT_ROUTE_PARAMS
  const evaParams = DEFAULT_EVA_PARAMS
  const prepared = useMemo(() => prepareGrid(grid, routeParams), [grid, routeParams])
  // The sun comes from the Mars24 clock for the site (DERIVED); the conditions file gives weather and radiation.
  const sunConditions = useMemo(() => withMarsSun(conditions, base.lat, base.lon), [conditions, base])
  const startChoices = useMemo(() => startOptions(sunConditions, base.lat, base.lon), [sunConditions, base])
  const defaultStart = defaultStartOption(startChoices)?.time ?? conditions[0].time
  /** Why a point cannot be a stop, or null: the same check for clicked stops and stops from a plan link. */
  const stopProblem = (w: Waypoint) => {
    const cell = cellAt(grid, w.lat, w.lon)
    if (cell < 0) return 'outside the mapped site.'
    if (!isPassable(prepared, cell)) return 'impassable on foot: no-go terrain or a slope of 25° or more.'
    return null
  }
  // A plan link (the URL hash) opens the same plan; from then on the hash follows every change to the plan.
  const [linked] = useState(() => decodePlan(window.location.hash, targets, stopProblem))
  const [startTime, setStartTime] = useState(() => linked?.startTime ?? defaultStart)
  const [layerState, setLayerState] = useState<Record<string, LayerState>>(() =>
    Object.fromEntries(config.layers.map((l) => [l.id, { visible: config.initialLayers.includes(l.id), opacity: l.opacity }])),
  )
  const [overlay, setOverlay] = useState<GridOverlayMode>('none')
  const [stops, setStops] = useState<Waypoint[]>(() => linked?.stops ?? [])
  const [routes, setRoutes] = useState<Record<RouteProfile, RouteResult> | null>(null)
  /** the user's pick when a real trade-off is offered; the safest route otherwise */
  const [profile, setProfile] = useState<RouteProfile>(() => linked?.profile ?? 'safest')
  const [walkHome, setWalkHome] = useState<Float32Array | null>(null)
  const [routing, setRouting] = useState(false)
  const [notice, setNoticeState] = useState<Message | null>(() => linkNotice(linked))
  const setNotice = (text: string | null, kind: Message['kind'] = 'error') => setNoticeState(text ? { kind, text } : null)
  /** where the rover is staged as a safe haven: 'habitat' or a stop id */
  const [roverAt, setRoverAt] = useState(() => linked?.roverAt ?? 'habitat')
  const [havenFields, setHavenFields] = useState<Record<number, Float32Array>>({})
  const [optimising, setOptimising] = useState(false)
  const [panel, setPanel] = useState<'layers' | 'conditions' | 'saved' | null>(null)
  const [saved, setSaved] = useState<SavedPlan[]>(() => loadSavedPlans())
  const [storm, setStorm] = useState(() => linked?.storm ?? false)
  const [selected, setSelected] = useState<number | null>(null)
  const [hoverIndex, setHoverIndex] = useState<number | null>(null)
  const [hud, setHud] = useState(false)
  const [tablet, setTablet] = useState(false)
  const client = useRef<{ client: RouteClient; ready: Promise<void> } | null>(null)
  const viaCount = useRef(linked?.stops.filter((s) => s.kind === 'via').length ?? 0)
  const baseCell = cellAt(grid, base.lat, base.lon)

  // Keep the address bar a working link to the current plan (replaceState: no history entry per edit).
  const planHash = encodePlan({ stops, startTime: startTime === defaultStart ? null : startTime, roverAt, profile, storm })
  useEffect(() => {
    if (planHash !== window.location.hash) window.history.replaceState(null, '', planHash || window.location.pathname + window.location.search)
  }, [planHash])

  // A plan link pasted into this tab replaces the plan.
  useEffect(() => {
    const onHash = () => {
      const plan = decodePlan(window.location.hash, targets, stopProblem)
      if (!plan) return
      setStops(plan.stops)
      setStartTime(plan.startTime ?? defaultStart)
      setRoverAt(plan.roverAt)
      setProfile(plan.profile)
      setStorm(plan.storm)
      viaCount.current = plan.stops.filter((s) => s.kind === 'via').length
      setSelected(null)
      setNoticeState(linkNotice(plan))
    }
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  })

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
      setRoutes(null)
      return
    }
    let current = true
    const cells = [base, ...stops, base].map((w) => cellAt(grid, w.lat, w.lon))
    setRouting(true)
    const c = client.current!
    c.ready
      // Plan both alternatives together, so switching between them is instant.
      .then(() => Promise.all([c.client.route(cells, 'fastest'), c.client.route(cells, 'safest')]))
      .then(([fastest, safest]) => current && setRoutes({ fastest, safest }))
      .catch((e: unknown) => current && setNotice(`Route failed: ${e instanceof Error ? e.message : String(e)}`))
      .finally(() => current && setRouting(false))
    return () => {
      current = false
    }
  }, [grid, base, stops])

  // The solar-storm drill raises a radiation alert across the whole O₂ span from the planned start.
  const effectiveConditions = useMemo(() => {
    if (!storm) return sunConditions
    const start = Date.parse(startTime)
    return withSimulatedStorm(sunConditions, start, start + evaParams.o2DurationS * 1000)
  }, [storm, sunConditions, startTime, evaParams])

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

  // Both alternatives are judged on the same walking model; safety first, so the safest route is the default and
  // the fastest is offered only when it saves enough time to be worth the extra hazard.
  const judge = (r: RouteResult | null) =>
    r && safeHaven ? evaluateEva({ prepared, route: r, walkHome: safeHaven, startTime, conditions: effectiveConditions, params: evaParams }) : null
  const fastVerdict = useMemo(() => judge(routes?.fastest ?? null), [routes, safeHaven, prepared, startTime, effectiveConditions, evaParams])
  const safeVerdict = useMemo(() => judge(routes?.safest ?? null), [routes, safeHaven, prepared, startTime, effectiveConditions, evaParams])
  const savingS = fastVerdict?.stats && safeVerdict?.stats ? safeVerdict.stats.totalS - fastVerdict.stats.totalS : 0
  const tradeOff = savingS >= FASTER_ALTERNATIVE_MIN_SAVING_MIN * 60
  const active: RouteProfile = tradeOff ? profile : 'safest'
  const route = routes ? routes[active] : null
  const altRoute = routes && tradeOff ? routes[active === 'fastest' ? 'safest' : 'fastest'] : null
  const verdict = active === 'fastest' ? fastVerdict : safeVerdict
  const routeOptions = tradeOff && fastVerdict && safeVerdict ? { fastest: fastVerdict, safest: safeVerdict } : null
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
    const why = stopProblem(w)
    if (why) return setNotice(`That spot is ${why}`)
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

  function updateSaved(list: SavedPlan[]) {
    setSaved(list)
    if (!storeSavedPlans(list)) setNotice('This browser refused to store saved plans (storage blocked or full). Copy the plan link instead.')
  }

  function savePlan(name: string) {
    const summary = { stops: stops.length, start: describeTime(startTime, base.lon), totalS: stats?.totalS ?? null, verdict: verdict?.verdict ?? null }
    const id = `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`
    updateSaved(withPlanSaved(saved, { name, savedAt: new Date().toISOString(), hash: planHash, summary }, id))
  }

  async function copySavedLink(p: SavedPlan) {
    try {
      await navigator.clipboard.writeText(planLink(p.hash, window.location))
      return true
    } catch {
      setNotice('Could not copy automatically. Open the plan, then copy the address bar.', 'info')
      return false
    }
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
          altRoute={altRoute}
          onPickAlternative={() => setProfile((p) => (p === 'fastest' ? 'safest' : 'fastest'))}
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
          onTablet={() => setTablet(true)}
          savedPanel={
            <SavedPlans
              plans={saved}
              current={{ hash: planHash, defaultName: `Marswalk ${saved.length + 1}`, canSave: stats !== null }}
              onSave={savePlan}
              onOpen={(p) => {
                window.location.hash = p.hash // the hashchange listener restores the plan
              }}
              onCopy={copySavedLink}
              onDelete={(p) => updateSaved(saved.filter((x) => x.id !== p.id))}
              onRestore={(p) => updateSaved([p, ...saved.filter((x) => x.hash !== p.hash)])}
              onClose={() => setPanel(null)}
            />
          }
          savedCount={saved.length}
          conditionsPanel={
            <ConditionsPanel
              conditions={effectiveConditions}
              startTime={startTime}
              startChoices={startChoices}
              onStartTime={setStartTime}
              lonEast={base.lon}
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

      {tablet && stats && safeHaven && verdict && (
        <Tablet
          config={config}
          stats={stats}
          stations={stations}
          walkHome={safeHaven}
          params={evaParams}
          planReasons={verdict.reasons}
          conditions={effectiveConditions}
          startTime={startTime}
          planAbort={planAbort}
          onExit={() => setTablet(false)}
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
        profile={active}
        onProfile={setProfile}
        routeOptions={stops.length > 0 && !routing ? routeOptions : null}
        savingS={savingS}
        notice={notice}
        startTime={startTime}
        startLabel={describeTime(startTime, base.lon)}
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
        onSavePlan={() => setPanel('saved')}
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
