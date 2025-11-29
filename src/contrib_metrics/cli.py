from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from .aggregation.run_manager import run_from_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="contrib-metrics",
        description="Compute contribution metrics from a configuration file.",
    )
    parser.add_argument(
        "command",
        nargs="?",
        help="Subcommand (optional, currently only 'compute').",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        required=True,
        help="Path to YAML configuration file.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command not in (None, "compute"):
        parser.error(f"Unknown command: {args.command}")

    run_from_config(args.config)


if __name__ == "__main__":
    main()
