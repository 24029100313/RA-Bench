<p align="center">
  <img src="assets/ra-bench-cover.png" width="100%" alt="RA-Bench: Can we defend against generated crisis videos?">
</p>

<h1 align="center">RA-Bench</h1>

<p align="center">
  <strong>A benchmark for AI-generated video detection that uses Real videos as Anchors</strong>
</p>

<p align="center">
  <a href="https://ra-bench-crisis-video.yxgma811120.chatgpt.site/">Project Page</a> |
  <a href="https://ra-bench-crisis-video.yxgma811120.chatgpt.site/ra-bench-paper.pdf">Paper</a> |
  <a href="https://huggingface.co/datasets/liangshuo0111/RA-Bench">Dataset</a> |
  <a href="#evaluation">Evaluation</a>
</p>

<p align="center">
  <a href="https://huggingface.co/papers/2608.14391">
    <img src="https://img.shields.io/badge/Hugging%20Face%20Daily%20Papers-%231-FFD21E?logo=huggingface&logoColor=000" alt="Hugging Face Daily Papers #1">
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/videos-17%2C886-0B315A" alt="17,886 videos">
  <img src="https://img.shields.io/badge/generators-9-E64A19" alt="9 generators">
  <img src="https://img.shields.io/badge/crisis_categories-10-147D78" alt="10 crisis categories">
  <img src="https://img.shields.io/badge/media-93.8_GB-555555" alt="93.8 GB public media">
</p>

RA-Bench evaluates whether current detectors can identify realistic generated videos anchored in real footage of crisis events. It pairs real videos with outputs from four open-source and five closed-source generators, then extends the evaluation to videos that mislead human reviewers and to videos processed through a sequential dissemination pipeline.

## At a Glance

| | RA-Bench |
| --- | ---: |
| Total videos | **17,886** |
| Real-video anchors | **1,830** |
| Generated videos | **16,056** |
| Generation sources | **9** |
| Social-risk categories / subcategories | **10 / 44** |
| Human-deceptive generated videos | **633** |

## Benchmark Tracks

| Track | Purpose | Public definition |
| --- | --- | --- |
| **RA-Bench** | Source-generalization benchmark with matched real-generated pairs. | `metadata/ra_bench_main.*` |
| **RA-Bench-HumanProof** | 633 generated videos judged `Real` by all five assigned reviewers. Media are reused from RA-Bench. | `metadata/ra_bench_humanproof.*` |
| **RA-Bench-LastMile** | Detector robustness under six sequential dissemination conditions, from the standardized video to the full processing chain. | `metadata/ra_bench_lastmile.*` |

The Hugging Face release contains 25,575 public media files totaling 93,772,561,883 bytes. Of the 1,830 real anchors, 1,319 are redistributed as media and 511 are represented by source URLs after record-level rights review. Generated media are released in full.

## Quick Start

```bash
git clone https://github.com/24029100313/RA-Bench.git
cd RA-Bench
python -m pip install -r requirements.txt
```

Download the complete media release from Hugging Face:

```bash
python scripts/download_dataset.py --output RA-Bench
python scripts/verify_dataset.py RA-Bench
```

Re-running the download command resumes from the local Hugging Face cache.

## Evaluation

RA-Bench uses **source-matched evaluation**. Each generated source is evaluated against the real anchors from which its videos were generated. Metrics are first computed separately for each of the nine generation sources; the benchmark-level result is their arithmetic mean, so sources contribute equally regardless of clip count.

| Detector output | Reported metrics |
| --- | --- |
| Continuous fake score | AUC and TPR@5%FPR |
| Discrete real/generated decision | BAcc, Macro-F1, and FakeR |

Predictions are supplied as CSV or JSONL with one row per evaluated item:

```csv
item_id,fake_score,prediction
real::L1-01_L2-01a_0003__scene_003,0.013,real
wan22_dynamic_seed0::L1-01_L2-01a_0003__scene_003,0.891,generated
```

`fake_score` must increase with evidence for the generated class. `prediction` must be `real` or `generated`. A file may contain either output or both.

Evaluate the three tracks:

```bash
# Main benchmark
python scripts/evaluate_predictions.py \
  --track main \
  --coverage public-media \
  --predictions predictions_main.csv \
  --output results_main.json

# Human-deceptive subset
python scripts/evaluate_predictions.py \
  --track humanproof \
  --coverage public-media \
  --predictions predictions_humanproof.csv \
  --output results_humanproof.json

# Sequential dissemination conditions
python scripts/evaluate_predictions.py \
  --track lastmile \
  --coverage public-media \
  --predictions predictions_lastmile.csv \
  --output results_lastmile.json
```

Two coverage modes are explicit:

- `public-media` evaluates only matched pairs whose real anchor is redistributed. It runs entirely from the public media release.
- `full` follows the complete paper manifest and requires predictions for URL-only real anchors as well. Use it only when those source videos are available to you under their original terms.

The evaluator rejects duplicate IDs and incomplete prediction files, fixes `real=0` and `generated=1`, does not invert scores for individual sources, and excludes the fixed-duration Wan2.2 auxiliary control from RA-Bench averages. See [EVALUATION.md](EVALUATION.md) for exact pairing rules, coverage counts, LastMile condition definitions, and metric details.

## Repository Layout

```text
RA-Bench/
|-- assets/
|-- metadata/
|   |-- ra_bench_main.csv
|   |-- ra_bench_humanproof.csv
|   |-- ra_bench_lastmile.csv
|   |-- real_rights_release.csv
|   `-- release_inventory.json
|-- scripts/
|   |-- download_dataset.py
|   |-- evaluate_predictions.py
|   `-- verify_dataset.py
|-- EVALUATION.md
`-- README.md
```

CSV and JSONL versions of each benchmark manifest are provided. Media paths are relative to the root of the Hugging Face dataset repository.

## Rights and Responsible Use

Release mode, source URL, rights basis, and attribution requirements for every real anchor are recorded in `metadata/real_rights_release.csv`. URL-only records are intentionally not redistributed. Users must preserve source attribution and comply with the terms attached to each source.

RA-Bench contains crisis-related material. It is released for research on detection, provenance, robustness, and responsible media analysis, not for creating or distributing deceptive content.

## Citation

The BibTeX entry will be added with the public paper release. Until then, please cite the paper title and link to this repository and the [project page](https://ra-bench-crisis-video.yxgma811120.chatgpt.site/).

