#!/usr/bin/env python3
"""Verify the file-level completeness of a downloaded RA-Bench release."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED_MEDIA_FILES = 25_575
EXPECTED_MEDIA_BYTES = 93_772_561_883
EXPECTED_METADATA = {
    "ra_bench_humanproof.csv",
    "ra_bench_humanproof.jsonl",
    "ra_bench_lastmile.csv",
    "ra_bench_lastmile.jsonl",
    "ra_bench_main.csv",
    "ra_bench_main.jsonl",
    "real_rights_release.csv",
    "release_inventory.json",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    args = parser.parse_args()

    media_root = args.root / "media"
    metadata_root = args.root / "metadata"
    media = [path for path in media_root.rglob("*") if path.is_file()]
    metadata = (
        {path.name for path in metadata_root.iterdir() if path.is_file()}
        if metadata_root.is_dir()
        else set()
    )
    private_paths = [
        str(path.relative_to(args.root))
        for path in args.root.rglob("*")
        if "private_archive" in path.parts
    ]
    result = {
        "media_files": len(media),
        "expected_media_files": EXPECTED_MEDIA_FILES,
        "media_bytes": sum(path.stat().st_size for path in media),
        "expected_media_bytes": EXPECTED_MEDIA_BYTES,
        "metadata_files": sorted(metadata),
        "expected_metadata_files": sorted(EXPECTED_METADATA),
        "private_archive_paths": len(private_paths),
    }
    result["verified"] = (
        result["media_files"] == EXPECTED_MEDIA_FILES
        and result["media_bytes"] == EXPECTED_MEDIA_BYTES
        and metadata == EXPECTED_METADATA
        and not private_paths
    )
    print(json.dumps(result, indent=2))
    return 0 if result["verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
