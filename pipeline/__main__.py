"""CLI entry point: python -m pipeline <command>. `mock` writes the synthetic site; `build` converts a real DEM;
`gale-dem` clips and converts the USGS Gale DEM for the site; `msl-targets` places Curiosity's boxwork stops;
`msl-images` fetches Curiosity raw images at those stops; `themis-night-ir` cuts the THEMIS night-IR overlay;
`gale-surface` maps sand and boulders from HiRISE and rebuilds the CostGrid with them;
`msl-weather` turns a Curiosity REMS daily report into the planned sol's conditions;
`gale-panoramas` renders 360° views at the stations from the real terrain;
`crism` makes the mineral overlay from an MRO CRISM observation."""

import argparse
import json
import sys
from pathlib import Path

from pipeline import config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline")
    commands = parser.add_subparsers(dest="command")

    mock = commands.add_parser("mock", help="generate the MOCK boxwork site (Phase 2)")
    mock.add_argument("--out", type=Path, default=config.DATA_DIR / "processed" / "mock")
    mock.add_argument("--seed", type=int, default=config.MOCK_SEED)

    build = commands.add_parser("build", help="convert a real elevation model (GeoTIFF) into a CostGrid (Phase 8)")
    build.add_argument("--dem", type=Path, required=True, help="elevation GeoTIFF, metres, any CRS")
    build.add_argument("--bbox", required=True, help="lonmin,latmin,lonmax,latmax (degrees, east-positive)")
    build.add_argument("--out", type=Path, required=True, help="output folder, e.g. data/processed/gale")
    build.add_argument("--cell-size", type=float, default=config.MOCK_CELL_SIZE_M, help="grid cell size, m")
    build.add_argument("--sand", help="sand mask raster with a rule, e.g. thermal_inertia.tif:<300 (default rule >0)")
    build.add_argument("--boulders", help="boulder mask raster with a rule, e.g. rocks.tif:>0")
    build.add_argument("--source", default="", help="provenance line stored in the CostGrid metadata")

    gale = commands.add_parser("gale-dem", help="USGS MSL Gale Merged DEM 1m -> CostGrid for the site in data/config.json")
    gale.add_argument("--out", type=Path, default=config.DATA_DIR / "processed" / "gale")
    gale.add_argument("--refresh", action="store_true", help="download the clip again instead of using data/raw/")

    commands.add_parser("msl-targets", help="Curiosity boxwork campaign -> science targets for the Gale site")
    commands.add_parser("msl-traverse", help="Curiosity's drive path inside the site -> map line")
    commands.add_parser("msl-images", help="Curiosity raw images at the science stops -> stop views")
    commands.add_parser("gale-panoramas", help="360° views at the habitat and stops, rendered from the real terrain")
    commands.add_parser("donki", help="NASA DONKI space weather around the planned sol -> alerts and events")
    commands.add_parser("msl-weather", help="Curiosity REMS daily weather report -> conditions for the planned sol")
    commands.add_parser("gale-surface", help="sand and boulder masks from the HiRISE orthophoto -> CostGrid rebuilt with them")
    commands.add_parser("themis-night-ir", help="THEMIS night-time infrared (Mars Trek) -> thermal overlay for the site")
    commands.add_parser("crism", help="MRO CRISM summary parameters (PDS) -> mineral overlay for the site")

    args = parser.parse_args(argv)
    if args.command == "donki":
        from pipeline.sources.donki import convert as convert_donki

        print(json.dumps(convert_donki(), indent=2))
    elif args.command == "msl-traverse":
        from pipeline.sources.msl_targets import convert_traverse

        print(json.dumps(convert_traverse(), indent=2))
    elif args.command == "gale-panoramas":
        from pipeline.sources.gale_panoramas import convert as convert_panoramas

        print(json.dumps(convert_panoramas(), indent=2))
    elif args.command == "msl-weather":
        from pipeline.sources.msl_weather import convert as convert_weather

        print(json.dumps(convert_weather(), indent=2))
    elif args.command == "gale-surface":
        from pipeline.sources.gale_dem import convert_surface

        print(json.dumps(convert_surface(), indent=2))
    elif args.command == "crism":
        from pipeline.sources.crism import convert as convert_crism

        print(json.dumps(convert_crism(), indent=2))
    elif args.command == "themis-night-ir":
        from pipeline.sources.trek_overlay import convert_themis_night_ir

        print(json.dumps(convert_themis_night_ir(), indent=2))
    elif args.command == "msl-images":
        from pipeline.sources.msl_images import convert as convert_images

        print(json.dumps(convert_images(), indent=2))
    elif args.command == "msl-targets":
        from pipeline.sources.msl_targets import convert as convert_targets

        print(json.dumps(convert_targets(), indent=2))
    elif args.command == "gale-dem":
        from pipeline.sources.gale_dem import convert

        print(json.dumps(convert(args.out, refresh=args.refresh), indent=2))
    elif args.command == "build":
        from pipeline.build import build as build_grid, parse_bbox

        summary = build_grid(
            args.dem, parse_bbox(args.bbox), args.out, args.cell_size, sand=args.sand, boulders=args.boulders, source=args.source
        )
        print(json.dumps(summary, indent=2))
    elif args.command == "mock":
        from pipeline.mock import build_mock

        out = args.out.resolve()
        try:
            url_prefix = out.relative_to(config.DATA_DIR.resolve()).as_posix()
        except ValueError:
            url_prefix = out.name
        summary = build_mock(out, url_prefix=url_prefix, seed=args.seed)
        print(json.dumps(summary, indent=2))
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
