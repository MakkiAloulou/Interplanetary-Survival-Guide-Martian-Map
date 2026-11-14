// A* (one leg) and the reversed-graph Dijkstra walk-home field, 8-connected, on a PreparedGrid.

import { createHeap } from './heap'
import { isPassable, maxWalkingSpeedMs, stepTime, type PreparedGrid } from './cost'

const DR = [-1, -1, -1, 0, 0, 1, 1, 1]
const DC = [-1, 0, 1, -1, 1, -1, 0, 1]
const DIAG = [true, false, true, false, false, true, false, true]

export interface Path {
  /** cell indices from start to goal, inclusive */
  cells: number[]
  timeS: number
}

/**
 * Calls visit(neighbour, distM) for every neighbour of `cell` that can be stepped to.
 * A diagonal step is not allowed to squeeze between two cells when either of them is impassable.
 */
function forEachNeighbour(p: PreparedGrid, cell: number, visit: (n: number, distM: number) => void) {
  const { width, height, cellSizeM } = p.grid
  const r = (cell / width) | 0
  const c = cell - r * width
  for (let k = 0; k < 8; k++) {
    const nr = r + DR[k]
    const nc = c + DC[k]
    if (nr < 0 || nr >= height || nc < 0 || nc >= width) continue
    if (DIAG[k] && (!isPassable(p, nr * width + c) || !isPassable(p, r * width + nc))) continue
    visit(nr * width + nc, DIAG[k] ? cellSizeM * Math.SQRT2 : cellSizeM)
  }
}

/** Fastest walking path between two cells, or null when there is none. */
export function findPath(p: PreparedGrid, start: number, goal: number): Path | null {
  if (!isPassable(p, start) || !isPassable(p, goal)) return null
  if (start === goal) return { cells: [start], timeS: 0 }

  const { width, cellSizeM } = p.grid
  const { g, came, closed } = p.scratch
  g.fill(Infinity)
  came.fill(-1)
  closed.fill(0)

  // Admissible: octile distance at the fastest speed any step can reach, with the smallest multiplier (1).
  const secondsPerCell = cellSizeM / maxWalkingSpeedMs(p.params)
  const goalR = (goal / width) | 0
  const goalC = goal - goalR * width
  const heuristic = (cell: number) => {
    const r = (cell / width) | 0
    const dr = Math.abs(r - goalR)
    const dc = Math.abs(cell - r * width - goalC)
    return (Math.max(dr, dc) + (Math.SQRT2 - 1) * Math.min(dr, dc)) * secondsPerCell
  }

  const heap = createHeap()
  g[start] = 0
  heap.push(heuristic(start), start)
  while (heap.size() > 0) {
    const cell = heap.pop()
    if (closed[cell]) continue
    if (cell === goal) return { cells: reconstruct(came, goal), timeS: g[goal] }
    closed[cell] = 1
    forEachNeighbour(p, cell, (n, distM) => {
      if (closed[n]) return
      const t = g[cell] + stepTime(p, cell, n, distM)
      if (t < g[n]) {
        g[n] = t
        came[n] = cell
        heap.push(t + heuristic(n), n)
      }
    })
  }
  return null
}

function reconstruct(came: Int32Array, goal: number): number[] {
  const cells = [goal]
  for (let c = came[goal]; c !== -1; c = came[c]) cells.push(c)
  return cells.reverse()
}

/**
 * Seconds to walk from every cell back to `base` (Infinity where unreachable).
 * One Dijkstra pass from the base over reversed edges: the value at u uses stepTime(u → v), the
 * direction the astronaut actually walks, so uphill/downhill asymmetry is respected.
 */
export function walkHomeField(p: PreparedGrid, base: number): Float32Array {
  const n = p.grid.width * p.grid.height
  const time = new Float32Array(n).fill(Infinity)
  if (!isPassable(p, base)) return time
  const { g, closed } = p.scratch
  g.fill(Infinity)
  closed.fill(0)

  const heap = createHeap()
  g[base] = 0
  heap.push(0, base)
  while (heap.size() > 0) {
    const v = heap.pop()
    if (closed[v]) continue
    closed[v] = 1
    time[v] = g[v]
    forEachNeighbour(p, v, (u, distM) => {
      if (closed[u]) return
      const t = g[v] + stepTime(p, u, v, distM)
      if (t < g[u]) {
        g[u] = t
        heap.push(t, u)
      }
    })
  }
  return time
}
