# Credits and AI use

Martian Map, NASA Space Apps Challenge 2026, *Interplanetary Survival Guide: Martian Map*.

This project is not endorsed by NASA or any space agency. It uses no NASA logos or branding. "NASA" appears only where we credit a data source.

## Use of AI

We used **Claude Code** (Anthropic's AI coding assistant, model Claude Opus) throughout the project:

- **Code:** most of the app (`app/`) and the data pipeline (`pipeline/`), including their tests, were written by the AI from our instructions. We set the requirements, reviewed the work, ran it, and made every commit.
- **Research:** the AI searched the web and NASA/USGS servers to find and check data. That covered the Curiosity traverse, the coverage of the Gale elevation model, and the dates of the boxwork campaign. Each source it found is listed below.
- **Documentation:** the README, this file, the design notes and the in-app wording were drafted with the AI.
- **Design:** the AI drafted the interface layout and the app's icons. We chose the design direction, and rejected an earlier dark design.
- **Decisions:** the site, the crew model, the safety rules and their thresholds, and the final site bounds were our decisions. The AI proposed options and we approved or changed them.

**No AI-generated images or videos** are used. The stop photos are real Curiosity raw images (NASA/JPL-Caltech). Earlier mock 360° panoramas were rendered by our own code from a synthetic terrain model, never by an image-generation model; the app no longer uses them. If the demo video uses any AI-generated imagery, voice or footage, it will be watermarked as AI-generated.

## Data

| Data | Credit | Where it comes from | How we use it |
|---|---|---|---|
| MRO HiRISE Curiosity roving-site mosaic | NASA/JPL-Caltech/University of Arizona | NASA Mars Trek, layer `curiosity_hirise_mosaic` (https://trek.nasa.gov/mars/) | Base map, shown as served |
| MSL Gale Merged DEM 1m v3 | USGS Astrogeology Science Center; T. Parker and F. J. Calef III (2016). Built from MRO HiRISE (NASA/JPL-Caltech/University of Arizona), MRO CTX (NASA/JPL-Caltech/MSSS), Mars Express HRSC (ESA/DLR/FU Berlin) and MGS MOLA (NASA/GSFC) | https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_dem_1m (Mars Trek layer `Gale_DEM_SMG_1m`) | Elevation, slope, hillshade and walking costs at 2 m |
| MSL Gale Merged Orthophoto Mosaic 25cm v3 | USGS Astrogeology Science Center; MRO HiRISE (NASA/JPL-Caltech/University of Arizona) | https://astrogeology.usgs.gov/search/map/mars_msl_gale_merged_orthophoto_mosaic_25cm | Mapping sand (smooth, dark hollow floors) and rocky ground, by our own rule (MODELED) |
| Curiosity traverse (rover waypoints) | NASA/JPL-Caltech, MMGIS | https://mars.nasa.gov/mmgis-maps/MSL/Layers/json/MSL_waypoints.json | Locating the 2025–26 boxwork campaign; choosing the site and the science centre; placing the science stops where Curiosity stood |
| Boxwork science stops: what Curiosity studied and why | NASA/JPL-Caltech: Curiosity mission blog (science.nasa.gov/blog), posts for sols 4561–4562, 4689–4694, 4709–4715, 4716–4722 and 4804–4811; JPL news 2025-06-23 and 2026-02-23 | URLs per stop in `pipeline/sources/msl_boxwork_targets.json` | Stop names, dates and the "why" texts (paraphrased) |
| Curiosity raw images at the stops (Navcam, Front Hazcam) | NASA/JPL-Caltech | https://mars.nasa.gov/msl/multimedia/raw-images/ (each image links to its own page) | Stop photos: what the ground looks like on arrival, and the drill workspaces. Resized copies; no other change. |
| THEMIS night-time infrared mosaic, 100 m | NASA/JPL-Caltech/Arizona State University (Mars Odyssey THEMIS) | NASA Mars Trek, layer `THEMIS_NightIR_ControlledMosaics_100m_v2_oct2018` | Thermal layer: where the ground keeps its heat at night (rock) and where it cools (sand, dust) |
| Curiosity REMS daily weather report, sol 4718 | NASA/JPL-Caltech/CAB (CSIC-INTA), Rover Environmental Monitoring Station | https://mars.nasa.gov/rss/api/?feed=weather&category=msl&feedtype=json | Weather on the planned sol: measured min/max air temperature and pressure, and sunrise/sunset used as a check of our Mars clock |
| Mars surface radiation dose rate | Hassler, D. M. et al. (2014), *Science* 343, 1244797 (Curiosity RAD) | Published paper | Radiation dose of a Marswalk (0.64 mSv/day) |
| Mars radius, gravity | NASA Goddard Space Flight Center, Mars Fact Sheet | https://nssdc.gsfc.nasa.gov/planetary/factsheet/marsfact.html | Distances, map projection |
| Boxwork science context | NASA/JPL news releases on Curiosity's boxwork campaign (2025) | https://www.jpl.nasa.gov/news/nasas-curiosity-mars-rover-starts-unpacking-boxwork-formations/ and https://www.jpl.nasa.gov/news/nasas-curiosity-rover-sees-martian-spiderwebs-up-close/ | Choosing the site and the science goals |

Full processing details for each dataset are in `data/SOURCES.md`.

**Synthetic (MOCK) content:** none left; every dataset is real. Assumptions are labelled `MODELED` (see below).

### Official challenge resources

| Resource | Used? |
|---|---|
| NASA Mars Trek | Yes: HiRISE base map, Gale elevation model, Curiosity traverse, THEMIS night-infrared layer. Its CRISM mineral mosaics do not cover our site (checked). |
| USGS Astrogeology interactive maps | Yes: the Gale elevation model and the Gale 25 cm HiRISE orthophoto (used to map sand and rocky ground) |
| Curiosity's proposed path up Mount Sharp (2019 animation) | Context for the demo story only |
| NASA Worldview | Design reference only (layered maps, data-source labels). No data used. |
| Mars 2020 raw images | Its Curiosity equivalent is used: the stop photos come from the Curiosity raw-image archive (https://mars.nasa.gov/msl/multimedia/raw-images/), because our site is Gale, not Jezero |

## Methods and algorithms

- **Mars clock and sun position:** the Mars24 algorithm, Allison, M. and McEwen, M. (2000), *Planetary and Space Science* 48, 215–235, as published by NASA GISS (https://www.giss.nasa.gov/tools/mars24/help/algorithm.html). We implemented it ourselves (with the AI, as above).
- **Walking speed:** Tobler's hiking function, Tobler, W. (1993), *Three presentations on geographical analysis and modeling*, NCGIA Technical Report 93-1. The spacesuit factor (0.6) is our assumption.
- **Slope and hillshade:** Horn, B. K. P. (1981), "Hill shading and the reflectance map", *Proceedings of the IEEE* 69(1).
- **Route search:** A* (Hart, Nilsson and Raphael, 1968) and Dijkstra's algorithm (1959) for the walk-home times. Stop order uses branch-and-bound and 2-opt (Croes, 1958).
- **Suit O₂ duration (8 h):** our assumption, based on the published EVA design goal of NASA's Artemis surface suits (xEMU).

All other thresholds (slope limits, terrain costs, reserves, the habitat placement rule) are our own assumptions. The app labels them `MODELED`. Each one has its reason written next to it in `app/src/config.ts` and `pipeline/config.py`.

## Software

| Software | License | Use |
|---|---|---|
| React, React DOM | MIT | App interface |
| Leaflet | BSD-2-Clause | Map |
| Vite, @vitejs/plugin-react | MIT | Build tool |
| TypeScript | Apache-2.0 | Language |
| Vitest | MIT | App tests |
| NumPy | BSD-3-Clause (and bundled permissive licenses) | Pipeline arrays |
| rasterio, with its bundled GDAL | BSD-3-Clause; GDAL MIT | Reading and reprojecting elevation models |
| pytest | MIT | Pipeline tests |
| Python, Node.js | PSF License; MIT | Runtimes |

## Fonts and icons

- **Barlow** by Jeremy Tribby, SIL Open Font License 1.1, from Google Fonts (https://fonts.google.com/specimen/Barlow). Self-hosted in `app/public/fonts/`.
- **Icons and favicon:** drawn for this project (with the AI, as above). No icon library is used.
