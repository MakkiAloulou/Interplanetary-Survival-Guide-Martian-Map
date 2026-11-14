# Martian Map

**Google Maps directions for one Marswalk.** A hyperlocal route planner for a two-astronaut + rover excursion through the boxwork ridges of Mount Sharp, Gale Crater. Built for the NASA Space Apps Challenge 2026, *Interplanetary Survival Guide: Martian Map*.

Mars Trek and the USGS geologic maps work at global and regional scale. This tool works at the scale of one walk: a few km² at meter resolution. It plans a route that stays on the ridges, avoids the sand, reaches the science stops, and always keeps the walk home within the O2 budget. Every verdict is GO / NO-GO with reasons.

Three views of the same data: **habitat** (planning), **tablet** (on the walk), **HUD** (helmet visor).

Every value is labeled `OBSERVED`, `DERIVED`, `MODELED` or `MOCK`. Until the official resources are released (Nov 13), all terrain is `MOCK`.

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
python -m pipeline --help
```
