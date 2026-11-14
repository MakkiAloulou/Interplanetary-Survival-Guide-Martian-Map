import { describe, expect, test } from 'vitest'
import { prepareGrid } from '../route/cost'
import { planLoop } from '../route/route'
import { gridFrom } from '../testing/grids'
import type { Conditions, PovImage, ScienceTarget, Waypoint } from '../types'
import { buildTimeline, compassPoint, initialBearingDeg, nearestPov, positionAt, withSimulatedStorm } from './eva'
import { routeStats } from './stats'

function loop() {
  const g = gridFrom(['.........'])
  const p = prepareGrid(g)
  const r = planLoop(p, 0, [8])
  if (!r.ok) throw new Error('no route')
  return routeStats(p, r.legs, 600)
}

describe('positionAt', () => {
  test('starts at the habitat, dwells at the stop, ends back home', () => {
    const s = loop()
    const stop = s.track.findIndex((t) => t.departS > t.arriveS)
    expect(positionAt(s.track, 0)).toMatchObject({ index: 0, atStop: false, nextStation: 1 })
    const mid = (s.track[stop].arriveS + s.track[stop].departS) / 2
    expect(positionAt(s.track, mid)).toMatchObject({ index: stop, atStop: true, nextStation: 1 })
    const after = positionAt(s.track, s.track[stop].departS + 1)
    expect(after.atStop).toBe(false)
    expect(after.nextStation).toBe(2)
    expect(positionAt(s.track, s.totalS + 100).index).toBe(s.track.length - 1)
  })

  test('interpolates between cells while walking', () => {
    const s = loop()
    const t = (s.track[1].arriveS + s.track[2].arriveS) / 2
    const p = positionAt(s.track, t)
    expect(p.lon).toBeGreaterThan(s.track[1].lon)
    expect(p.lon).toBeLessThan(s.track[2].lon)
  })
})

describe('bearing', () => {
  test('cardinal directions', () => {
    expect(initialBearingDeg({ lat: 0, lon: 0 }, { lat: 1, lon: 0 })).toBeCloseTo(0, 6)
    expect(initialBearingDeg({ lat: 0, lon: 0 }, { lat: 0, lon: 1 })).toBeCloseTo(90, 6)
    expect(initialBearingDeg({ lat: 0, lon: 0 }, { lat: -1, lon: 0 })).toBeCloseTo(180, 6)
    expect(initialBearingDeg({ lat: 0, lon: 0 }, { lat: 0, lon: -1 })).toBeCloseTo(270, 6)
    expect([0, 44, 46, 180, 315, 359].map(compassPoint)).toEqual(['N', 'NE', 'NE', 'S', 'NW', 'N'])
  })
})

describe('buildTimeline', () => {
  test('both crew walk each leg with the rover; instruments split between them at a science stop', () => {
    const s = loop()
    const stops: Waypoint[] = [{ id: 't', lat: 0, lon: 0, kind: 'science', name: 'Ridge' }]
    const targets = [{ id: 't', instrumentsNeeded: ['camera', 'rock hammer', 'sample bags'] }] as ScienceTarget[]
    const tl = buildTimeline(s, stops, targets)
    expect(tl.filter((x) => x.kind === 'walk')).toHaveLength(4)
    expect(tl.find((x) => x.actor === 'EV1' && x.kind === 'task')?.label).toBe('Camera, sample bags')
    expect(tl.find((x) => x.actor === 'EV2' && x.kind === 'task')?.label).toBe('Rock hammer')
    expect(tl.find((x) => x.actor === 'Rover' && x.kind === 'parked')?.label).toContain('safe haven')
    expect(Math.max(...tl.map((x) => x.endS))).toBeCloseTo(s.totalS, 9)
  })
})

test('buildTimeline survives a zero-length leg (two stops on the same cell)', () => {
  const g = gridFrom(['.....'])
  const p = prepareGrid(g)
  const r = planLoop(p, 0, [4, 4])
  if (!r.ok) throw new Error('no route')
  const s = routeStats(p, r.legs, 600)
  const stops: Waypoint[] = [
    { id: 'a', lat: 0, lon: 0, kind: 'via', name: 'A' },
    { id: 'b', lat: 0, lon: 0, kind: 'via', name: 'B' },
  ]
  expect(() => buildTimeline(s, stops, [])).not.toThrow()
})

describe('nearestPov / withSimulatedStorm', () => {
  test('nearest panorama within range only', () => {
    const povs = [{ lat: 0, lon: 0 }, { lat: 0, lon: 0.001 }] as PovImage[]
    expect(nearestPov(povs, 0, 0.0009)).toBe(povs[1])
    expect(nearestPov(povs, 1, 1)).toBeNull()
  })

  test('storm raises the alert across the EVA window only', () => {
    const c = [0, 1, 2, 5].map((h) => ({ time: new Date(h * 3600_000).toISOString(), radiationAlert: false }) as Conditions)
    const out = withSimulatedStorm(c, 2 * 3600_000, 3 * 3600_000)
    expect(out.map((x) => x.radiationAlert)).toEqual([false, true, true, false])
    expect(c.every((x) => !x.radiationAlert)).toBe(true)
  })
})
