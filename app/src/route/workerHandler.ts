// Message protocol of the route worker, as a plain function so it can be tested without a Worker.

import { parseCostGrid } from '../costGrid'
import type { CostGridMeta } from '../types'
import { DEFAULT_ROUTE_PARAMS, prepareGrid, type PreparedGrid, type RouteParams } from './cost'
import { planRoute, type RouteResult } from './route'
import { walkHomeField } from './search'

export type WorkerRequest =
  | { type: 'init'; id: number; meta: CostGridMeta; buffer: ArrayBuffer; params?: RouteParams }
  | { type: 'route'; id: number; stops: number[] }
  | { type: 'walkHome'; id: number; base: number }

export type WorkerResponse =
  | { type: 'init'; id: number }
  | { type: 'route'; id: number; result: RouteResult }
  | { type: 'walkHome'; id: number; field: Float32Array }
  | { type: 'error'; id: number; message: string }

export interface WorkerState {
  prepared: PreparedGrid | null
}

/** Handles one request. Returns the response and any buffers to transfer back. */
export function handleRequest(state: WorkerState, req: WorkerRequest): { response: WorkerResponse; transfer: Transferable[] } {
  try {
    if (req.type === 'init') {
      state.prepared = prepareGrid(parseCostGrid(req.meta, req.buffer), req.params ?? DEFAULT_ROUTE_PARAMS)
      return { response: { type: 'init', id: req.id }, transfer: [] }
    }
    if (!state.prepared) throw new Error('route worker not initialised: send init first')
    if (req.type === 'route') {
      return { response: { type: 'route', id: req.id, result: planRoute(state.prepared, req.stops) }, transfer: [] }
    }
    const field = walkHomeField(state.prepared, req.base)
    return { response: { type: 'walkHome', id: req.id, field }, transfer: [field.buffer] }
  } catch (e) {
    return { response: { type: 'error', id: req.id, message: e instanceof Error ? e.message : String(e) }, transfer: [] }
  }
}
