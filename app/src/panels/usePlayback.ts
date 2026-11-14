import { useEffect, useRef, useState } from 'react'

export const PLAYBACK_SPEEDS = [60, 300, 900]

/** The EVA clock for demoing a walk: play at a speed-up, pause, or scrub. Shared by the tablet and the HUD. */
export function usePlayback(totalS: number) {
  const [t, setT] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(300)
  const last = useRef<number | null>(null)

  useEffect(() => {
    if (!playing) return
    let raf = 0
    const tick = (now: number) => {
      if (last.current !== null) {
        setT((v) => {
          const next = v + ((now - last.current!) / 1000) * speed
          if (next >= totalS) setPlaying(false)
          return Math.min(next, totalS)
        })
      }
      last.current = now
      raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => {
      cancelAnimationFrame(raf)
      last.current = null
    }
  }, [playing, speed, totalS])

  const done = t >= totalS
  return {
    t,
    playing,
    speed,
    done,
    setSpeed,
    /** jump to an EVA time and stop playing */
    seek: (s: number) => {
      setPlaying(false)
      setT(Math.max(0, Math.min(totalS, s)))
    },
    toggle: () => {
      if (done) {
        setT(0)
        setPlaying(true)
      } else setPlaying((v) => !v)
    },
    pause: () => setPlaying(false),
  }
}
