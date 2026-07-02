#!/usr/bin/env python3
"""Write Claude Code status-bar segment selections."""

from __future__ import annotations

import json
import sys

from status_bar_config import SEGMENT_IDS, _write_config


def write_segments(config_path: str, segments: list[str]) -> None:
    ordered = [seg for seg in SEGMENT_IDS if seg in segments]
    _write_config(config_path, ordered)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        print("Usage: status_bar_segment_install.py CONFIG_PATH JSON_SEGMENTS", file=sys.stderr)
        return 2
    segments = json.loads(args[1])
    write_segments(args[0], [str(item) for item in segments])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())