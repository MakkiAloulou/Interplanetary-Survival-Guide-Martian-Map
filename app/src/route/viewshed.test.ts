import { describe, expect, test } from 'vitest'
import { commsGaps } from '../stats/comms'
import type { TrackPoint } from '../stats/stats'
import { gridFrom, idx } from '../testing/grids'
import { combinedViewshed, viewshed } from './viewshed'

const flat = (n: number) => Array.from({ length: n }, () => '.'.repeat(n))

describe('viewshed', () => {
  test('flat ground: everything is in sight', () => {
    const g = gridFrom(flat(21))
    const v = viewshed(g, { cell: idx(g, 10, 10), heightM: 3 }, 1.8)
    expect(v.every((x) => x === 1)).toBe(true)
  })

  test('a wall hides the ground behind it, not the ground in front', () => {
    // 10 m wall in column 12; antenna at column 2, 3 m high
    const g = gridFrom(flat(21), (_r, c) => (c === 12 ? 10 : 0))
    const v = viewshed(g, { cell: idx(g, 10, 2), heightM: 3 }, 1.8)
    expect(v[idx(g, 10, 8)]).toBe(1) // in front of the wall
    expect(v[idx(g, 10, 12)]).toBe(1) // the wall top itself
    expect(v[idx(g, 10, 14)]).toBe(0) // just behind it
    expect(v[idx(g, 10, 20)]).toBe(0)
  })

  test('a tall enough mast sees over the wall', () => {
    const g = gridFrom(flat(21), (_r, c) => (c === 12 ? 10 : 0))
    const v = viewshed(g, { cell: idx(g, 10, 2), heightM: 60 }, 1.8)
    expect(v[idx(g, 10, 20)]).toBe(1)
  })

  test('two antennas: a cell hidden from one but seen by the other counts as in contact', () => {
    const g = gridFrom(flat(21), (_r, c) => (c === 12 ? 10 : 0))
    const both = combinedViewshed(g, [{ cell: idx(g, 10, 2), heightM: 3 }, { cell: idx(g, 10, 18), heightM: 3 }], 1.8)
    expect(both[idx(g, 10, 16)]).toBe(1)
    expect(viewshed(g, { cell: idx(g, 10, 2), heightM: 3 }, 1.8)[idx(g, 10, 16)]).toBe(0)
  })
})

describe('commsGaps', () => {
  // track of 5 cells, 60 s per step, a 120 s stop at index 2
  const track = [0, 1, 2, 3, 4].map((cell, i) => ({
    cell, lat: 0, lon: 0, distanceM: i, elevationM: 0, leg: 0,
    arriveS: i * 60 + (i > 2 ? 120 : 0),
    departS: i * 60 + (i >= 2 ? 120 : 0),
  })) as TrackPoint[]

  test('all in sight: no gap', () => {
    expect(commsGaps(track, Uint8Array.from([1, 1, 1, 1, 1]))).toEqual({ outS: 0, longestS: 0, longestStart: -1 })
  })

  test('a hidden stop counts its dwell plus half of each adjacent step', () => {
    const g = commsGaps(track, Uint8Array.from([1, 1, 0, 1, 1]))
    expect(g.outS).toBe(30 + 120 + 30)
    expect(g.longestS).toBe(180)
    expect(g.longestStart).toBe(2) // the first hidden point
  })

  test('two separate gaps: total and longest differ', () => {
    const g = commsGaps(track, Uint8Array.from([0, 1, 1, 1, 0]))
    expect(g.outS).toBe(60)
    expect(g.longestS).toBe(30)
  })
})
