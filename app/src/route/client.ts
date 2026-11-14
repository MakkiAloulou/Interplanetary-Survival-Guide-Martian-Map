// Promise wrapper around the route worker, for the UI.

import type { CostGridMeta } from '../types'
import type { RouteParams } from './cost'
import type { RouteResult } from './route'
import type { WorkerResponse } from './workerHandler'

export interface RouteClient {
  /** Hands the grid to the worker. The buffer is transferred: it is unusable on this thread afterwards. */
  init(meta: CostGridMeta, buffer: ArrayBuffer, params?: RouteParams): Promise<void>
  route(stops: number[]): Promise<RouteResult>
  walkHome(base: number): Promise<Float32Array>
  terminate(): void
}

export function createRouteClient(): RouteClient {
  const worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' })
  const pending = new Map<number, { resolve: (r: WorkerResponse) => void; reject: (e: Error) => void }>()
  let nextId = 1

  worker.onmessage = (e: MessageEvent<WorkerResponse>) => {
    const p = pending.get(e.data.id)
    if (!p) return
    pending.delete(e.data.id)
    if (e.data.type === 'error') p.reject(new Error(e.data.message))
    else p.resolve(e.data)
  }

  function send(message: object, transfer: Transferable[] = []): Promise<WorkerResponse> {
    const id = nextId++
    return new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject })
      worker.postMessage({ ...message, id }, transfer)
    })
  }

  return {
    init: async (meta, buffer, params) => {
      await send({ type: 'init', meta, buffer, params }, [buffer])
    },
    route: async (stops) => {
      const r = await send({ type: 'route', stops })
      if (r.type !== 'route') throw new Error(`unexpected response ${r.type}`)
      return r.result
    },
    walkHome: async (base) => {
      const r = await send({ type: 'walkHome', base })
      if (r.type !== 'walkHome') throw new Error(`unexpected response ${r.type}`)
      return r.field
    },
    terminate: () => worker.terminate(),
  }
}
