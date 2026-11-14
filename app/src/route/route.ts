// Multi-stop routes (base → stops → base) and lat/lon ↔ cell conversion.

import type { CostGrid } from '../types'
import type { PreparedGrid } from './cost'
import { findPath } from './search'

export interface Leg {
  from: number
  to: number
  cells: number[]
  timeS: number
}

export type RouteResult = { ok: true; legs: Leg[]; timeS: number } | { ok: false; failedLeg: number }

/** Walk the stops in the given order (no reordering). Fails on the first leg with no path. */
export function planRoute(p: PreparedGrid, stops: number[]): RouteResult {
  const legs: Leg[] = []
  for (let i = 0; i + 1 < stops.length; i++) {
    const path = findPath(p, stops[i], stops[i + 1])
    if (!path) return { ok: false, failedLeg: i }
    legs.push({ from: stops[i], to: stops[i + 1], cells: path.cells, timeS: path.timeS })
  }
  return { ok: true, legs, timeS: legs.reduce((sum, leg) => sum + leg.timeS, 0) }
}

/** base → each stop in order → base. */
export function planLoop(p: PreparedGrid, base: number, stops: number[]): RouteResult {
  return planRoute(p, [base, ...stops, base])
}

/** Cell containing (lat, lon), or -1 outside the grid. Row 0 = latMax, column 0 = lonMin. */
export function cellAt(grid: CostGrid, lat: number, lon: number): number {
  const { latMin, latMax, lonMin, lonMax } = grid.bounds
  const r = Math.floor(((latMax - lat) / (latMax - latMin)) * grid.height)
  const c = Math.floor(((lon - lonMin) / (lonMax - lonMin)) * grid.width)
  if (r < 0 || r >= grid.height || c < 0 || c >= grid.width) return -1
  return r * grid.width + c
}

export function cellCenter(grid: CostGrid, cell: number): { lat: number; lon: number } {
  const { latMin, latMax, lonMin, lonMax } = grid.bounds
  const r = Math.floor(cell / grid.width)
  const c = cell - r * grid.width
  return {
    lat: latMax - ((r + 0.5) * (latMax - latMin)) / grid.height,
    lon: lonMin + ((c + 0.5) * (lonMax - lonMin)) / grid.width,
  }
}
