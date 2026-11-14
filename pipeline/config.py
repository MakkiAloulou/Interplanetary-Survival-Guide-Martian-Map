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

# ---------- Real datasets (CLAUDE.md §8; provenance in data/SOURCES.md) ----------

# USGS MSL Gale Merged DEM 1m v3 (Parker & Calef 2016; HiRISE + CTX + HRSC tied to MOLA). Same product as the
# Mars Trek layer Gale_DEM_SMG_1m. Source: https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m
GALE_DEM_URL = "https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif"
# Extra DEM read around the site before warping, m, so bilinear resampling at the edges has neighbours.
GALE_DEM_CLIP_MARGIN_M = 100.0

# ---------- Habitat placement on a real site (MODELED: team rule, no official habitat site exists) ----------

# A pad this wide, every cell under the slope limit, for the habitat and the rover to park on.
HABITAT_PAD_RADIUS_M = 30.0
HABITAT_PAD_MAX_SLOPE_DEG = 8.0
# Keep the habitat and its traffic off the science terrain it was sent to study.
HABITAT_MIN_DISTANCE_FROM_SCIENCE_M = 300.0
# Rover parked this far east of the habitat, on the same pad.
ROVER_OFFSET_EAST_M = 30.0
# Science centre of the site: Curiosity's 2025-26 boxwork campaign, mean of MMGIS waypoints sols 4560-4841
# (https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json, retrieved 2026-11-14). OBSERVED positions.
GALE_SCIENCE_CENTER = (-4.8051, 137.3814)

# Curiosity traverse, one point per drive (JPL MMGIS). Source: https://mars.nasa.gov/maps/location/?mission=MSL
MSL_WAYPOINTS_URL = "https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json"
# A rover stop on ground a suited walker cannot reach (e.g. a steep ridge wall) moves to the nearest reachable cell
# within this distance; farther than this, the stop is dropped. MODELED: team rule (arm's reach plus a few steps).
TARGET_MAX_SNAP_M = 20.0

# Curiosity raw images (official resource 5, Curiosity equivalent). JSON API behind the raw-image gallery.
MSL_RAW_IMAGES_API = "https://mars.nasa.gov/api/v1/raw_image_items/"
MSL_RAW_IMAGE_PAGE = "https://mars.nasa.gov/raw_images/"
# Stop views: Navcam frames looking out over the terrain (mast elevation in this range, degrees), up to this many per
# stop, spread around the compass. Copies are resized for the app (team choice, keeps the repo small).
POV_NAVCAM_EL_RANGE_DEG = (-25.0, -5.0)
POV_NAVCAM_PER_STOP = 3
# Mast azimuths within this many degrees of straight back (180° in the rover frame) mostly show the rover's own deck
# and power source; such frames are used only when nothing else exists. Measured on the selected frames (~190°).
POV_SKIP_REAR_HALF_ANGLE_DEG = 35.0
POV_IMAGE_PX = 768
POV_THUMB_PX = 240

# THEMIS night-time infrared, controlled global mosaic, 100 m (Mars Odyssey; ASU / USGS), served by NASA Mars Trek.
# Deepest TileMatrix in its WMTSCapabilities is 9 (~81 m per tile pixel at the equator).
THEMIS_NIGHT_IR_LAYER = "THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018"
THEMIS_NIGHT_IR_ZOOM = 9
# Side of site image overlays sampled from tiles, px (each source pixel shows as a ~10 px block; no smoothing).
OVERLAY_PX = 500

# ---------- Sand and boulders from the HiRISE orthophoto (pipeline/surface.py; MODELED: team rule) ----------

# USGS MSL Gale Merged Orthophoto Mosaic 25cm v3 (same project as the Gale DEM). Source:
# https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm
GALE_ORTHO_URL = "https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_Orthophoto_Mosaic_25cm_v3.tif"
SURFACE_SAMPLE_M = 0.25  # orthophoto samples per cell side: 2 m / 0.25 m = 8
SURFACE_CONTEXT_CELLS = 5  # "darker than the surroundings" = below the mean of the 11 x 11 cells (22 m) around
SAND_SMOOTH_PERCENTILE = 35.0  # smooth = speckle in the lowest 35% of the site
SAND_MAX_SLOPE_DEG = 15.0  # sand settles in hollows, not on steep faces
SAND_MIN_NEIGHBOURS = 5  # of the 3 x 3 cells, so sand comes in patches, not single cells
BOULDER_SPECKLE_PERCENTILE = 98.0  # the most speckled 2% of the site
BOULDER_MIN_NEIGHBOURS = 4  # of the 3 x 3 cells: clusters, not single fractures

# ---------- Weather: Curiosity REMS daily reports (pipeline/sources/msl_weather.py) ----------

# NASA "Mars Weather" feed of Curiosity's REMS station (Spanish Centro de Astrobiología instrument). Daily values only.
MSL_WEATHER_URL = "https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json"
# The sol the plan uses: sol 4718 (2025-11-13), the day Curiosity drilled Nevado Sajama on this site (mission blog).
MSL_WEATHER_SOL = 4718
# REMS air temperature at Gale peaks in the early afternoon; hour of the maximum, local mean solar time. MODELED.
REMS_MAX_TEMP_LMST = 13.5
# Column dust opacity for the feed's opacity words, which carry no number. MODELED: assumed clear-sky and cloudy values.
SUNNY_DUST_TAU = 0.6
CLOUDY_DUST_TAU = 1.0

# 360° views rendered from the real terrain: farthest ray, m (the site is 2 km wide; beyond the grid is haze anyway).
PANORAMA_MAX_DISTANCE_M = 3000.0

# ---------- Space weather: NASA DONKI (pipeline/sources/donki.py; rule MODELED) ----------

# How far back to look for CME simulations that could reach Mars during the planned sol (CMEs take 1-5 days), days.
SPACE_WEATHER_LOOKBACK_DAYS = 7
# Half-width of the window around a forecast CME arrival at Mars, hours: about the typical error of CME arrival
# forecasts (roughly half a day). Direct non-minor arrivals = radiation ALERT (NO-GO); minor/glancing = ADVISORY.
CME_ARRIVAL_UNCERTAINTY_H = 12.0
