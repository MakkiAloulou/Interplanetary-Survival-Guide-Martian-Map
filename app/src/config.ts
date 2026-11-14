// Constants and thresholds. Each one carries its source and status.
// MODELED = assumption we chose; tune when the official resources (Nov 13) give better numbers.
// Mirror any value the pipeline also needs in pipeline/config.py.

import { TERRAIN, type TerrainClass } from './types'

// ---------- Mars physical constants ----------

/** Volumetric mean radius, m. Use for distances along the surface (haversine). Source: NASA GSFC Mars Fact Sheet. */
export const MARS_MEAN_RADIUS_M = 3_389_500

/** Equatorial radius, m. Use for the map projection (equirectangular CRS). Source: IAU / MOLA reference, NASA GSFC Mars Fact Sheet. */
export const MARS_EQUATORIAL_RADIUS_M = 3_396_190

/** Meters per degree of latitude in the map projection. Derived from MARS_EQUATORIAL_RADIUS_M. */
export const METERS_PER_DEG_LAT = (2 * Math.PI * MARS_EQUATORIAL_RADIUS_M) / 360

/** Surface gravity, m/s². Source: NASA GSFC Mars Fact Sheet. */
export const MARS_GRAVITY_MS2 = 3.721

// ---------- Walking speed (Tobler's hiking function) ----------
// v = TOBLER_MAX_SPEED_KMH · exp(−TOBLER_DECAY · |tanθ + TOBLER_SLOPE_OFFSET|) · SUIT_SPEED_FACTOR
// Source: Tobler, W. (1993), "Three presentations on geographical analysis and modeling", NCGIA TR 93-1.

/** Peak walking speed on Earth, km/h (reached on a 5% downhill). Source: Tobler 1993. */
export const TOBLER_MAX_SPEED_KMH = 6

/** Exponential decay with slope. Source: Tobler 1993. */
export const TOBLER_DECAY = 3.5

/** Downhill offset of the fastest gradient (tanθ = −0.05). Source: Tobler 1993. */
export const TOBLER_SLOPE_OFFSET = 0.05

/**
 * Speed multiplier for a suited astronaut carrying equipment. MODELED: team assumption
 * (CLAUDE.md §5 default). Suit mass, joint stiffness and the 0.38 g gait are not in Tobler's data.
 */
export const SUIT_SPEED_FACTOR = 0.6

// ---------- Trafficability ----------

/** Slope above which walking cost is penalized, degrees. MODELED: team assumption (CLAUDE.md §5). */
export const SLOPE_PENALTY_START_DEG = 15

/** Slope at or above which a cell is impassable on foot, degrees. MODELED: team assumption (CLAUDE.md §5). */
export const SLOPE_IMPASSABLE_DEG = 25

/**
 * Extra cost per degree above SLOPE_PENALTY_START_DEG, as a fraction of base cost
 * (cost × (1 + k·(θ − start))). 0.2 → ×3 at 25°. MODELED: team assumption.
 */
export const SLOPE_PENALTY_PER_DEG = 0.2

/** Cost multiplier per terrain class. Infinity = impassable. MODELED: team assumption (CLAUDE.md §5). */
export const TERRAIN_COST_MULTIPLIER: Record<TerrainClass, number> = {
  [TERRAIN.BEDROCK]: 1,
  [TERRAIN.SAND]: 2, // loose sand in boxwork hollows: wheel slip for Curiosity, slow footing for crew
  [TERRAIN.BOULDERS]: 4,
  [TERRAIN.NO_GO]: Infinity,
}

// ---------- Life support and EVA timeline ----------

/**
 * Usable suit O2 for one EVA, minutes. MODELED: assumption based on the ~8 h EVA
 * design target of NASA's xEMU / Artemis surface suits. Replace with resource docs if given.
 */
export const SUIT_O2_DURATION_MIN = 480

/** O2 that must still remain on arrival back at base, minutes. MODELED: team assumption. */
export const O2_RESERVE_MIN = 30

/** Default time spent working at each science stop, minutes. MODELED: team assumption. */
export const SCIENCE_STOP_DWELL_MIN = 20

/** Crew must be back at base this long before local sunset, minutes. MODELED: team assumption. */
export const SUNSET_MARGIN_MIN = 30

/**
 * Emergency walk home is assumed this much slower than a planned walk (fatigue, suit fault,
 * helping a partner). Drives the point-of-no-return check. MODELED: team assumption.
 */
export const WALK_HOME_CONTINGENCY_FACTOR = 1.5

// ---------- Radiation ----------

/**
 * Baseline surface dose equivalent at Gale Crater, mSv/day. OBSERVED: Curiosity RAD,
 * Hassler et al. (2014), Science 343, 1244797 (0.64 ± 0.12 mSv/day).
 */
export const RAD_BASELINE_DOSE_MSV_PER_DAY = 0.64
