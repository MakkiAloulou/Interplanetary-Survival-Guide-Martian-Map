import type { DataStatus } from '../types'

const TITLES: Record<DataStatus, string> = {
  OBSERVED: 'Direct measurement',
  DERIVED: 'Computed from observations',
  MODELED: 'Based on assumptions',
  MOCK: 'Placeholder, not real data',
}

/** Every value in the UI shows where it comes from (CLAUDE.md §4 Scientific honesty). */
export function StatusBadge({ status }: { status: DataStatus }) {
  return (
    <span className={`badge badge-${status.toLowerCase()}`} title={TITLES[status]}>
      {status}
    </span>
  )
}
