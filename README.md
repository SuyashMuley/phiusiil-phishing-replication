# Replicating and critiquing PhiUSIIL phishing URL detection under dataset shift

Course project (Replication and Critique track). Primary paper: Prasad and Chandra,
*PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and
incremental learning*, Computers & Security 136 (2024), [doi:10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545).

The repository holds the code, result tables, notes and the draft report. It is work in progress; the final report is
due 2026-12-08. The current draft is [`report/report.pdf`](report/report.pdf).

## What was found

1. **The published result reproduces.** With the paper's predict-then-`partial_fit` protocol, BestSecurity accuracy is
   0.9915 (mean of four shuffled row orders) and 0.9934 in file order, against 0.9924 published. Tables 3, 5, 6 and 7 are
   reproduced to within about 0.001 accuracy.
2. **The URL similarity index is a construction shortcut, not label leakage.** The paper matches each URL against the
   Open PageRank top-10M list and draws the legitimate class from that same list, so listed legitimate URLs score 100
   without any labels. The index is also not needed: URL form (every legitimate URL is a bare `https://www.` homepage) and
   page-content artifacts separate the classes without it. Removing it changes BestSecurity accuracy by 0.0001, and URL-only
   columns still give 0.987 in the paper's protocol.
3. **URL-only models do not keep their operating point on other sources.** Three sources (PhiUSIIL, GramBeddings,
   PhreshPhish) are compared with matched pool size and class mix, registered-domain-disjoint splits and a threshold fixed at
   95% recall on source validation data. In-source recall holds (0.93-0.98 for all five models); on another source, HistGB
   recall ranges from 0.52 to 0.98 and false-positive rate from 0.00 to 1.00, in opposite directions for different pairs
   (PhiUSIIL-trained models flag most URLs elsewhere; GramBeddings-trained models miss about half of PhiUSIIL phishing).
   An oracle threshold chosen on the target would not repair most pairs. Pair-level AUROC varies widely by model, so the
   recall/FPR pattern is the result to rely on.
4. **Pooling two sources at the same total size does not give a transferable operating point either.** Leave-one-source-out
   training (half of the pool from each of two sources, threshold fixed on the pooled validation data) never did worse on
   false-positive rate than the worse single source, beat both single sources on AUROC in 15 of 30 model and feature-set
   cells (never with PhiUSIIL held out), and mostly moved the recall/FPR trade-off instead of improving the ranking.
5. **The sources differ in ways that more data from the same source is unlikely to fix.** A classifier recovers the source
   from the URL alone within a class (AUROC 0.85-1.00; 0.71 for PhreshPhish against PhishTank phishing), and normalizing URL
   formatting (no scheme, `www`, case or trailing slash) does not improve transfer. The claim about sample size is an
   argument from these measurements; the full 800,000-row GramBeddings featurization was not run.

Details, tables, caveats and open items are in [`plan.md`](plan.md); the chronological record is in
[`MD/project_log.md`](MD/project_log.md); the checkpoint report is in [`checkpoint/`](checkpoint/).

## Layout

| Path | Contents |
|---|---|
| `scripts/` | Experiment scripts (see below) and `common.py` (loaders, 22-feature URL extractor, matched sampling, domain-disjoint splits, validation-fixed thresholds) |
| `results/` | Result CSVs, figures and run logs (`results/logs/`) |
| `report/` | Report draft: `report.tex`, `report.pdf`, `outline.md`, generated `tables/` |
| `plan.md` | Progress tracker with all result tables |
| `MD/` | Project log, verified literature table, and two unverified plans written by other LLMs (`MD/llm_plans/`) |
| `proposal/`, `checkpoint/` | LaTeX source and PDF of the proposal and the checkpoint report |
| `data/` | Not in the repository (see below) |

