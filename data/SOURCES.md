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

Everything else (sand and boulder classes, thermal and mineralogy layers, POV images, conditions) is still synthetic (`MOCK`) or MODELED, labelled as such, until it is replaced through CLAUDE.md §8.
