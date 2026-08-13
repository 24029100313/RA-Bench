# RA-Bench Dataset

This repository contains the public metadata and download utilities for RA-Bench. Dataset media are hosted in the [RA-Bench Hugging Face dataset repository](https://huggingface.co/datasets/liangshuo0111/RA-Bench); video files are not duplicated in GitHub.

## Dataset Contents

| Component | Definition |
| --- | --- |
| RA-Bench | 17,886 entries: 1,830 real-video anchors and 16,056 generated clips from four open-source and five closed-source generators. Of the real anchors, 1,319 are released as media and 511 are represented by source URLs according to the record-level rights review. |
| RA-Bench-HumanProof | 633 generated clips judged `Real` by all five assigned reviewers. This subset reuses media under `media/main/`; it is defined by `metadata/ra_bench_humanproof.*` and therefore has no duplicate media directory. |
| RA-Bench-LastMile | 9,900 evaluation entries covering sequential dissemination conditions T0-T5. Its manifest may reference both `media/main/` and `media/lastmile/`. |

The Hugging Face release contains 25,575 public media files totaling 93,772,561,883 bytes, plus the eight metadata files mirrored here. URL-only real anchors are not redistributed as media.

## Metadata

- `metadata/ra_bench_main.csv` and `.jsonl`: main benchmark manifest.
- `metadata/ra_bench_humanproof.csv` and `.jsonl`: HumanProof subset definition and anonymized review outcomes.
- `metadata/ra_bench_lastmile.csv` and `.jsonl`: dissemination evaluation manifest.
- `metadata/real_rights_release.csv`: record-level release mode, source URL, rights basis, and attribution fields for real anchors.
- `metadata/release_inventory.json`: release counts and exclusions.

Paths in the manifests are relative to the root of the Hugging Face dataset repository. Records with `release_mode=url_only` provide a source URL instead of redistributed media.

## Download

Install the Hugging Face Hub client:

```bash
python -m pip install -U huggingface_hub
```

Download the complete release:

```bash
python scripts/download_dataset.py --output RA-Bench
```

If the Hugging Face repository is private or gated during pre-release, authenticate first with `hf auth login` or provide `HF_TOKEN` through the process environment. The token is never stored by the download script. Re-running the command resumes from the local Hugging Face cache.

Verify the downloaded release:

```bash
python scripts/verify_dataset.py RA-Bench
```

## Rights

Release mode and rights information for each real anchor are recorded in `metadata/real_rights_release.csv`. Source URLs and required attribution must be preserved. The absence of a media file for a URL-only record is intentional.

