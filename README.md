# Replicating and critiquing PhiUSIIL phishing URL detection under dataset shift

Course project (Replication and Critique track). Primary paper: Prasad and Chandra,
*PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and
incremental learning*, Computers & Security 136 (2024), [doi:10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545).

The repository holds the code, result tables and notes for a checkpoint-stage study. It is work in progress; the
final report is due 2026-12-08.

## What was found so far

1. **The published result reproduces.** With the paper's predict-then-`partial_fit` protocol, BestSecurity accuracy is
   0.9915 (mean of four shuffled row orders) and 0.9934 in file order, against 0.9924 published.
2. **The URL similarity index is a construction shortcut, not label leakage.** The paper matches each URL against the
   Open PageRank top-10M list and draws the legitimate class from that same list, so listed legitimate URLs score 100
   without any labels. The index is also not needed: URL form (every legitimate URL is a bare `https://www.` homepage) and
   page-content artifacts separate the classes without it, and 21 URL-only columns still give 0.987 accuracy in the
   paper's protocol.
3. **URL-only models do not transfer.** Models with AUROC about 1.00 on PhiUSIIL reach 0.61-0.78 on GramBeddings, and a
   95%-recall threshold chosen on source validation data fails in both directions (flags most legitimate URLs one way,
   misses about half the phishing the other way).

Details, tables, caveats and the open items are in [`plan.md`](plan.md); the chronological record is in
[`MD/project_log.md`](MD/project_log.md); the checkpoint report is in [`checkpoint/`](checkpoint/).

## Layout

| Path | Contents |
|---|---|
| `scripts/` | Experiment scripts (see below) and `common.py` (loaders, 22-feature URL extractor, matched sampling, domain-disjoint splits, validation-fixed thresholds) |
| `results/` | Result CSVs and run logs (`results/logs/`) |
| `plan.md` | Progress tracker with all result tables |
| `MD/` | Project log, verified literature table, and two unverified plans written by other LLMs (`MD/llm_plans/`) |
| `proposal/`, `checkpoint/` | LaTeX source and PDF of the proposal and the checkpoint report |
| `data/` | Not in the repository (see below) |

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Results were produced with Python 3.14 on an Apple M4 (10 cores, 24 GB). The longest run (paper Table 7) takes about
20 minutes; most others take seconds to a few minutes.

## Data (not included)

Place the files at these paths relative to the repository root.

| Path | Source |
|---|---|
| `data/PhiUSIIL_Phishing_URL_Dataset.csv` | [UCI #967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) (also on Mendeley Data, CC BY 4.0) |
| `data/grambeddings/grambeddings_dataset_main/{train,test}.csv` | [GramBeddings dataset](https://web.cs.hacettepe.edu.tr/~selman/grambeddings-dataset/) (the archive is a password-protected RAR; the password and extraction notes are in `MD/project_log.md`, sections 2 and 7) |
| `data/external/phishtank_online_valid.csv` | [PhishTank](https://phishtank.org/developer_info.php) `online-valid.csv`. The experiments used the snapshot of 2026-10-01 (76,451 URLs); a fresh download will differ. |
| `data/external/top-1m.csv` | [Tranco list](https://tranco-list.eu/) top 1M (`rank,domain`) |

`data/CIC_Trap4phish/` and `data/external/openphish_feed.txt` were looked at but are not used by the reported results.
Check each dataset's license before redistributing it.

## Running the experiments

Run everything from the repository root.

```
.venv/bin/python scripts/02_dataset_summary.py          # sizes, duplicates, URL and domain overlap
.venv/bin/python scripts/03_cross_dataset.py            # first-pass transfer; also builds data/cache/*.pkl (needed by 07)
.venv/bin/python scripts/04_shift_and_reverse.py        # first-pass feature shift and reverse direction
.venv/bin/python scripts/05_reproduce_phiusiil.py       # Tables 5 and 6 (add --order shuffle --seed N, --drop usi,page, --table7 sequential|random)
.venv/bin/python scripts/06_shortcut_ablation.py        # is the similarity index leakage or a shortcut?
nice .venv/bin/python scripts/07_transfer_matched.py --seeds 0,1,2,3,4   # Part B transfer, about 5 min
.venv/bin/python scripts/08_summarize_transfer.py       # mean and std over seeds
.venv/bin/python scripts/09_table3_baselines.py --seed 0   # one process per seed, then add --summarize (needs results/repro_features_file_s0.csv from script 05)
```

Scripts 01-04 are the first pass from before the proposal feedback (single seed, untuned) and are kept for the record;
scripts 05-09 are the checkpoint experiments and supersede them.

## Deviations from the paper

LightGBM, XGBoost and CatBoost are not installed, so scikit-learn gradient boosting and extra trees stand in for the
paper's feature-importance ensemble and HistGradientBoosting stands in for its boosting rows; the Voting and Stacking
baselines are not run. The paper does not state its row order, split for Table 3, final feature count, or the pre-training
split, so the choices made here are documented in `plan.md`.
