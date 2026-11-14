# Data sources and provenance

One entry per real dataset used by the app or pipeline (CLAUDE.md §4). Anything not listed here is `MOCK`.

Template:

```
## <Dataset name>
- Mission / instrument:
- Product ID:
- URL:
- Resolution:
- Coverage of site:
- License / credit:
- Date retrieved:
- Processing applied:
- Used as: <layer id / contract field>, status <OBSERVED|DERIVED>
```

---

## MRO HiRISE, Curiosity Roving Site Mosaic (via NASA Mars Trek)
- Mission / instrument: Mars Reconnaissance Orbiter (MRO) / High Resolution Imaging Science Experiment (HiRISE)
- Product ID: Mars Trek layer `curiosity_hirise_mosaic` ("MRO HiRISE, Curiosity Roving Site Mosaic")
- URL: https://trek.nasa.gov/tiles/Mars/EQ/curiosity_hirise_mosaic/1.0.0/WMTSCapabilities.xml
- Tiles: `https://trek.nasa.gov/tiles/Mars/EQ/curiosity_hirise_mosaic/1.0.0//default/default028mm/{z}/{y}/{x}.png` (ResourceURL template from GetCapabilities; Style `default`, TileMatrixSet `default028mm`)
- Resolution: TileMatrix 0-16, 256 px tiles, equirectangular, top-left -180/90, 2^(z+1) x 2^z tiles; level 16 = ~0.64 m/pixel in this tiling (HiRISE native ~0.25-0.5 m/pixel)
- Coverage of site: yes. Layer bbox lon 137.1224669-137.7298129, lat -4.9254743 to -4.2489588; sample tiles at (-4.80, 137.38) for z12/z14/z16 contain imagery
- License / credit: NASA/JPL-Caltech/University of Arizona; served by NASA Mars Trek (JPL)
- Date retrieved: 2026-10-30 (tiles are fetched live by the app)
- Processing applied: none; displayed as served
- Used as: layer `hirise`, status OBSERVED

