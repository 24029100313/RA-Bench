#!/usr/bin/env python3
"""Reference evaluator for RA-Bench public manifests."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from sklearn.metrics import roc_auc_score, roc_curve


ROOT = Path(__file__).resolve().parents[1]
MAIN_MANIFEST = "ra_bench_main.csv"
HUMANPROOF_MANIFEST = "ra_bench_humanproof.csv"
LASTMILE_MANIFEST = "ra_bench_lastmile.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate predictions on RA-Bench release manifests."
    )
    parser.add_argument(
        "--track",
        choices=("main", "humanproof", "lastmile"),
        required=True,
    )
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument(
        "--metadata-dir",
        type=Path,
        default=ROOT / "metadata",
        help="Directory containing the released CSV manifests.",
    )
    parser.add_argument(
        "--coverage",
        choices=("full", "public-media"),
        default="public-media",
    )
    parser.add_argument(
        "--metrics",
        choices=("auto", "continuous", "discrete", "both"),
        default="auto",
    )
    parser.add_argument(
        "--include-auxiliary-control",
        action="store_true",
        help="Report fixed-duration Wan2.2 for LastMile without adding it to RA-Bench means.",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_predictions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))
    elif suffix in {".jsonl", ".ndjson"}:
        rows = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if line.strip():
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Invalid JSON on line {line_number}: {exc}"
                        ) from exc
    else:
        raise ValueError("Predictions must be CSV or JSONL.")

    indexed: dict[str, dict[str, Any]] = {}
    for line_number, row in enumerate(rows, start=2 if suffix == ".csv" else 1):
        item_id = str(row.get("item_id", "")).strip()
        if not item_id:
            raise ValueError(f"Missing item_id at record {line_number}.")
        if item_id in indexed:
            raise ValueError(f"Duplicate item_id: {item_id}")

        normalized: dict[str, Any] = {"item_id": item_id}
        raw_score = row.get("fake_score")
        if raw_score is not None and str(raw_score).strip() != "":
            try:
                score = float(raw_score)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"Invalid fake_score for {item_id}: {raw_score}") from exc
            if not math.isfinite(score):
                raise ValueError(f"Non-finite fake_score for {item_id}: {raw_score}")
            normalized["fake_score"] = score

        raw_prediction = row.get("prediction")
        if raw_prediction is not None and str(raw_prediction).strip() != "":
            prediction = str(raw_prediction).strip().lower()
            aliases = {"fake": "generated", "authentic": "real"}
            prediction = aliases.get(prediction, prediction)
            if prediction not in {"real", "generated"}:
                raise ValueError(
                    f"Invalid prediction for {item_id}: {raw_prediction}; "
                    "expected real or generated."
                )
            normalized["prediction"] = prediction
        indexed[item_id] = normalized
    return indexed


def public_real(row: dict[str, str]) -> bool:
    release_mode = row.get("release_mode", "")
    return bool(row.get("media_path")) and not release_mode.startswith("url_only")


def pair_record(
    generated_id: str,
    real_id: str,
    source_key: str,
    **extra: str,
) -> dict[str, str]:
    return {
        "generated_id": generated_id,
        "real_id": real_id,
        "source_key": source_key,
        **extra,
    }


def main_pairs(
    metadata_dir: Path, coverage: str
) -> dict[str, list[dict[str, str]]]:
    rows = read_csv(metadata_dir / MAIN_MANIFEST)
    real_by_norm = {
        row["norm_clip_id"]: row for row in rows if row["label"] == "real"
    }
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row["label"] != "generated":
            continue
        real = real_by_norm.get(row["norm_clip_id"])
        if real is None:
            raise ValueError(f"Missing real anchor for {row['item_id']}")
        if coverage == "public-media" and not public_real(real):
            continue
        grouped[row["source_key"]].append(
            pair_record(row["item_id"], real["item_id"], row["source_key"])
        )
    return dict(grouped)


def humanproof_pairs(
    metadata_dir: Path, coverage: str
) -> dict[str, list[dict[str, str]]]:
    rows = read_csv(metadata_dir / HUMANPROOF_MANIFEST)
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if coverage == "public-media" and row["paired_real_release_mode"] != "media":
            continue
        grouped[row["source_key"]].append(
            pair_record(
                row["item_id"],
                f"real::{row['norm_clip_id']}",
                row["source_key"],
            )
        )
    return dict(grouped)


def lastmile_pairs(
    metadata_dir: Path,
    coverage: str,
    include_auxiliary: bool,
) -> tuple[
    dict[tuple[str, str], list[dict[str, str]]], dict[tuple[str, str], str]
]:
    rows = read_csv(metadata_dir / LASTMILE_MANIFEST)
    real_by_key = {
        (row["condition"], row["norm_clip_id"]): row
        for row in rows
        if row["label"] == "real"
    }
    grouped: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    roles: dict[tuple[str, str], str] = {}
    for row in rows:
        if row["label"] != "generated":
            continue
        role = row["benchmark_role"]
        if role == "auxiliary_control" and not include_auxiliary:
            continue
        real = real_by_key.get((row["condition"], row["norm_clip_id"]))
        if real is None:
            raise ValueError(f"Missing LastMile real anchor for {row['item_id']}")
        if coverage == "public-media" and not public_real(real):
            continue
        key = (row["condition"], row["source_key"])
        grouped[key].append(
            pair_record(
                row["item_id"],
                real["item_id"],
                row["source_key"],
                condition=row["condition"],
                benchmark_role=role,
            )
        )
        roles[key] = role
    return dict(grouped), roles


def required_ids(groups: Iterable[list[dict[str, str]]]) -> set[str]:
    result: set[str] = set()
    for pairs in groups:
        for pair in pairs:
            result.add(pair["generated_id"])
            result.add(pair["real_id"])
    return result


def resolve_metric_modes(
    predictions: dict[str, dict[str, Any]], expected_ids: set[str], requested: str
) -> tuple[bool, bool]:
    score_ids = {item_id for item_id in expected_ids if "fake_score" in predictions.get(item_id, {})}
    decision_ids = {
        item_id for item_id in expected_ids if "prediction" in predictions.get(item_id, {})
    }

    require_continuous = requested in {"continuous", "both"}
    require_discrete = requested in {"discrete", "both"}
    if requested == "auto":
        require_continuous = bool(score_ids)
        require_discrete = bool(decision_ids)
        if not require_continuous and not require_discrete:
            raise ValueError(
                "No complete prediction output found; provide fake_score, prediction, or both."
            )

    for enabled, field, present in (
        (require_continuous, "fake_score", score_ids),
        (require_discrete, "prediction", decision_ids),
    ):
        if not enabled:
            continue
        missing = sorted(expected_ids - present)
        if missing:
            preview = ", ".join(missing[:5])
            raise ValueError(
                f"Missing {field} for {len(missing)} required items; first IDs: {preview}"
            )
    return require_continuous, require_discrete


def tpr_at_fpr(labels: np.ndarray, scores: np.ndarray, max_fpr: float = 0.05) -> float:
    fpr, tpr, _ = roc_curve(
        labels, scores, pos_label=1, drop_intermediate=False
    )
    eligible = tpr[fpr <= max_fpr + 1e-12]
    return float(np.max(eligible)) if eligible.size else 0.0


def safe_f1(tp: int, fp: int, fn: int) -> float:
    denominator = 2 * tp + fp + fn
    return (2 * tp / denominator) if denominator else 0.0


def evaluate_pairs(
    pairs: list[dict[str, str]],
    predictions: dict[str, dict[str, Any]],
    continuous: bool,
    discrete: bool,
) -> dict[str, float | int]:
    if not pairs:
        raise ValueError("Cannot evaluate an empty pair group.")
    result: dict[str, float | int] = {"pair_count": len(pairs)}

    if continuous:
        real_scores = np.asarray(
            [predictions[pair["real_id"]]["fake_score"] for pair in pairs],
            dtype=float,
        )
        generated_scores = np.asarray(
            [predictions[pair["generated_id"]]["fake_score"] for pair in pairs],
            dtype=float,
        )
        labels = np.concatenate(
            [np.zeros(len(pairs), dtype=int), np.ones(len(pairs), dtype=int)]
        )
        scores = np.concatenate([real_scores, generated_scores])
        result["auc"] = round(100.0 * float(roc_auc_score(labels, scores)), 6)
        result["tpr_at_5fpr"] = round(
            100.0 * tpr_at_fpr(labels, scores, max_fpr=0.05), 6
        )

    if discrete:
        generated_pred = np.asarray(
            [
                predictions[pair["generated_id"]]["prediction"] == "generated"
                for pair in pairs
            ],
            dtype=bool,
        )
        real_pred = np.asarray(
            [
                predictions[pair["real_id"]]["prediction"] == "generated"
                for pair in pairs
            ],
            dtype=bool,
        )
        tp = int(generated_pred.sum())
        fn = len(pairs) - tp
        fp = int(real_pred.sum())
        tn = len(pairs) - fp
        fake_recall = tp / len(pairs)
        real_recall = tn / len(pairs)
        macro_f1 = (safe_f1(tp, fp, fn) + safe_f1(tn, fn, fp)) / 2.0
        result["bacc"] = round(100.0 * (fake_recall + real_recall) / 2.0, 6)
        result["macro_f1"] = round(100.0 * macro_f1, 6)
        result["fake_recall"] = round(100.0 * fake_recall, 6)
    return result


def metric_mean(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    if not rows:
        return {"source_count": 0, "pair_count": 0}
    keys = sorted(set.intersection(*(set(row) for row in rows)) - {"pair_count"})
    result: dict[str, float | int] = {
        "source_count": len(rows),
        "pair_count": sum(int(row["pair_count"]) for row in rows),
    }
    for key in keys:
        values = [float(row[key]) for row in rows]
        result[key] = round(float(np.mean(values)), 6)
    return result


def evaluate_main_or_humanproof(
    track: str,
    groups: dict[str, list[dict[str, str]]],
    predictions: dict[str, dict[str, Any]],
    continuous: bool,
    discrete: bool,
) -> dict[str, Any]:
    by_source = []
    for source_key, pairs in groups.items():
        by_source.append(
            {
                "source_key": source_key,
                **evaluate_pairs(pairs, predictions, continuous, discrete),
            }
        )
    source_metrics = [
        {key: value for key, value in row.items() if key != "source_key"}
        for row in by_source
    ]
    result: dict[str, Any] = {
        "by_source": by_source,
        "source_equal_mean": metric_mean(source_metrics),
    }
    if track == "humanproof":
        pooled_pairs = [pair for pairs in groups.values() for pair in pairs]
        result["pooled"] = evaluate_pairs(
            pooled_pairs, predictions, continuous, discrete
        )
    return result


def evaluate_lastmile(
    groups: dict[tuple[str, str], list[dict[str, str]]],
    roles: dict[tuple[str, str], str],
    predictions: dict[str, dict[str, Any]],
    continuous: bool,
    discrete: bool,
) -> dict[str, Any]:
    conditions: dict[str, Any] = {}
    for condition in sorted({key[0] for key in groups}):
        by_source = []
        for key in sorted(key for key in groups if key[0] == condition):
            source_key = key[1]
            by_source.append(
                {
                    "source_key": source_key,
                    "benchmark_role": roles[key],
                    **evaluate_pairs(
                        groups[key], predictions, continuous, discrete
                    ),
                }
            )
        benchmark_rows = [
            {
                key: value
                for key, value in row.items()
                if key not in {"source_key", "benchmark_role"}
            }
            for row in by_source
            if row["benchmark_role"] == "RA-Bench"
        ]
        conditions[condition] = {
            "by_source": by_source,
            "source_equal_mean": metric_mean(benchmark_rows),
        }

    condition_means = [value["source_equal_mean"] for value in conditions.values()]
    metric_keys = sorted(
        set.intersection(*(set(row) for row in condition_means))
        - {"source_count", "pair_count"}
    )
    overall = {"condition_count": len(condition_means)}
    for key in metric_keys:
        overall[key] = round(
            float(np.mean([float(row[key]) for row in condition_means])), 6
        )
    return {"conditions": conditions, "condition_equal_mean": overall}


def main() -> None:
    args = parse_args()
    predictions = read_predictions(args.predictions)

    if args.track == "main":
        groups = main_pairs(args.metadata_dir, args.coverage)
        group_lists = list(groups.values())
        roles = None
    elif args.track == "humanproof":
        groups = humanproof_pairs(args.metadata_dir, args.coverage)
        group_lists = list(groups.values())
        roles = None
    else:
        groups, roles = lastmile_pairs(
            args.metadata_dir,
            args.coverage,
            args.include_auxiliary_control,
        )
        group_lists = list(groups.values())

    expected = required_ids(group_lists)
    continuous, discrete = resolve_metric_modes(
        predictions, expected, args.metrics
    )

    if args.track in {"main", "humanproof"}:
        metrics = evaluate_main_or_humanproof(
            args.track,
            groups,
            predictions,
            continuous,
            discrete,
        )
    else:
        assert roles is not None
        metrics = evaluate_lastmile(
            groups,
            roles,
            predictions,
            continuous,
            discrete,
        )

    result = {
        "schema_version": "ra-bench-evaluation-v1",
        "track": args.track,
        "coverage": args.coverage,
        "units": "percent",
        "continuous_metrics": continuous,
        "discrete_metrics": discrete,
        "required_prediction_items": len(expected),
        "provided_prediction_items": len(predictions),
        "ignored_prediction_items": len(set(predictions) - expected),
        "include_auxiliary_control": bool(args.include_auxiliary_control),
        "metrics": metrics,
    }
    rendered = json.dumps(result, indent=2, ensure_ascii=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
