# Martian Map

**Google Maps directions for one Marswalk.** A hyperlocal route planner for two suited astronauts and a support rover, walking through the boxwork ridges of Mount Sharp in Gale Crater, where Curiosity worked in 2025–26. Built for the NASA Space Apps Challenge 2026, *Interplanetary Survival Guide: Martian Map*.

**Live app:** https://interplanetary-survival-guide-marti-red.vercel.app
**Example plan** (four real Curiosity stops, rover staged as a radio relay): [open it](https://interplanetary-survival-guide-marti-red.vercel.app/#stops=t:msl-panorama,t:msl-valle-de-la-luna,t:msl-nevado-sajama,t:msl-nodules&rover=2)

## Why

Mars Trek and the USGS geologic maps work at global and regional scale. A crew on foot needs the scale of one walk: a 2 × 2 km site at 2 m resolution. Martian Map plans that walk on real terrain, keeps it on the ridges and off the sand, takes it to the science, and judges it **GO or NO-GO, always with the reasons**.

## What it does

- **Plans the route** with A* over a walking-time model: Tobler's hiking function, slowed for a spacesuit, with uphill and downhill treated differently. Slopes of 25° or more and no-go ground are impassable. It offers a safest route by default, and a faster one only when the time saved is worth the extra hazard.
- **Runs the safety checks:**
  - **O₂ budget:** the walk must fit the suit's 8 h with a 30 min reserve.
  - **Point of no return:** from every point on the route, an emergency walk home at 1.5× the planned time must still fit the remaining O₂.
  - **Sunset:** the crew must be back at least 30 min before sunset, from the Mars24 clock.
  - **Radiation:** alerts and the background dose.
  - **Radio line of sight:** to the habitat mast or the staged rover.
  - **Space weather:** CME forecasts for Mars.
- **Stages the rover** at any stop as a second safe haven and radio relay. The walk-home map, the point-of-no-return check and the radio check all use it.
- **Shows each science stop:** what to look at and why, from NASA's mission reports; the kit and who does what; real Curiosity photos taken at that spot; and a 360° view rendered from the terrain.
- **Compares with the rover:** Curiosity's real path is drawn on the map. A line under the verdict states how many sols Curiosity spent on the plan's stops, against one Marswalk.
- **Three views of the same plan:**
  - the **habitat planner** (this page);
  - a **tablet view** carried on the walk: map following the crew, next stop, live warnings, abort;
  - a **helmet HUD:** bearing, distance, O₂, walk-home margin, short alerts.
- **Shares and prints:** every plan is a link; plans can be saved in the browser; a two-sided A4 card prints the route, the checks and each stop.

## Real data, labelled honestly

Every value is labelled `OBSERVED`, `DERIVED`, `MODELED` or `MOCK`, and nothing in the app is `MOCK`.

| Layer or input | Source | Label |
|---|---|---|
| Base map | MRO HiRISE Curiosity-site mosaic (NASA Mars Trek) | OBSERVED |
| Elevation, slope, hillshade | USGS MSL Gale Merged DEM 1 m (HiRISE, CTX, HRSC) | DERIVED |
| Sand and rocky ground | Our rule applied to the USGS Gale 25 cm HiRISE orthophoto | MODELED |
| Night-time warmth (rock vs sand) | Mars Odyssey THEMIS night IR, 100 m (Mars Trek) | OBSERVED |
| Science stops, Curiosity's path | Curiosity traverse (JPL MMGIS), mission blog, JPL news | DERIVED / OBSERVED |
| Stop photos | Curiosity Navcam and Hazcam raw images | OBSERVED |
| 360° views | Rendered from the DEM and orthophoto (not photos) | DERIVED |
| Weather on the planned sol | Curiosity REMS daily report, sol 4718 (2025-11-13) | MODELED (measured min/max, assumed curve) |
| Space weather | NASA DONKI: WSA-Enlil CME forecasts for Mars | MODELED |
| Walking speed, O₂, limits, habitat position, antenna heights | Our stated assumptions, each documented in the config | MODELED |

No mineral layer: the official resources have no CRISM data over this site (checked; see [data/SOURCES.md](data/SOURCES.md)).

Full provenance for every dataset (product IDs, URLs, processing and checks) is in **[data/SOURCES.md](data/SOURCES.md)**.

## Credits and AI use

Built with the help of an AI coding assistant (Claude Code). **[CREDITS.md](CREDITS.md)** explains where AI was used and lists every data, code, font and method source. No NASA logos or branding are used, and no AI-generated images or video.

## Run it locally

The site data the app needs is already in the repo, so after cloning:

```bash
cd app
npm install
npm run dev        # open the address it prints
npm test           # unit tests
npm run build      # static build in app/dist
```

You need Node.js 22.12 or newer, and an internet connection: the HiRISE base map loads live from Mars Trek. Python is only needed to rebuild the data.

## Rebuild the data (optional)

Python 3.11+, from the repo root. Downloads are cached in `data/raw/` (git-ignored).

```bash
pip install -r pipeline/requirements.txt
python -m pytest                       # pipeline tests

python -m pipeline gale-surface        # USGS DEM + 25 cm orthophoto → terrain grid with sand and rocky ground, habitat placed
python -m pipeline msl-targets         # Curiosity's boxwork stops placed on the grid
python -m pipeline msl-traverse        # Curiosity's path inside the site
python -m pipeline msl-images          # Curiosity raw images at each stop
python -m pipeline gale-panoramas      # 360° views rendered at the habitat and the stops
python -m pipeline themis-night-ir     # THEMIS night-IR overlay
python -m pipeline msl-weather         # REMS weather for sol 4718
python -m pipeline donki               # space weather around that sol (NASA_API_KEY optional, DEMO_KEY otherwise)
python -m pipeline msl-weather         # again, so DONKI radiation alerts reach the conditions
```

`python -m pipeline build --dem <file.tif> --bbox <lonmin,latmin,lonmax,latmax> --out data/processed/<name>` converts any other elevation GeoTIFF into a terrain grid. See `--help` for sand and boulder masks.

## Layout

```
app/        Vite + React + TypeScript + Leaflet; route engine in a Web Worker (Vitest)
pipeline/   Python data pipeline: one converter per dataset in pipeline/sources/ (pytest)
data/       config.json, SOURCES.md (provenance), processed/ (what the app reads)
```

The app's optional what-if copilot (`app/src/copilot/`) runs in offline mode when its server is not running, as on the live site.
