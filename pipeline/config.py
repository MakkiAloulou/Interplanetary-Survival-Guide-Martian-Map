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

# ---------- Trafficability (mirror app/src/config.ts) ----------

# Slope at or above which a cell is impassable on foot, degrees. MODELED: team assumption (CLAUDE.md §5).
SLOPE_IMPASSABLE_DEG = 25.0
