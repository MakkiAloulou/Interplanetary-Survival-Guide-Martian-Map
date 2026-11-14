import { describe, expect, test } from 'vitest'
import { METERS_PER_DEG_LAT } from '../config'
import { DEFAULT_ROUTE_PARAMS } from '../route/cost'
import { gridFrom } from '../testing/grids'
import { cellHazard, gridOverlayPixels, hazardRuns, legHazardSeconds } from './overlays'
import { metresPerPixel, tileAt, tileDegrees } from './tiles'

describe('Mars Trek tile matrix (from curiosity_hirise_mosaic WMTSCapabilities.xml)', () => {
  test('level 0 is 2 x 1 tiles from -180/90; level 16 is 131072 x 65536', () => {
    expect(tileAt(89.9, -179.9, 0)).toEqual({ row: 0, col: 0 })
    expect(tileAt(-89.9, 179.9, 0)).toEqual({ row: 0, col: 1 })
    expect(360 / tileDegrees(16)).toBe(131072)
    expect(180 / tileDegrees(16)).toBe(65536)
  })

  test('the site centre maps to the tiles fetched from Trek on 2026-10-30', () => {
    // GET .../curiosity_hirise_mosaic/1.0.0//default/default028mm/{z}/{row}/{col}.png returned imagery for these.
    expect(tileAt(-4.8, 137.38, 12)).toEqual({ row: 2157, col: 7222 })
    expect(tileAt(-4.8, 137.38, 14)).toEqual({ row: 8628, col: 28888 })
    expect(tileAt(-4.8, 137.38, 16)).toEqual({ row: 34515, col: 115554 })
  })

  test('level 16 is ~0.64 m per pixel on Mars', () => {
    expect(metresPerPixel(16, METERS_PER_DEG_LAT)).toBeCloseTo(0.633, 2)
  })
})

describe('grid overlays', () => {
  test('terrain: bedrock transparent, sand / boulders / no-go coloured', () => {
    const g = gridFrom(['.sb#'])
    const px = gridOverlayPixels(g, 'terrain', DEFAULT_ROUTE_PARAMS)
    const alpha = [3, 7, 11, 15].map((i) => px[i])
    expect(alpha[0]).toBe(0)
    expect(alpha.slice(1).every((a) => a > 0)).toBe(true)
  })

  test('slope: transparent up to the penalty start, stronger amber toward the limit, dark when impassable', () => {
    const g = gridFrom(['....'])
    g.slopeDeg.set([10, 16, 24, 30])
    const px = gridOverlayPixels(g, 'slope', DEFAULT_ROUTE_PARAMS)
    expect(px[3]).toBe(0)
    expect([px[4], px[5], px[6]]).toEqual([0xf9, 0xab, 0x00])
    expect(px[11]).toBeGreaterThan(px[7])
    expect([px[12], px[13], px[14]]).toEqual([0x20, 0x21, 0x24])
  })

  test('legHazardSeconds sums each step into the hazard of the cell it enters', () => {
    const g = gridFrom(['..ss.'])
    const track = [0, 1, 2, 3, 4].map((cell, i) => ({ cell, arriveS: i * 10, departS: i * 10, leg: 0 }))
    expect(legHazardSeconds(g, track, 0, DEFAULT_ROUTE_PARAMS)).toEqual({ clear: 20, steep: 0, sand: 20, boulders: 0, blocked: 0 })
  })
})

describe('route hazards', () => {
  test('cell hazard priority: blocked > boulders > sand > steep > clear', () => {
    const g = gridFrom(['.sb#^.'])
    g.slopeDeg[5] = 18
    expect([0, 1, 2, 3, 4, 5].map((c) => cellHazard(g, c, DEFAULT_ROUTE_PARAMS))).toEqual([
      'clear',
      'sand',
      'boulders',
      'blocked',
      'blocked',
      'steep',
    ])
  })

  test('runs share boundary cells so the drawn line is continuous', () => {
    const g = gridFrom(['..ss..'])
    const runs = hazardRuns(g, [0, 1, 2, 3, 4, 5], DEFAULT_ROUTE_PARAMS)
    expect(runs).toEqual([
      { hazard: 'clear', cells: [0, 1, 2] },
      { hazard: 'sand', cells: [2, 3, 4] },
      { hazard: 'clear', cells: [4, 5] },
    ])
  })
})
