import { useEffect, useState, type ReactNode } from 'react'
import type { LayerState } from '../map/MapView'
import { HAZARD_COLORS, HAZARD_LABELS, WALK_HOME_BANDS, WALK_HOME_UNREACHABLE, type GridOverlayMode, type Hazard } from '../map/overlays'
import { formatMarsClock, ltstHours, marsTime } from '../marsTime'
import type { DataConfig, DataStatus } from '../types'
import { CloseIcon, LayersIcon, TabletIcon, VisorIcon } from '../ui/icons'
import { StatusBadge } from '../ui/StatusBadge'

interface Props {
  config: DataConfig
  baseLon: number
  gridStatus: DataStatus
  layerState: Record<string, LayerState>
  onLayerChange: (id: string, state: LayerState) => void
  overlay: GridOverlayMode
  onOverlayChange: (mode: GridOverlayMode) => void
  panel: 'layers' | 'conditions' | null
  onPanel: (panel: 'layers' | 'conditions' | null) => void
  conditionsPanel: ReactNode
  stormActive: boolean
  hudEnabled: boolean
  onHud: () => void
  onTablet: () => void
}

const OVERLAYS: { mode: GridOverlayMode; label: string }[] = [
  { mode: 'none', label: 'Off' },
  { mode: 'slope', label: 'Slope' },
  { mode: 'terrain', label: 'Terrain' },
  { mode: 'walkhome', label: 'Walk home' },
]

function MarsClock({ lon, open, alert, onClick }: { lon: number; open: boolean; alert: boolean; onClick: () => void }) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const t = marsTime(now)
  return (
    <button
      type="button"
      className={`chip-float clock ${alert ? 'is-alert' : ''}`}
      aria-expanded={open}
      title={`Mars sol date ${t.msd.toFixed(2)} · season Ls ${t.lsDeg.toFixed(1)}° · open conditions`}
      onClick={onClick}
    >
      {alert && <span className="alert-dot" aria-label="Radiation alert" />}
      <span className="clock-label">Mars local time</span>
      <strong>{formatMarsClock(ltstHours(t, lon))}</strong>
      <StatusBadge status="DERIVED" />
    </button>
  )
}

export function MapControls(props: Props) {
  const { config, baseLon, gridStatus, layerState, onLayerChange, overlay, onOverlayChange } = props
  const { panel, onPanel, conditionsPanel, stormActive, hudEnabled, onHud, onTablet } = props
  const toggle = (p: 'layers' | 'conditions') => onPanel(panel === p ? null : p)
  return (
    <div className="map-controls">
      <div className="map-controls-row">
        <MarsClock lon={baseLon} open={panel === 'conditions'} alert={stormActive} onClick={() => toggle('conditions')} />
        <button type="button" className="chip-float layers-btn" aria-expanded={panel === 'layers'} aria-controls="layers-panel" onClick={() => toggle('layers')}>
          <LayersIcon size={18} />
          Layers
        </button>
        <button type="button" className="chip-float layers-btn" disabled={!hudEnabled} title={hudEnabled ? 'Tablet carried on the walk' : 'Plan a route first'} onClick={onTablet}>
          <TabletIcon size={18} />
          Tablet
        </button>
        <button type="button" className="chip-float layers-btn" disabled={!hudEnabled} title={hudEnabled ? 'Helmet visor view' : 'Plan a route first'} onClick={onHud}>
          <VisorIcon size={18} />
          HUD
        </button>
      </div>

      {panel === 'conditions' && conditionsPanel}

      {panel === 'layers' && (
        <section id="layers-panel" className="card layers-panel" aria-label="Map layers">
          <header className="layers-head">
            <h2>Map layers</h2>
            <button type="button" className="icon-btn" aria-label="Close layers" onClick={() => onPanel(null)}>
              <CloseIcon size={16} />
            </button>
          </header>

          <ul className="layer-list">
            {config.layers.map((layer) => {
              const state = layerState[layer.id]
              return (
                <li key={layer.id}>
                  <label className="layer-toggle">
                    <input type="checkbox" checked={state.visible} onChange={(e) => onLayerChange(layer.id, { ...state, visible: e.target.checked })} />
                    <span className="layer-name">
                      {layer.name}
                      <small>{layer.dataType}</small>
                    </span>
                    <StatusBadge status={layer.status} />
                  </label>
                  {state.visible && (
                    <input
                      className="opacity"
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={state.opacity}
                      aria-label={`${layer.name} opacity`}
                      onChange={(e) => onLayerChange(layer.id, { ...state, opacity: Number(e.target.value) })}
                    />
                  )}
                </li>
              )
            })}
          </ul>

          <h3 id="overlay-h">
            Trafficability <StatusBadge status={gridStatus} />
          </h3>
          <div className="segmented" role="radiogroup" aria-labelledby="overlay-h">
            {OVERLAYS.map(({ mode, label }) => (
              <button key={mode} type="button" role="radio" aria-checked={overlay === mode} onClick={() => onOverlayChange(mode)}>
                {label}
              </button>
            ))}
          </div>
          {overlay === 'walkhome' ? (
            <>
              <p className="note">Minutes to the nearest safe haven (habitat, or the rover where it is staged), at planned pace.</p>
              <ul className="legend" aria-label="Walk-home time colours">
                {[...WALK_HOME_BANDS, WALK_HOME_UNREACHABLE].map((b) => (
                  <li key={b.label}>
                    <span className="swatch" style={{ background: b.color }} />
                    {b.label}
                  </li>
                ))}
              </ul>
            </>
          ) : (
            <ul className="legend" aria-label="Route and terrain colours">
              {(Object.keys(HAZARD_COLORS) as Hazard[]).map((h) => (
                <li key={h}>
                  <span className="swatch" style={{ background: HAZARD_COLORS[h] }} />
                  {h === 'clear' ? 'Clear walking' : HAZARD_LABELS[h]}
                </li>
              ))}
            </ul>
          )}
          {gridStatus === 'MOCK' && (
            <p className="note">Terrain, targets and conditions are a synthetic site placed on the real HiRISE imagery. They do not match the ground you see.</p>
          )}
        </section>
      )}
    </div>
  )
}
