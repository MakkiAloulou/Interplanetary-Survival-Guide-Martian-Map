# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- **Astronaut crew (persona the tool is built for):** two suited astronauts plus a support rover on a Marswalk through the Mount Sharp boxwork, Gale Crater. They plan in the habitat on a large screen, carry a tablet on the walk, and see a helmet-visor HUD.
- **NASA Space Apps 2026 judges:** they meet the product through a 2-3 minute demo video and a live demo. The screen must read as credible mission software an astronaut could actually use, and land its point within that demo.

Both audiences are confirmed as equal priority.

## Product Purpose

"Google Maps directions for one Marswalk." A hyperlocal route planner for the few square kilometres one crew covers on one excursion, at metre resolution. It plans a walk that stays on the boxwork ridges, avoids the sandy hollows, reaches the science stops, and always keeps the walk home inside the O2 budget. Success: a crew (or a judge) can see the route, the stops, and a GO / NO-GO verdict with its reasons, and trust where every number comes from.

## Positioning

Mars Trek and the USGS geologic maps work at global and regional scale. This works at the scale of one walk: suit-speed walking times (Tobler's function × suit factor), a walk-home field from every cell, and a point-of-no-return check against O2. Every value is labelled OBSERVED, DERIVED, MODELED or MOCK.

## Operating Context

- Habitat planning view first (large screen): build and compare routes, review conditions, assign tasks. Tablet view and HUD view come later from the same data.
- Site: boxwork on the sulfate-bearing unit of Mount Sharp, Gale Crater. Ridges 1-2 m tall, ~5 m wide, sandy hollows between.
- Map base: real MRO HiRISE imagery via NASA Mars Trek. Terrain, targets, conditions and POV images are synthetic (MOCK) until the official resources arrive on Nov 13, 2026.
- Hackathon: Nov 14-15, 2026.

## Capabilities and Constraints

- Static web app (Vite + React + TypeScript + Leaflet), no backend. Route engine (A*, walk-home Dijkstra) runs in a Web Worker on a 1000 x 1000 grid at 2 m cells.
- Built today: layer toggles and opacity, slope / terrain overlay, click to add stops (science targets or via points), route coloured by hazard, GO / NO-GO panel with reasons, stations table with arrival times, EVA line strip, Mars24 clock.
- Terms: Marswalk, EVA, habitat, support rover, science stop, via point, walk-home, point of no return, sol, LMST/LTST, Ls.
- Data statuses must be visible in the UI; MOCK or MODELED is never presented as OBSERVED.

## Brand Commitments

Name "Martian Map". No logo, colours or team name fixed yet.

## Evidence on Hand

- Real: MRO HiRISE Curiosity roving-site mosaic tiles (Mars Trek). Mars24 algorithm verified against NASA GISS worked examples.
- Synthetic (MOCK): terrain grid, six science targets, panoramas, conditions, habitat position (`data/processed/mock/`).
- No real crew, mission, testimonials or partner endorsements exist; none may be implied.

## Product Principles

1. Safety reads first: a verdict always comes with its reasons.
2. Honest provenance: every number shows how it was obtained.
3. Hyperlocal over global: metre-scale detail of one walk beats planet-wide breadth.
4. Calm under load: an astronaut in a suit, or a judge in a 2-minute demo, must not have to hunt.

## Accessibility & Inclusion

Not yet specified. Legibility at a distance (habitat screen) and in a demo video is a practical requirement.
