#!/usr/bin/env python3
"""Download the RA-Bench media and metadata release from Hugging Face."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import snapshot_download


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("RA-Bench"))
    parser.add_argument("--repo-id", default="liangshuo0111/RA-Bench")
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--workers", type=int, default=16)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_XET_HIGH_PERFORMANCE", "1")
    snapshot_download(
        repo_id=args.repo_id,
        repo_type="dataset",
        local_dir=args.output,
        endpoint=args.endpoint,
        token=os.environ.get("HF_TOKEN") or None,
        max_workers=args.workers,
        allow_patterns=["media/**", "metadata/**"],
    )
    print(f"RA-Bench downloaded to {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

