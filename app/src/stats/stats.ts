// Route statistics: distance, elevation profile, per-leg time, slopes, time per terrain type, timeline.

import { MARS_MEAN_RADIUS_M, SCIENCE_STOP_DWELL_MIN } from '../config'
import { stepTime, type PreparedGrid } from '../route/cost'
import { cellCenter, type Leg } from '../route/route'
import { TERRAIN, type DataStatus, type TerrainClass } from '../types'
import { worstStatus } from './status'

/** One route cell, in walking order. Stop cells shared by two legs appear once. */
export interface TrackPoint {
  cell: number
  lat: number
  lon: number
  /** along-route spherical distance from the start, m */
  distanceM: number
  elevationM: number
  /** EVA clock (walking + dwell) on arrival and on leaving; they differ only at science stops */
  arriveS: number
  departS: number
  leg: number
}

export interface LegStats {
  from: number
  to: number
  distanceM: number
  walkS: number
  ascentM: number
  descentM: number
  maxSlopeDeg: number
}

export interface RouteStats {
  distanceM: number
  walkS: number
  dwellS: number
  /** walking + dwell = EVA duration */
  totalS: number
  ascentM: number
  descentM: number
  maxSlopeDeg: number
  maxSlopeCell: number
  /** walking time per terrain class; each step's time is split between its two cells */
  timeByTerrainS: Record<TerrainClass, number>
  legs: LegStats[]
  track: TrackPoint[]
  status: { distance: DataStatus; time: DataStatus }
}

/** Great-circle distance on the Mars mean sphere (haversine), m. */
export function sphericalDistanceM(a: { lat: number; lon: number }, b: { lat: number; lon: number }): number {
  const rad = Math.PI / 180
  const dLat = (b.lat - a.lat) * rad
  const dLon = (b.lon - a.lon) * rad
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLon / 2) ** 2
  return 2 * MARS_MEAN_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)))
}

/**
 * Stats for consecutive legs (base → stops → base). dwellS is the time spent at the end of each
 * leg except the last: one number for every stop, or one per stop.
 */
export function routeStats(p: PreparedGrid, legs: Leg[], dwellS: number | number[] = SCIENCE_STOP_DWELL_MIN * 60): RouteStats {
  const { grid } = p
  const timeByTerrainS: Record<TerrainClass, number> = {
    [TERRAIN.BEDROCK]: 0,
    [TERRAIN.SAND]: 0,
    [TERRAIN.BOULDERS]: 0,
    [TERRAIN.NO_GO]: 0,
  }
  const track: TrackPoint[] = []
  const legStats: LegStats[] = []
  let elapsed = 0
  let distance = 0
  let dwellTotal = 0
  let maxSlopeDeg = -Infinity
  let maxSlopeCell = -1

  const point = (cell: number, leg: number) => {
    const { lat, lon } = cellCenter(grid, cell)
    track.push({ cell, lat, lon, distanceM: distance, elevationM: grid.elevation[cell], arriveS: elapsed, departS: elapsed, leg })
    if (grid.slopeDeg[cell] > maxSlopeDeg) {
      maxSlopeDeg = grid.slopeDeg[cell]
      maxSlopeCell = cell
    }
  }

  legs.forEach((leg, li) => {
    const s: LegStats = { from: leg.from, to: leg.to, distanceM: 0, walkS: 0, ascentM: 0, descentM: 0, maxSlopeDeg: grid.slopeDeg[leg.cells[0]] }
    if (li === 0) point(leg.cells[0], 0)
    for (let k = 1; k < leg.cells.length; k++) {
      const a = leg.cells[k - 1]
      const b = leg.cells[k]
      const diagonal = a % grid.width !== b % grid.width && Math.floor(a / grid.width) !== Math.floor(b / grid.width)
      const t = stepTime(p, a, b, diagonal ? grid.cellSizeM * Math.SQRT2 : grid.cellSizeM)
      const d = sphericalDistanceM(cellCenter(grid, a), cellCenter(grid, b))
      const dz = grid.elevation[b] - grid.elevation[a]
      timeByTerrainS[grid.terrainClass[a] as TerrainClass] += t / 2
      timeByTerrainS[grid.terrainClass[b] as TerrainClass] += t / 2
      s.walkS += t
      s.distanceM += d
      if (dz > 0) s.ascentM += dz
      else s.descentM -= dz
      s.maxSlopeDeg = Math.max(s.maxSlopeDeg, grid.slopeDeg[b])
      elapsed += t
      distance += d
      point(b, li)
    }
    if (li < legs.length - 1) {
      const dwell = Array.isArray(dwellS) ? (dwellS[li] ?? 0) : dwellS
      track[track.length - 1].departS += dwell
      elapsed += dwell
      dwellTotal += dwell
    }
    legStats.push(s)
  })

  const distanceStatus = worstStatus('DERIVED', grid.status)
  return {
    distanceM: distance,
    walkS: elapsed - dwellTotal,
    dwellS: dwellTotal,
    totalS: elapsed,
    ascentM: legStats.reduce((sum, l) => sum + l.ascentM, 0),
    descentM: legStats.reduce((sum, l) => sum + l.descentM, 0),
    maxSlopeDeg,
    maxSlopeCell,
    timeByTerrainS,
    legs: legStats,
    track,
    status: { distance: distanceStatus, time: worstStatus('MODELED', distanceStatus) },
  }
}
