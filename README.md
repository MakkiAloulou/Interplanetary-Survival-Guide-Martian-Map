# Martian Map

**Google Maps directions for one Marswalk.** A hyperlocal route planner for a two-astronaut + rover excursion through the boxwork ridges of Mount Sharp, Gale Crater. Built for the NASA Space Apps Challenge 2026, *Interplanetary Survival Guide: Martian Map*.

Mars Trek and the USGS geologic maps work at global and regional scale. This tool works at the scale of one walk: a few km² at meter resolution. It plans a route that stays on the ridges, avoids the sand, reaches the science stops, and always keeps the walk home within the O2 budget. Every verdict is GO / NO-GO with reasons.

Three views of the same data: **habitat** (planning), **tablet** (on the walk), **HUD** (helmet visor).

Every value is labeled `OBSERVED`, `DERIVED`, `MODELED` or `MOCK`. All data is real NASA/USGS data: HiRISE imagery and the Gale elevation model, sand and rocky ground mapped from the HiRISE orthophoto, THEMIS night-time infrared, Curiosity's traverse, stop photos and REMS weather. Assumptions (walking model, O₂, safety limits) are labelled `MODELED`.

## Credits and AI use

Built with the help of an AI coding assistant (Claude Code). [CREDITS.md](CREDITS.md) explains where AI was used and lists every data, code, font and method source. No NASA logos or branding are used.

## Layout

```
app/        Vite + React + TypeScript + Leaflet (Vitest)
pipeline/   Python 3.11 raster pipeline (pytest)
data/       config.json, SOURCES.md (provenance), raw/ (git-ignored), processed/
docs/       resources.md (official Resources tab)
```


## Run

The site data the app needs is in the repo (`data/config.json`, `data/processed/`). After cloning, `npm install` and `npm run dev` are enough; no pipeline step is required.

```bash
# App
cd app
npm install
npm run dev        # dev server
npm test           # unit tests
npm run build      # static build

# Pipeline (from repo root)
pip install -r pipeline/requirements.txt
python -m pytest
python -m pipeline mock        # writes the MOCK site to data/processed/mock/ (~30 s)
python -m pipeline gale-dem    # rebuilds data/processed/gale/ from the USGS Gale DEM (downloads ~1-2 min, cached in data/raw/)
python -m pipeline msl-targets # re-places the Curiosity boxwork science stops on that grid

# Generic converter for any other elevation GeoTIFF (replace <your_dem.tif>; writes to a NEW folder,
# never over data/processed/gale/, which must match data/config.json):
python -m pipeline build --dem <your_dem.tif> --bbox <lonmin,latmin,lonmax,latmax> --out data/processed/<name>
                               # see --help for the --sand/--boulders masks
```
