// Authored icons: 24px grid, 1.75 stroke, round caps, currentColor.

import type { ReactNode } from 'react'

interface IconProps {
  size?: number
  title?: string
}

function Svg({ size = 18, title, children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={title ? undefined : true}
      role={title ? 'img' : undefined}
    >
      {title && <title>{title}</title>}
      {children}
    </svg>
  )
}

export function CloseIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M6 6l12 12M18 6L6 18" />
    </Svg>
  )
}

/** The wordmark's mark: a line bending at 45° through an interchange ring. */
export function LineMark(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M2 20h5l5-5" />
      <path d="M17 10l5-5" />
      <circle cx="14.5" cy="12.5" r="3" />
    </Svg>
  )
}

export function LayersIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3l9 5-9 5-9-5z" />
      <path d="M3 13l9 5 9-5" />
    </Svg>
  )
}

export function TabletIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <rect x="4" y="3" width="16" height="18" rx="2.5" />
      <path d="M10.5 18h3" />
    </Svg>
  )
}

/** A helmet visor seen from the front. */
export function VisorIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M4 13a8 8 0 0 1 16 0v3a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3z" />
      <path d="M7 12.5c1.5-1.5 8.5-1.5 10 0" />
    </Svg>
  )
}

/** Six dots: a handle to drag a row. */
export function GripIcon(props: IconProps) {
  return (
    <Svg {...props}>
      {[8, 16].map((x) => [6, 12, 18].map((y) => <circle key={`${x}-${y}`} cx={x} cy={y} r="1.3" fill="currentColor" stroke="none" />))}
    </Svg>
  )
}

export function AlertIcon(props: IconProps) {
  return (
    <Svg {...props}>
      <path d="M12 3l9.5 17h-19z" />
      <path d="M12 10v4.5M12 17.5v.01" />
    </Svg>
  )
}
