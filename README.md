# Martian Map

**Google Maps directions for one Marswalk.** A hyperlocal route planner for a two-astronaut + rover excursion through the boxwork ridges of Mount Sharp, Gale Crater. Built for the NASA Space Apps Challenge 2026, *Interplanetary Survival Guide: Martian Map*.

Mars Trek and the USGS geologic maps work at global and regional scale. This tool works at the scale of one walk: a few km² at meter resolution. It plans a route that stays on the ridges, avoids the sand, reaches the science stops, and always keeps the walk home within the O2 budget. Every verdict is GO / NO-GO with reasons.

Three views of the same data: **habitat** (planning), **tablet** (on the walk), **HUD** (helmet visor).

Every value is labeled `OBSERVED`, `DERIVED`, `MODELED` or `MOCK`. Terrain comes from the real USGS Gale elevation model (HiRISE/CTX/HRSC). Science targets, stop panoramas, weather, thermal and mineralogy are still `MOCK` until they are replaced with real data.

## Credits and AI use

Built with the help of an AI coding assistant (Claude Code). [CREDITS.md](CREDITS.md) explains where AI was used and lists every data, code, font and method source. No NASA logos or branding are used.

## Layout

```
app/        Vite + React + TypeScript + Leaflet (Vitest)
pipeline/   Python 3.11 raster pipeline (pytest)
data/       config.json, SOURCES.md (provenance), raw/ (git-ignored), processed/
docs/       resources.md (official Resources tab)
```

See [CLAUDE.md](CLAUDE.md) for the full design, data contracts and phase plan.

## Run

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
python -m pipeline mock   # writes the MOCK site to data/processed/mock/ (~30 s)
python -m pipeline build --dem dtm.tif --bbox 137.36,-4.82,137.40,-4.78 --out data/processed/gale
                          # real elevation model -> CostGrid + hillshade (see --help for --sand/--boulders masks)
```
