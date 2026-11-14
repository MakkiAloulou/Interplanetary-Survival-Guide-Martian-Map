"""CLI entry point: python -m pipeline <command>. Commands are added per phase (build arrives in Phase 8)."""

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

    args = parser.parse_args(argv)
    if args.command == "mock":
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
