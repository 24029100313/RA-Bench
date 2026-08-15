# RA-Bench Evaluation Protocol

This document defines the public evaluation contract for RA-Bench, RA-Bench-HumanProof, and RA-Bench-LastMile. The reference evaluator is `scripts/evaluate_predictions.py`.

## 1. Prediction Contract

Prediction files may be CSV or JSONL. Every row must contain:

- `item_id`: the exact item identifier from the relevant manifest.
- `fake_score` (optional): a finite continuous score for which larger values indicate stronger evidence that the video is generated.
- `prediction` (optional): `real` or `generated`.

At least one prediction output must be supplied. If an output column is present, it must be complete for every item required by the selected track and coverage mode. Duplicate `item_id` values are rejected.

Canonical example:

```csv
item_id,fake_score,prediction
real::L1-01_L2-01a_0003__scene_003,0.013,real
wan22_dynamic_seed0::L1-01_L2-01a_0003__scene_003,0.891,generated
```

For RA-Bench-LastMile, use the condition-prefixed IDs in `ra_bench_lastmile.csv`, such as `T3::real::<norm_clip_id>` and `T3::<source_key>::<norm_clip_id>`.

## 2. Metrics

We treat real videos as class 0 and generated videos as class 1.

### Continuous outputs

- **AUC**: area under the ROC curve.
- **TPR@5%FPR**: the maximum true-positive rate among ROC operating points whose false-positive rate is at most 5%. No interpolation or source-specific score inversion is applied.

### Discrete outputs

- **BAcc**: the mean of generated-video recall and real-video recall.
- **Macro-F1**: the unweighted mean of the class-wise F1 scores for the real and generated classes.
- **FakeR**: generated-video recall, i.e., the fraction of generated videos predicted as `generated`.

All reported values are percentages in `[0, 100]`.

## 3. Pairing and Aggregation

### RA-Bench

For each generation source, every generated clip is paired with the real anchor sharing its `norm_clip_id`. Metrics are computed on that source's generated clips and their matched real anchors. The RA-Bench result is the arithmetic mean of the nine source-level metrics.

This source-equal aggregation is important: closed-source providers returned different numbers of clips, so pooling all videos would give sources with more returned samples greater weight.

| Coverage | Pair comparisons across nine sources |
| --- | ---: |
| `full` | 16,056 |
| `public-media` | 11,579 |

### RA-Bench-HumanProof

Each of the 633 generated videos is evaluated with its matched real anchor. If multiple generated videos share one real anchor, that real prediction is reused for each corresponding pair, matching the pair-level evaluation in the paper.

The evaluator reports pooled HumanProof metrics, source-specific metrics, and an equal-source diagnostic mean. The pooled result is the primary HumanProof result.

| Coverage | Matched pairs |
| --- | ---: |
| `full` | 633 |
| `public-media` | 430 |

### RA-Bench-LastMile

RA-Bench-LastMile contains 150 real anchors and their matched videos from all nine RA-Bench generation sources under six conditions:

| Manifest condition | Operation |
| --- | --- |
| `T0` | Original standardized clips. |
| `T1` | VP9 encoding followed by H.264 transcoding. |
| `T2` | 0.5x spatial downsampling plus T1. |
| `T3` | Conversion to 8 fps plus T1. |
| `T4` | AP-style news badge plus T1. |
| `T5` | Full chain combining spatial downsampling, 8-fps conversion, the news badge, and T1. |

Metrics are computed separately for each condition and source, then averaged equally over the nine RA-Bench sources. The fixed-duration Wan2.2 rows have `benchmark_role=auxiliary_control`; they are excluded from benchmark averages. Pass `--include-auxiliary-control` to report them separately.

| Coverage | Pair comparisons per condition |
| --- | ---: |
| `full` | 1,350 |
| `public-media` | 990 |

## 4. Coverage Modes

### Public-media evaluation

`--coverage public-media` uses only pairs whose real anchor is redistributed in the Hugging Face release. This mode is fully reproducible from the public media files and is the recommended starting point for external users.

### Full paper protocol

`--coverage full` follows every row in the released manifests. It requires predictions for the 511 real anchors represented by source URLs rather than redistributed media. This mode is intended for users who already have lawful access to those source clips. The evaluator does not silently substitute, drop, or reconstruct missing videos.

Results from the two coverage modes should be labeled explicitly and should not be compared as if they used the same sample set.

## 5. Commands

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Evaluate continuous predictions, discrete decisions, or both:

```bash
python scripts/evaluate_predictions.py \
  --track main \
  --coverage public-media \
  --predictions predictions.csv \
  --metrics auto \
  --output metrics.json
```

`--metrics auto` evaluates every output type that is present and complete. Use `continuous`, `discrete`, or `both` to require a specific output contract.

The output JSON records the selected protocol, prediction coverage, source-level metrics, and the appropriate benchmark summary. Extra prediction IDs are counted but ignored; missing required predictions cause evaluation to stop with an error.

