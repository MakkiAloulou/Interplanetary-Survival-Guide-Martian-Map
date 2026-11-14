/** "2 h 05 min", "45 min", "under 1 min". */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds)) return 'unbounded'
  const sign = seconds < 0 ? '-' : ''
  const totalMin = Math.round(Math.abs(seconds) / 60)
  if (totalMin === 0) return 'under 1 min'
  const h = Math.floor(totalMin / 60)
  const m = totalMin % 60
  return h === 0 ? `${sign}${m} min` : `${sign}${h} h ${String(m).padStart(2, '0')} min`
}

/** "850 m", "2.4 km". */
export function formatDistance(metres: number): string {
  return metres < 1000 ? `${Math.round(metres)} m` : `${(metres / 1000).toFixed(1)} km`
}
