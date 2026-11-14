"""CLI entry point: python -m pipeline <command>. `mock` writes the synthetic site; `build` converts a real DEM."""

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

    args = parser.parse_args(argv)
    if args.command == "build":
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
