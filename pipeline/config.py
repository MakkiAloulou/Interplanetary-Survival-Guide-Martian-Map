"""Pipeline constants. Each one carries its source. Values shared with the app mirror app/src/config.ts and app/src/types.ts."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

# ---------- Contract values (mirror app/src/types.ts) ----------

DATA_STATUSES = ("OBSERVED", "DERIVED", "MODELED", "MOCK")

# CostGrid.terrainClass codes.
TERRAIN_BEDROCK = 0
TERRAIN_SAND = 1
TERRAIN_BOULDERS = 2
TERRAIN_NO_GO = 3

# ---------- Mars physical constants (mirror app/src/config.ts) ----------

# Volumetric mean radius, m. Surface distances. Source: NASA GSFC Mars Fact Sheet.
MARS_MEAN_RADIUS_M = 3_389_500.0

# Equatorial radius, m. Map projection (equirectangular). Source: IAU / MOLA reference, NASA GSFC Mars Fact Sheet.
MARS_EQUATORIAL_RADIUS_M = 3_396_190.0

# Length of a mean solar day (sol), s. Source: Allison & McEwen (2000), Planet. Space Sci. 48, 215.
MARS_SOL_S = 88_775.244

# ---------- Trafficability (mirror app/src/config.ts) ----------

# Slope at or above which a cell is impassable on foot, degrees. MODELED: team assumption (CLAUDE.md §5).
SLOPE_IMPASSABLE_DEG = 25.0

# ---------- Mock site (Phase 2) ----------
# Everything below is MOCK: shapes chosen to look like the Mount Sharp boxwork, not measured.
# Positions inside the site are fractions of the site size so small test grids keep the same layout.

# Site centre, degrees. Placeholder near Curiosity's 2025 boxwork area, unverified (CLAUDE.md §6, §8 step 2).
MOCK_CENTER_LAT = -4.80
MOCK_CENTER_LON = 137.38

# Square site side and grid cell size, m. CLAUDE.md §7 Phase 2: ~2 x 2 km at 2 m cells.
MOCK_SIZE_M = 2000.0
MOCK_CELL_SIZE_M = 2.0
MOCK_SEED = 2026

# Elevation at site centre, m (areoid). Rough level of the sulfate unit Curiosity reached in 2025
# (several hundred m above the -4501 m landing site). MOCK guess.
MOCK_BASE_ELEVATION_M = -3700.0
# Regional rise toward Mount Sharp (south), m/m (~1.7 deg). MOCK guess.
MOCK_REGIONAL_GRADE = 0.03
# Low-frequency relief: amplitude (m) and length scale (m).
MOCK_UNDULATION_M = 3.0
MOCK_UNDULATION_SCALE_M = 200.0

# Boxwork polygon spacing, m. MOCK guess; check against HiRISE once available.
MOCK_BOXWORK_SPACING_M = 25.0
# Ridge height range, m. CLAUDE.md §2: ridges roughly 1-2 m tall.
MOCK_RIDGE_HEIGHT_M = (1.0, 2.0)
# Ridge cross-section: flat top half-width + cosine flank width, m. ~5 m wide at mid-height (CLAUDE.md §2).
MOCK_RIDGE_TOP_HALF_WIDTH_M = 1.0
MOCK_RIDGE_FLANK_WIDTH_M = 3.0
# Fraction of the area where ridges are broken down to low saddles (crossing points).
MOCK_RIDGE_BREAK_FRACTION = 0.12
# Fraction of hollow floors covered by loose sand.
MOCK_SAND_FRACTION_IN_HOLLOWS = 0.75

# The one steep wall: a north-facing scarp across the west of the site, tapering to a ramp in the east.
MOCK_WALL_HEIGHT_M = 8.0
MOCK_WALL_FACE_WIDTH_M = 1.2  # logistic width of the face; peak slope ~60 deg
MOCK_WALL_Y_FRAC = 0.375  # mean northing of the wall line
MOCK_WALL_AMPLITUDE_FRAC = 0.025  # meander of the wall line
MOCK_WALL_END_X_FRAC = 0.675  # wall tapers out east of this
MOCK_WALL_TAPER_M = 150.0

# Habitat position and the smooth bedrock pad around it (no boxwork).
MOCK_BASE_XY_FRAC = (0.775, 0.85)
MOCK_BASE_CLEAR_FRAC = (0.075, 0.15)  # boxwork ramps in between these radii

# Boulder clusters per 2 x 2 km and their radius range, m.
MOCK_BOULDER_CLUSTERS = 18
MOCK_BOULDER_RADIUS_M = (12.0, 35.0)

# Thermal inertia by surface type, J m^-2 K^-1 s^-1/2. Typical Mars ranges: sand ~150-350, bedrock several
# hundred, rock > 1000 (Fergason et al. 2006, JGR 111, E12004). MOCK values.
MOCK_TI = {"sand": 220.0, "bedrock": 450.0, "ridge": 700.0, "boulders": 1000.0}
# Resolutions the mock layers are degraded to, m/pixel, so they are no sharper than the real
# products: THEMIS thermal inertia ~100 m, CRISM ~18 m.
MOCK_THEMIS_PIXEL_M = 100.0
MOCK_CRISM_PIXEL_M = 18.0

# Panoramas: astronaut eye height above ground, m (MODELED), render size and reach.
POV_EYE_HEIGHT_M = 1.7
POV_WIDTH_PX = 1024
POV_HEIGHT_PX = 256
POV_VFOV_DEG = 90.0
POV_MAX_DISTANCE_M = 1500.0