## USGS MSL Gale Merged DEM 1m v3 (Mars Trek layer `Gale_DEM_SMG_1m`)
- Mission / instrument: MRO HiRISE, MRO CTX and Mars Express HRSC stereo DEMs, tied to MGS MOLA; merged by USGS Astrogeology (T. Parker, F. J. Calef III, 2016)
- Product ID: `MSL_Gale_DEM_Mosaic_1m_v3.tif` ("Mars MSL Gale Merged DEM 1m"); shown on NASA Mars Trek as `Gale_DEM_SMG_1m` (official resource 1)
- URL: https://planetarymaps.usgs.gov/mosaic/Mars/MSL/MSL_Gale_DEM_Mosaic_1m_v3.tif (product page https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m)
- Resolution: 1 m posting; float32 metres, nodata -32767; equirectangular (eqc, lon_0 0, R 3396190 m); 32980 x 57440 px. Effective resolution coarser than 1 m (stereo noise): slope at 1 m overstates steepness, so the app uses 2 m cells.
- Coverage of site: yes, whole site box, no nodata; real metre-scale relief at the boxwork (checked 2026-11-14, docs/resources.md)
- License / credit: USGS Astrogeology Science Center / NASA; HiRISE NASA/JPL-Caltech/University of Arizona; CTX NASA/JPL-Caltech/MSSS; HRSC ESA/DLR/FU Berlin
- Date retrieved: 2026-11-14 (only the site rows, read over HTTP with GDAL /vsicurl/)
- Processing applied: `python -m pipeline gale-dem` → site box + 100 m margin copied unchanged to `data/raw/gale_dem_1m_site.tif`; `pipeline/build.py` warps it bilinearly onto 2 m square cells in Mars geographic coordinates (R 3396190 m, the app's map sphere), Horn slope with the true 2 m cell size, hillshade (sun NW 45°). No sand or boulder mask yet: every measured cell is bedrock (terrainClass MODELED); cells without elevation would be NO_GO (none in this box).
- Used as: CostGrid `processed/gale/costgrid.json` (elevation, slopeDeg DERIVED; terrainClass MODELED), status DERIVED
- Used as: layer `hillshade`, status DERIVED

## Curiosity boxwork campaign: traverse and science stops
- Mission / instrument: Mars Science Laboratory, Curiosity rover (NASA/JPL-Caltech). Positions from the rover's localized drive end-points; science from the mission blog and JPL news.
- Product ID: MMGIS layer "Waypoints" (`MSL_waypoints.json`, 1389 points, sol 3-5073 at retrieval)
- URL: https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json (MMGIS map: https://mars.nasa.gov/maps/location/?mission=MSL). Reports cited per stop in `pipeline/sources/msl_boxwork_targets.json`: JPL news 2025-06-23 and 2026-02-23; Curiosity blog posts for sols 4561-4562, 4689-4694, 4709-4715, 4716-4722, 4804-4811 (science.nasa.gov/blog).
- Resolution: one point per drive; positions to about a metre
- Coverage of site: yes; the 2025-26 boxwork campaign (sols ~4541-4841) lies inside the site
- License / credit: NASA/JPL-Caltech
- Date retrieved: 2026-11-14
- Processing applied: `python -m pipeline msl-targets`. 7 curated stops (first ridge close-up, Altadena drill, nodules, panorama viewpoint, Valle de la Luna hollow drill, Nevado Sajama ridge drill, final-phase workspace), each placed at the last waypoint on or before its sol. Earth dates converted to sols from the blog's own pairs (sol 4560 = 2025-06-04, sol 4718 = 2025-11-13). A stop the habitat cannot reach on foot moves to the nearest reachable cell within 20 m and says so (nodules: 3 m off a 36° ridge wall); none dropped. `why` texts paraphrase the reports; crew kit is our MODELED choice.
- Used as: `processed/gale/science_targets.json` (ScienceTarget[]), status DERIVED

## Curiosity raw images at the science stops (Navcam, Front Hazcam)
- Mission / instrument: Mars Science Laboratory, Curiosity rover: left Navcam (NAV_LEFT_B) and left Front Hazcam (FHAZ_LEFT_B), engineering cameras (NASA/JPL-Caltech)
- Product ID: raw image ids listed per image in `processed/gale/pov_images.json` (e.g. NLB_813579644EDR_F1191722NCAM00259M); 21 Navcam + 3 Front Hazcam frames
- URL: https://mars.nasa.gov/msl/multimedia/raw-images/ (JSON API https://mars.nasa.gov/api/v1/raw_image_items/); each image links to its page https://mars.nasa.gov/raw_images/<id>
- Resolution: originals 1024 x 1024 px grayscale JPEG; app copies 768 px (thumbnails 240 px)
- Coverage of site: yes; every image was taken at a stop's own rover position (site/drive in the image id = the MMGIS waypoint)
- License / credit: NASA/JPL-Caltech (credit line as given by the raw-image API)
- Date retrieved: 2026-11-14
- Processing applied: `python -m pipeline msl-images`. Per stop: left-Navcam full frames from the arrival sol with mast elevation -25° to -5° (looking out over the terrain), views within 35° of straight back over the rover deck skipped, up to 3 spread around the compass; plus the latest Front Hazcam full frame of the drill workspace on `workspaceSol` (Altadena 4568, Valle de la Luna 4693, Nevado Sajama 4718). Resized with averaging, JPEG quality 85; no other change. Viewing direction = waypoint yaw + mast azimuth (approximate; checked once against the DEM horizon at sol 4671).
- Used as: `processed/gale/pov_images.json` (PovImage[], isPanorama false), status OBSERVED

## THEMIS night-time infrared, controlled global mosaic 100 m (via NASA Mars Trek)
- Mission / instrument: 2001 Mars Odyssey / Thermal Emission Imaging System (THEMIS), night-time infrared; controlled mosaic (Arizona State University / USGS)
- Product ID: Mars Trek layer `THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018`
- URL: https://trek.nasa.gov/tiles/Mars/EQ/THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018/1.0.0/WMTSCapabilities.xml (tiles `.../1.0.0//default/default028mm/{z}/{row}/{col}.png`)
- Resolution: 100 m mosaic; deepest TileMatrix 9 (~81 m per tile pixel); 24.6 tile pixels across the 2 km site
- Coverage of site: yes (mosaic covers latitudes -65° to 65°)
- License / credit: NASA/JPL-Caltech/Arizona State University; served by NASA Mars Trek (JPL)
- Date retrieved: 2026-11-14
- Processing applied: `python -m pipeline themis-night-ir` (pipeline/sources/trek_overlay.py). Level-9 tile pixels sampled nearest (no smoothing) onto a 500 x 500 px image exactly covering the site; grey values (Trek's display stretch, 142-215 inside the site) stretched between their 2nd and 98th percentile and coloured cool (dark blue) to warm (yellow). Relative only: warm at night = material that keeps its heat (rock, high thermal inertia), cool = sand or dust. Too coarse for 2 m hollows; regional context.
- Used as: layer `themis-night-ir`, status OBSERVED

## Mineralogy: not available at the site
Checked 2026-11-14: Mars Trek's CRISM MTRDR browse mosaics (e.g. `frt_07_brhydj_mtr3_ll`) are built from 42 targeted observations for human-exploration sites, none over this site (ArcGIS layer `mars_mro_crism_mtrdr_c0a_humex_frt_sites`, envelope query: 0 features). The nearest OMEGA/CRISM hydrous-mineral detection in Trek is 15.7 km away (`Hydrous_Mineral_Detections_OMEGA_CRISM_clon0`). TES mineral and thermal-inertia maps (~3 km pixels) are coarser than the whole site. So the app has no mineral layer; the mock one was removed. Mineral findings at the stops (clay in the ridge sample, carbonate in the hollow sample) come from Curiosity's own analyses, cited in the stop texts.

Everything else (sand and boulder classes, conditions) is still synthetic (`MOCK`) or MODELED, labelled as such, until it is replaced through CLAUDE.md §8.
