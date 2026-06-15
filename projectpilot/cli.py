"""Command line interface for ProjectPilot Agent."""

from __future__ import annotations

import argparse
from pathlib import Path

from projectpilot.config import load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="projectpilot",
        description="ProjectPilot Agent Day 1 skeleton CLI.",
    )
    subparsers = parser.add_subparsers(dest="command")

    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Load a config and print a Day 1 mock analysis summary.",
    )
    analyze_parser.add_argument(
        "--config",
        required=True,
        help="Path to a projectpilot.yaml config file.",
    )

    return parser


def run_analyze(config_path: str) -> int:
    path = Path(config_path)
    load_config(path)

    print("ProjectPilot Agent skeleton is ready.")
    print(f"Config loaded: {config_path}")
    print("No real analysis executed yet.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        return run_analyze(args.config)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