## Setup

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Results were produced with Python 3.14 on an Apple M4 (10 cores, 24 GB, CPU only). The longest run (paper Table 7) takes
about 20 minutes; the five-seed transfer run takes about 13 minutes; most others take seconds to a few minutes. The report
is compiled with [tectonic](https://tectonic-typesetting.github.io/) (`cd report && tectonic report.tex`).

## Data (not included)

Place the files at these paths relative to the repository root.

| Path | Source |
|---|---|
| `data/PhiUSIIL_Phishing_URL_Dataset.csv` | [UCI #967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) (also on Mendeley Data, CC BY 4.0) |
| `data/grambeddings/grambeddings_dataset_main/{train,test}.csv` | [GramBeddings dataset](https://web.cs.hacettepe.edu.tr/~selman/grambeddings-dataset/) (the archive is a password-protected RAR; the password and extraction notes are in `MD/project_log.md`, sections 2 and 7) |
| `data/external/phishtank_online_valid.csv` | [PhishTank](https://phishtank.org/developer_info.php) `online-valid.csv`. The experiments used the snapshot of 2026-10-01 (76,451 URLs); a fresh download will differ. |
| `data/external/top-1m.csv` | [Tranco list](https://tranco-list.eu/) top 1M (`rank,domain`) |
| `data/phreshphish/phreshphish_url_label_date.csv` | Created by `scripts/10_pull_phreshphish.py` from the Hugging Face dataset [`phreshphish/phreshphish`](https://huggingface.co/datasets/phreshphish/phreshphish) ([arXiv:2507.10854](https://arxiv.org/abs/2507.10854)). It reads only the url, label and date columns (about 0.1-0.4 MB per shard, not the page HTML). |

`data/CIC_Trap4phish/` and `data/external/openphish_feed.txt` were looked at but are not used by the reported results.
Check each dataset's license before redistributing it. Feature caches are written to `data/cache/` by scripts 03, 11 and 14.

## Running the experiments

Run everything from the repository root.

**First pass and Part A (paper reproduction)**

```
.venv/bin/python scripts/02_dataset_summary.py          # sizes, duplicates, URL and domain overlap
.venv/bin/python scripts/03_cross_dataset.py            # first-pass transfer; also builds data/cache/*.pkl (needed by 07)
.venv/bin/python scripts/04_shift_and_reverse.py        # first-pass feature shift and reverse direction
.venv/bin/python scripts/05_reproduce_phiusiil.py       # Tables 5 and 6 (add --order shuffle --seed N, --drop usi,page, --table7 sequential|random)
.venv/bin/python scripts/06_shortcut_ablation.py        # is the similarity index leakage or a shortcut?
.venv/bin/python scripts/09_table3_baselines.py --seed 0   # one process per seed, then add --summarize (needs results/repro_features_file_s0.csv from script 05)
```

**Part B (URL-only transfer) and the third source**

```
.venv/bin/python scripts/10_pull_phreshphish.py         # url/label/date of all PhreshPhish shards (needs pyarrow)
.venv/bin/python scripts/11_build_phreshphish_cache.py  # balanced 100k sample with the 22 features -> data/cache/phreshphish.pkl
nice .venv/bin/python scripts/07_transfer_matched.py --seeds 0,1,2,3,4 --out results/transfer_runs_v2.csv   # about 13 min
.venv/bin/python scripts/08_summarize_transfer.py results/transfer_runs_v2.csv results/transfer_summary_v2.csv
```

Script 07's default output is `results/transfer_runs.csv`, which holds the earlier three-source run; pass `--out` to keep
both. The three older sources reproduce that file exactly in the v2 run.

**Combined-source (diversity) experiment**

```
nice .venv/bin/python scripts/21_combined_sources.py --seeds 0,1,2,3,4   # about 4.5 min -> results/combined_runs.csv
.venv/bin/python scripts/22_summarize_combined.py       # results/combined_vs_single.csv, combined_in_source.csv
```

**Why the sources differ (A1-A5)**

```
.venv/bin/python scripts/12_source_profile.py           # URL form by source, class and URL type -> results/source_profile.csv
.venv/bin/python scripts/13_source_discriminator.py     # can a model tell the source from the URL? -> results/source_discriminator.csv
.venv/bin/python scripts/14_build_canonical_cache.py    # canonical-URL feature caches (data/cache/*_canon.pkl)
nice .venv/bin/python scripts/07_transfer_matched.py --canonical --seeds 0,1,2,3,4   # about 5 min -> results/transfer_runs_canon.csv
.venv/bin/python scripts/07_transfer_matched.py --seeds 0 --models LR,HistGB --featsets all --save-scores results/scores_seed0.npz --out results/transfer_runs_scores_seed0.csv
.venv/bin/python scripts/15_plot_scores.py              # score distributions -> results/fig_scores_*.png
```

**Final tables, figures and report**

```
.venv/bin/python scripts/16_final_tables_figures.py     # results/final_tables.md, final_table_*.csv, fig_operating_points.png, fig_canonical_vs_raw.png
.venv/bin/python scripts/17_final_table_partA.py        # results/final_partA_tables.md and CSVs (cross-checks the existing summaries)
.venv/bin/python scripts/19_report_figures.py           # 2x2 operating-point figure used in the report
.venv/bin/python scripts/18_make_latex_tables.py        # report/tables/*.tex from the result files
cd report && tectonic report.tex
```

Scripts 01-04 are the first pass from before the proposal feedback (single seed, untuned) and are kept for the record;
scripts 05-22 are the experiments that the checkpoint and the report use.

## Deviations from the paper

LightGBM, XGBoost and CatBoost are not installed, so scikit-learn gradient boosting and extra trees stand in for the
paper's feature-importance ensemble and HistGradientBoosting stands in for its boosting rows; the Voting and Stacking
baselines are not run. The paper does not state its row order, split for Table 3, final feature count, or the pre-training
split, so the choices made here are documented in `plan.md`.

## Known gaps

The Part B pools are small (11,666 rows per variant) and domain-disjoint splits are uneven because a few hosting domains
are large, so single-seed numbers are noisy and five-seed means are reported. GramBeddings and PhreshPhish are used as
100,000-row balanced samples. The provenance of GramBeddings (phishing source, crawler seeds) is not documented on its
pages. Some related-work numbers in the report are quoted at abstract level (see `MD/sota_verified_table.md`).
