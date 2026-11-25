# Project log: phishing URL classifier generalization

Date of work: 2026-10-01. Project folder: `/Users/suyashmuley/Desktop/ML/Project`.

## 1. Where the project stands

- Professor's reply: the first step is to have an LLM reason through the problem and establish the SOTA (independent of the PhiUSIIL paper) as a reference top-baseline.
- **SOTA step: done.** Result is in `sota_verified_table.md` (some claims unverified, see section 3). A draft email to the professor was written (section 7).
- **Experiments: run early, set aside for now.** Section 5 records them so nothing is lost. The user chose to focus on the professor's reply only.
- Not done: SVM and MLP, XGBoost (needs `libomp`), a character n-gram baseline, multi-source training, the temporal test, an LLM zero-shot baseline.

## 2. Files and folders

| Path | What it is |
|---|---|
| `MD/llm_plans/sota_plan_phishing_url.md`, `MD/llm_plans/phishing_cross_dataset_feasibility_plan.md` | Two plans written by other LLMs (inputs, not verified; moved here from the project root on 2026-11-01) |
| `MD/sota_verified_table.md` | Verified SOTA table, written by a research subagent (moved here from the project root) |
| `proposal/proposal.tex`, `proposal/proposal.pdf` | One-page project proposal (Replication and Critique track) |
| `MD/project_log.md` | This file |
| `data/PhiUSIIL_Phishing_URL_Dataset.csv` | PhiUSIIL (UCI #967), 235,795 rows |
| `data/grambeddings/grambeddings_dataset_main/` | GramBeddings `train.csv`, `test.csv`, `classes.txt` (RAR password: `grambeddings`) |
| `data/external/` | `phishtank_online_valid.csv`, `openphish_feed.txt`, `top-1m.csv` (Tranco) |
| `data/CIC_Trap4phish/` | CIC Trap4Phish "Final CSV" folder: attachment features, no URLs |
| `data/cache/` | Cached feature tables written by script 03 |
| `scripts/01_leakage_and_repro.py` | Leakage check and reproduction |
| `scripts/02_dataset_summary.py` | Counts, duplicates, overlap |
| `scripts/common.py` | Loaders, URL-only feature extractor (22 features), `metrics` |
| `scripts/03_cross_dataset.py` | Train on PhiUSIIL, test in-distribution and cross-source |
| `scripts/04_shift_and_reverse.py` | Feature shift analysis and both training directions |
| `results/*.csv` | `cross_dataset_results.csv`, `feature_means.csv`, `feature_ks.csv`, `reverse_directions.csv` |
| `.venv/` | Python 3.14 environment (pandas, scikit-learn, xgboost, tldextract) |

Run scripts from the project folder with `.venv/bin/python scripts/<name>.py`.

## 3. SOTA step (professor's reply)

Reference baseline for URL-only models:

| Setting | Result | Source |
|---|---|---|
| In-distribution (PhiUSIIL) | 99.6-99.8% accuracy (LR, XGBoost, CharCNN, BERT-base) | Ahamed et al. 2026, Frontiers in Comput. Sci. (abstract verified) |
| PhiUSIIL, 2 features only | 99.63% accuracy; single AND rule 99.67% | Rahman et al. 2026, G-Tech (full text read) |
| Cross-source (PhishTank phish + Majestic benign) | 0.73-0.87 accuracy, FPR 0.25-0.54 (LR 0.87/0.25, XGB 0.73/0.54, BERT 0.85/0.30) | Ahamed et al., Table 12 (read through a summary; re-check by hand) |
| Cross-dataset, 3 test sets | 77.8% average accuracy (XGBoost) | Misiek & Hyla 2026, IEEE Access (abstract) |
| Cross-dataset, 20 shared features | 51-59% accuracy | Mia et al. 2024 (full text read) |
| Domain adaptation | about +0.06 F1 on average | Rashid et al. 2024, Computer Networks (abstract) |

Takeaways: no single best model; the number to beat is cross-source performance, not in-distribution accuracy; no paper found that audits PhiUSIIL as a shortcut ("leakage" is our inference).

Corrections to the LLM plans:
- "PhiUSIIL ~99.2% accuracy" is not confirmed. The only number seen was precision of 99.79% (pre-training) and 99.24% (incremental). Check the paper.
- Rashid same-dataset (0.98-1.00) and cross-dataset (0.67-0.94) F1 ranges: unverified.
- Misiek & Hyla F1 77.93%: unverified.
- Frontiers PhishTank-only result (0.995-0.999) is not a real cross-source test.
- Sabir et al. real title: "Reliability and Robustness analysis of Machine Learning based Phishing URL Detectors".
- ScienceDirect and IEEE full texts could not be opened (403). Three papers were checked by abstract only.

## 4. Data findings

| Dataset | Total | Phish | Legit | Dup URLs |
|---|---:|---:|---:|---:|
| PhiUSIIL | 235,795 | 100,945 | 134,850 | 425 |
| GramBeddings | 800,000 | 400,000 | 400,000 | 1 |
| PhishTank (snapshot 2026-10-01) | 76,451 | 76,451 | 0 | 3 |

| Pair | Exact URL overlap | eTLD+1 overlap |
|---|---:|---:|
| PhiUSIIL - GramBeddings | 459 (0.20%) | 11,060 (6.31%) |
| PhiUSIIL - PhishTank | 2,113 (2.76%) | 638 (4.21%) |
| GramBeddings - PhishTank | 72 (0.09%) | 399 (2.63%) |

Label conventions: PhiUSIIL `1 = legit`; GramBeddings `1 = Phish, 2 = Legitimate`; our code uses `phish = 1`. GramBeddings URLs can contain commas, so lines are split on the first comma only.

Other notes:
- OpenPhish free feed has only 300 URLs (unused).
- Tranco lists bare domains, so it has no deep links.
- CIC Trap4Phish "Final CSV" is the malicious-attachment dataset (Word, Excel, PDF, HTML features). No URL column. The "Source Files" tree has a "QR Codes" folder that was never inspected.
- PhishTank has about 15,000 unique domains over 76k URLs (inferred from overlap percentages), so a domain-disjoint filter removes large chunks at once.

## 5. Experiments (early, set aside)

### 5.1 Leakage and reproduction (`01`)
- Majority class: 57.2% accuracy.
- Rule `URLSimilarityIndex < 100 -> phishing`: accuracy 0.9967, F1 0.9961. All legitimate URLs have `URLSimilarityIndex` = 100.
- Gradient boosting on all engineered features, random 80/20 split: accuracy, F1, AUC all 1.0000.
- XGBoost would not load (needs `brew install libomp`), so scikit-learn `HistGradientBoostingClassifier` was used.

### 5.2 Train on PhiUSIIL, URL-only features (`03`)
Domain-disjoint in-distribution test: AUROC 0.998-0.999, F1 0.997-0.998.

AUROC on GramBeddings (50k/50k sample; 'domain' filter removes shared registered domains):

| Model | all features | no `is_https` |
|---|---:|---:|
| LR | 0.744 | 0.574 |
| RF | 0.517 | 0.543 |
| HistGB | 0.682 | 0.777 |

The domain filter changes AUROC by at most about 0.02. At threshold 0.5 the models flag about 98.6% of legitimate GramBeddings URLs as phishing, and F1 around 0.67 equals "predict everything phishing". Use AUROC and PR-AUC, not F1 or FPR@0.5, for external sets.

PhishTank + Tranco test is confounded (synthetic `https://` added to Tranco domains, homepage artifact): LR AUROC 0.99 with `is_https`, 0.49 without. Do not cite as generalization.

### 5.3 Feature shift (`04`)
Per-class means:

| Dataset / class | no path | has_www | is_https |
|---|---:|---:|---:|
| PhiUSIIL legit | 1.000 | 1.000 | 1.000 |
| PhiUSIIL phish | 0.403 | 0.415 | 0.486 |
| GramBeddings legit | 0.074 | 0.442 | 0.593 |
| GramBeddings phish | 0.001 | 0.139 | 0.469 |
| PhishTank phish | 0.071 | 0.042 | 0.911 |

Every PhiUSIIL legitimate URL is a bare `https://www.` homepage. Most shifted features between datasets: `path_len`, `path_depth`, `has_www`, `is_https`, `url_len`.

### 5.4 Both directions (`04`)
AUROC, URL-only features:

| Train - Test | Range over LR/RF/HistGB |
|---|---|
| PhiUSIIL - GramBeddings | 0.52-0.78 |
| GramBeddings - PhiUSIIL | 0.76-0.90 (0.81-0.90 with exact-URL filter only) |

GramBeddings in-distribution AUROC is 0.90-0.96 (harder, no shortcut). GramBeddings-trained models catch 16-54% of PhishTank at a 5%-FPR threshold; PhiUSIIL-trained models "detect" 99.9% but also flag about 98.6% of GramBeddings legitimate URLs, so that number is vacuous.

Caveats: one seed, one split, 22 hand-built features, GramBeddings sampled to 100k, models untuned.

## 6. Open items

1. Read `sota_verified_table.md` and check the key papers by hand (Frontiers Table 12, PhiUSIIL abstract).
2. `brew install libomp` if XGBoost is wanted (currently HistGB).
3. Inspect the Trap4Phish "Source Files > QR Codes" folder for URLs, or drop Trap4Phish.
4. Later, in order: rule baseline (`www & https & no path -> legit`), shortcut ablation, character n-gram TF-IDF baseline, multi-source training with a size-matched control, SVM and MLP.

## 7. Environment notes

- Auto mode's permission check blocked some shell commands in the working session. Scripts 02-04 were written to disk and run by the user in their own terminal; their output is what this log reports.
- RAR extraction needs `unar` (installed) and the password above.

## 8. Draft email to the professor

Drafted in chat. Content: in-distribution ceiling ~99.7% (even 2 features), cross-source reference 0.73-0.87 accuracy with 0.25-0.54 FPR, the unverified items listed in section 3, and a request to confirm the baseline definition. The user still needs to fill in names, attach `sota_verified_table.md`, and check Frontiers Table 12 before sending.

---

# Session log: 2026-11-01 (checkpoint prep)

`plan.md` (project root) is the live tracker and holds all result tables. This section is the chronological record and the file index for the new work. Sections 1-8 above are the Oct 1 state; where they say "experiments set aside" or list open items, this section supersedes them.

## 9. Feedback received on the proposal (10/20)
1. Is the similarity score using the answer, or a strong dataset shortcut? Check before calling it leakage.
2. Keep original reproduction separate from URL-only transfer; control size and class mix.
3. How does a validation-fixed threshold transfer, with no external labels to retune?
4. PhishTank supports recall only; keep the model list bounded.
Checkpoint: 2026-11-10. Final report: 2026-12-08.

## 10. What was done today
1. **Read the PhiUSIIL paper** (`1-s2.0-S0167404823004558-main.pdf` in the project root; sections 3.1, 4.1, 4.2, 5.1-5.6 read). USI = character-match score against the Open PageRank top-10M list; legit URLs came from that same list. Evaluation is prequential (predict, then `partial_fit`), not held out. Published numbers are in `plan.md` section 3.0.
2. **Shortcut check (F1)**, `scripts/06_shortcut_ablation.py`, `results/shortcut_*.csv`, `results/shortcut_log.txt`. USI uses no labels; it is a construction shortcut and is redundant: URL form (all legit = bare `https://www.` homepages) and page content (83% of phishing pages have 0 images) separate the classes without it. Our count of phishing with 80<=USI<100 is 7,341, equal to the paper's. The Tranco membership proxy was inconclusive.
3. **Reproduction (Part A)**, `scripts/05_reproduce_phiusiil.py`. BestSecurity accuracy 0.9934 (file order) / 0.9915 (shuffled mean of 4) vs paper 0.9924. Table 7 within about 0.0005 of the paper for both pre-train split modes. Outputs `results/repro_table{5,6,7}_*.csv`, `repro_features_*.csv`, logs in `results/logs/`.
4. **Reproduction with groups removed**, same script with `--drop usi|page|usi,page`, `results/repro_ablation_summary.csv`. Dropping USI: no change. URL-only (21 columns): accuracy 0.987.
5. **Part B helpers** in `scripts/common.py`: `url_type`, `class_mix`, `matched_sample`, `domain_split`, `drop_seen`, `val_threshold`, `at_threshold`, `transfer_metrics`.
6. **Part B transfer run**, `scripts/07_transfer_matched.py` (5 seeds, LR/RF/HistGB/MLP/NGRAM, featsets all and no_scheme, matched pool 11,666 at 50% phishing, validation-fixed 95%-recall threshold), `scripts/08_summarize_transfer.py` -> `results/transfer_summary.csv`, plus `transfer_runs.csv`, `transfer_class_mix.csv`.

## 11. Key results (see plan.md for tables and caveats)
- PhiUSIIL has zero deep-link legitimate URLs (legit homepage share 1.000), so URL type cannot be matched for PhiUSIIL as a source; targets are sliced by URL type instead.
- Validation-fixed thresholds do not transfer, in opposite directions: PhiUSIIL-trained flags 81-95% of GramBeddings legit URLs (recall 0.98); GramBeddings-trained keeps FPR near 0 but recall on PhiUSIIL is 0.53-0.58.
- PhishTank recall alone is misleading (0.94-0.97 from models that flag almost everything).
- Char n-gram model: best in-distribution on GramBeddings (AUROC 0.97) and best GramBeddings->PhiUSIIL (0.92), not better PhiUSIIL->GramBeddings (0.73). It does not fix the threshold.
- Without the scheme, PhiUSIIL-trained thresholds flag essentially everything on GramBeddings (FPR 0.97-0.99) while NGRAM AUROC rises (0.73 -> 0.87): AUROC and the fixed-threshold operating point disagree.
- Part of GramBeddings->PhiUSIIL ranking success comes from `is_https` (every PhiUSIIL legit URL is https).

## 12. Commands (run from the project folder)
```
.venv/bin/python scripts/06_shortcut_ablation.py
.venv/bin/python scripts/05_reproduce_phiusiil.py [--order shuffle --seed N] [--drop usi,page] [--table7 sequential|random] [--max-rows N]
nice .venv/bin/python scripts/07_transfer_matched.py --seeds 0,1,2,3,4        # about 5 min
.venv/bin/python scripts/08_summarize_transfer.py
```
Machine: Apple M4, 10 cores, 24 GB; all runs fit comfortably (the longest, Table 7, is about 20 min per mode).

## 13. Deviations and open points
- LightGBM and XGBoost not installed: sklearn GradientBoosting and ExtraTrees stand in for the paper's importance ensemble; mutual information on a 30k subsample; no feature scaling; deprecated `PassiveAggressiveClassifier` kept for fidelity.
- Paper row order unknown, so file-order and shuffled runs are both reported.
- Unexplained: dropping page content while keeping USI (0.9726) is worse than dropping both (0.9870).
- GramBeddings is the cached 100k sample in Part B; `has_www` not ablated; NGRAM untuned.
- Still to do before 2026-11-10: Table 3 baselines (held-out, 5 seeds), paper's final feature count (Sec 4.2.1) vs our 43, checkpoint write-up. Optional: no-www ablation, Table 7 over shuffled orders, featurize all 800k GramBeddings rows.
- After the checkpoint: combined-source training at matched size; decide about a third two-class source by about 2026-11-15; final report by 2026-12-08.

## 14. Table 3 baselines (added 2026-11-01, later in the same session)
`scripts/09_table3_baselines.py` (14 batch models, stratified random 80/20, 5 seeds, feature sets `selected` = 43 from script 05 and `url_only` = 21), merged with `--summarize` into `results/table3_summary.csv`; per-seed files `results/table3_seed*.csv`; logs `results/logs/table3_*.log`. About 3 min for all 5 seeds in parallel.
- Incremental-type models match the paper's Table 3 (BernoulliNB 0.988 vs 0.986; MultinomialNB 0.673 vs 0.690; Perceptron 0.980 vs 0.980). SGD is higher than the paper (0.984 vs 0.943) and unstable on unscaled features.
- Tree and boosting models are at 1.0000 on the 43 features (paper 0.9987-0.9999).
- With 21 URL-only columns most batch models still reach 0.995-0.998 (MLP 0.9981; AdaBoost 0.990, Naive Bayes lower), so the paper's ~99% does not need USI or page content.
- Not run: LightGBM, XGBoost, CatBoost (not installed; HistGB stands in), Voting, Stacking. Paper's split unknown.
- Paper's final feature count (Sec 4.2.1) checked: the paper states the procedure but not the resulting count or list (Algorithm 3 takes an unnamed "Reduced feature set"), so our 43 of 50 cannot be compared. The abstract's 99.24% / 99.79% match Table 5 BestSecurity and Table 7 90:10, our reproduction targets.
- Remaining before 2026-11-10: checkpoint write-up.

## 15. Checkpoint report draft (2026-11-01)
`checkpoint/checkpoint.tex` -> `checkpoint/checkpoint.pdf` (2 pages; built with `tectonic checkpoint.tex`). Sections: summary, response to feedback, Part A, similarity-index finding, Part B, remaining plan and risks. All numbers are taken from plan.md; format and length requirements of the course were not checked.

## 16. `no_scheme_no_www` ablation (2026-11-01)
Script 07 gained a third feature set, `no_scheme_no_www` (drops `is_https` and `has_www`; NGRAM strips `http(s)://` and a leading `www.`). The default `--featsets` is now `all,no_scheme,no_scheme_no_www` (about 7 min for 5 seeds). Results merged into `results/transfer_runs.csv`; `scripts/08_summarize_transfer.py` regenerates `results/transfer_summary.csv`; log `results/logs/transfer_nowww.log`.
- RF and HistGB still reach AUROC 1.00 on PhiUSIIL without scheme and `www`, so my earlier guess that trees recover through `has_www` is refuted (other URL-form columns carry it).
- `has_www` carries real signal on GramBeddings: in-distribution AUROC drops 0.02-0.04 without it.
- PhiUSIIL-trained transfer gets no better; GramBeddings-trained LR and NGRAM flag more PhiUSIIL legit URLs (FPR 0.02 -> 0.30 and 0.00 -> 0.16). The fixed-threshold conclusion is unchanged.

## 17. Decision (2026-11-01)
Full 800k GramBeddings featurization and Part B rerun deferred until after the 2026-11-10 checkpoint; the checkpoint states the 100k-sample caveat instead.

## 18. Check-in format (2026-11-09)
Professor's guidance for the checkpoint: informal is fine, show feasibility and that the pieces are in place, state conceptual issues, no performance analysis, say what is changing or new. Wrote `checkpoint/checkpoint_revised.tex` / `.pdf` from the original report: same structure and tone, result tables and all performance numbers removed, sections added for conceptual issues and changes since the proposal. The earlier numbers version, `checkpoint/checkpoint.pdf`, stays as backup. (A one-page informal draft was tried and removed at the user's request.)

## 19. Checkpoint feedback (11/20), 2026-11-23
Feedback: good clarification of shortcut vs leakage; the transfer study is now the main contribution; show the results and explain the remaining source / URL-type differences (a larger dataset alone will not resolve those); keep thresholds fixed from source validation. Consequences recorded in `plan.md` section 3b: explaining source / URL-type differences becomes the core work (source profile, source discriminator, canonical-URL variant, score distributions, GramBeddings collection description); the 800k rerun is optional; the diversity experiment is secondary and lacks an independent target without a third two-class source. A quick profile showed that even homepage URLs differ by source and class (trailing slash, `www`, `https`): e.g. 99% of GramBeddings phishing homepages end with `/` against 53% of legitimate ones, and 0% of PhiUSIIL legitimate ones. Not yet analysed further.

## 20. Third-source vetting (2026-11-23)
Searched for a third independent two-class URL dataset for option C. Best candidate: PhreshPhish (HF `phreshphish/phreshphish`; Jul 2024 to Dec 2025; benign from Webroot browsing telemetry and brand-targeted Google results, phishing from PhishTank/APWG/NetCraft; 666k rows; CC BY 4.0, anti-phishing research only; 36.6 GB because of HTML). Rejected or weak: LegitPhish (legit only Wikipedia and Stack Overflow, phishing from URLHaus), PhishBench-External D4V (1,000 rows), the 579,920-URL dataset (unverified, no link), ISCX-URL2016 (2016, backup). Several papers could not be read (403 or bot challenge), so details rest on summaries and are marked unverified in `plan.md` section 3b. Nothing downloaded yet; overlap with PhiUSIIL, GramBeddings and the PhishTank snapshot is not yet measured. A1-A4 are on hold at the user's request.

## 21. Plan update and message to professor (2026-11-23)
Option C1 chosen: find and vet a third source (PhreshPhish best candidate). A1-A4 not started. Plan section 3b updated with the steps, threshold rule for combined or third-source runs, fallback, and a revised schedule. A message to the professor with the open questions was drafted in chat (not sent by Claude).

## 22. Third source: PhreshPhish pulled and overlap-checked (2026-11-25)
Installed pyarrow 26.0.1 (requirements.txt updated). Read parquet footers and only url/label/date over HTTP range requests (0.1-0.4 MB per shard, 56 shards), saved 666,315 rows to data/phreshphish/phreshphish_url_label_date.csv. Counts match the dataset card. Exact-URL overlap with PhiUSIIL and GramBeddings is about 0; with the PhishTank snapshot 4.3% of its phishing rows. Registered-domain overlap is 55% (phish) and 21% (legit) against PhiUSIIL, 40% and 35% against GramBeddings, driven by shared hosting platforms (884 domains, e.g. gitbook.io, webflow.io, pages.dev). After domain removal against PhiUSIIL: 134k phish and 292k legit rows remain. Form profile: PhreshPhish legit are 92.7% deep links, phishing 44.9% homepage, opposite of PhiUSIIL's homepage-only legit class. Verdict: usable as an independent third target with the caveat that domain-disjoint evaluation drops hosting-platform phishing. Not yet run through script 07. A1-A5 still not started.

## 23. PhreshPhish feature cache (2026-11-25)
Moved the pull code into scripts/10_pull_phreshphish.py (smoke-tested with --limit 2). Added scripts/11_build_phreshphish_cache.py: balanced 50,000 per class sample (seed 0, duplicates dropped), eTLD+1 plus the 22 URL-only features, saved to data/cache/phreshphish.pkl (100,000 x 25, same columns as gram_sample.pkl, 2 s). 123 rows have an empty registered domain (IP hosts). Next: add PhreshPhish to script 07.

## 24. Script 07 extended with PhreshPhish (2026-11-25)
scripts/07_transfer_matched.py: added --variants, PhreshPhish cache as target for every source and as source PhreshPhish/all (homepage-only variant skipped: about 3,600 legit homepages). Pool size stays 11,666 (set by all four variants). Mix file name follows --out. Smoke run (seed 0, LR/RF/HistGB, all features) took 18 s; smoke CSVs deleted. Finding from the smoke run: hosting-platform domains make the domain-disjoint splits lumpy (val phishing share 0.35-0.57), so single-seed fixed-threshold results vary; use the 5-seed means. Full run launched into results/transfer_runs_v2.csv, log results/transfer_v2.log.

## 25. A1 source profile and A2 source discriminator (2026-11-25)
scripts/12_source_profile.py writes results/source_profile.csv (form profile by source, class, URL type, four sources). scripts/13_source_discriminator.py writes results/source_discriminator.csv (HistGB, 4000 per source, domain-disjoint, 3 seeds, three feature sets). Findings: within class the source is recoverable (legit PhiUSIIL vs others 0.96-1.00 AUROC even homepage-only; phishing pairs 0.85-0.93; PhreshPhish vs PhishTank phishing only 0.71). Homepage legit trailing slash: 0% / 53% / 100% for PhiUSIIL / GramBeddings / PhreshPhish. No feature attribution yet. Results in plan.md under 'A1/A2 results'. Transfer v2 run still going in the background.

## 26. A5 GramBeddings description (2026-11-25)
Read the dataset page and GitHub README/Dataset.md (via subagent). Stated: 800k balanced, crawled May 2019 to June 2021 weekly, custom crawler plus manual domain-similarity filter for legitimate URLs. Not stated: phishing feed, crawler seeds, homepage vs deep, per-class dates, preprocessing, limitations. Dataset.md label convention (-1 legit, 1 phish) differs from our files (1 phish, 2 legit); we keep our file's convention. Details in plan.md 'A5 results'.

## 27. A3 and A4 code (2026-11-25)
Script 07 gained --canonical (A3), --save-scores/--score-models (A4), and a robust class-mix output path (earlier version could overwrite the results file when --out had no 'runs' in its name; the scratch smoke file was affected, no real results were). New: scripts/14_build_canonical_cache.py (data/cache/*_canon.pkl), scripts/15_plot_scores.py, results/scores_seed0.npz, results/fig_scores_HistGB.png and _LR.png, results/transfer_runs_scores_seed0.csv (seed-0 run used for the scores). matplotlib installed (requirements.txt). Canonical LR smoke (seed 0) does not improve transfer. Full canonical 5-seed run waits for the v2 job (seed 3 of 5 running).

## 28. Transfer v2 finished and summarized (2026-11-25)
5 seeds x 4 sources x 3 feature sets x 5 models = 2400 rows in results/transfer_runs_v2.csv (class mix: transfer_class_mix_v2.csv, log transfer_v2.log). Old three sources reproduce exactly. scripts/08 now takes input/output paths; summary in results/transfer_summary_v2.csv. Headline table in plan.md. Canonical (A3) 5-seed run started into results/transfer_runs_canon.csv.

## 29. A3 canonical run and cross-model check (2026-11-25)
Ran scripts/07 --canonical (5 seeds, 5 models, feature set all; 800 rows, results/transfer_runs_canon.csv; log transfer_canon.log) and compared with the raw v2 runs (results/canonical_vs_raw.csv). Mean cross-source AUROC (8 cells) raw vs canonical: HistGB 0.694/0.667, LR 0.693/0.618, MLP 0.683/0.662, NGRAM 0.819/0.757, RF 0.651/0.665; in-source AUROC drops (e.g. PhiUSIIL HistGB 0.997 -> 0.847). Cross-source FPR at the fixed threshold rises. Conclusion: formatting explains part of in-source separability but not the transfer failure. Cross-model check: fixed-threshold recall/FPR pattern agrees across HistGB/LR/MLP/NGRAM/RF; pair-level AUROC varies widely by model (PhreshPhish -> PhiUSIIL 0.27 to 0.99). NGRAM's 0.99 there is a https://www. artifact (drops to 0.72-0.74 without it). Process note: plan.md was emptied by a bad overwrite command and restored from the Claude Code file snapshot (v7) plus the re-added v2 block; backups now kept in the scratchpad and tracked files staged in git (not committed).

## 30. B1/B2: final tables and figures for Part B (2026-11-25)
scripts/16_final_tables_figures.py (reads results only, writes new files): results/final_tables.md plus final_table_main.csv, final_table_slices.csv, final_table_phishtank_recall.csv, final_table_canonical.csv; figures fig_operating_points.png and fig_canonical_vs_raw.png. Figures checked by eye; fixed a legend collision and added labels for the 95% and no-skill reference lines. tabulate 0.10.0 installed (needed by DataFrame.to_markdown) and added to requirements.txt. Fixed dataset colors from the dataviz skill's first three categorical slots. Not done: Part A final table (paper reproduction) and an A1 source-profile figure. plan.md edited only with the Edit tool; backups in the scratchpad.

## 31. B1 Part A final tables (2026-11-25)
scripts/17_final_table_partA.py reads the per-run reproduction CSVs (repro_table5/6 file order and shuffled seeds 1-4, the four feature-group configurations, repro_features_*, repro_table7_*, table3_seed0-4) and writes results/final_partA_tables.md and final_partA_{table5,table6,ablation,table3,table7}.csv (new files only). Means recomputed from the raw runs agree with repro_ablation_summary.csv and table3_summary.csv (no differences above 5e-4); Table 7 mean absolute gap to the paper 0.0004 (sequential) and 0.0005 (random). Numbers unchanged from plan section 3.1. B1 is complete; remaining: report writing (E), optional A1 figure and 800k rerun.

## 32. Report draft 1 (2026-11-25)
Wrote report/outline.md and report/report.tex (compiled to report/report.pdf, 10 pages with appendix). Tables are generated, not typed: scripts/18_make_latex_tables.py reads results/final_*.csv, shortcut_ablation_summary.csv, source_profile.csv, source_discriminator.csv and transfer_runs_v2.csv and writes report/tables/*.tex; scripts/19_report_figures.py makes the 2x2 operating-point figure (results/fig_operating_points_2x2.png); scripts/15_plot_scores.py was changed so every column has a title (figure files regenerated). Citations verified: PhreshPhish = Dalton et al., arXiv:2507.10854 (title and 8 authors read on arXiv). Not verified and flagged in the text: Rahman et al. title and first names; GramBeddings paper authors, venue, year; related-work numbers are abstract-level. Wording corrections made while drafting: no claim that prior studies failed to control pool size or class mix (abstracts only); "more data would not help" stated as an argument, not a measured result (800k featurization not run); 41% of PhiUSIIL phishing missed was a seed-0 figure, 5-seed HistGB recall is 0.53; PhishTank recall numbers regenerated with fixed decimals. Appendix B timing: v2 transfer run 808 s, canonical run 275 s.

## 33. README update (2026-11-25)
Rewrote README.md (backup of the previous version in the scratchpad): findings now cover the three-source transfer study, the source discriminator and the canonical-URL test; layout adds report/; data table adds PhreshPhish (script 10); run commands now list scripts 10-19 with explicit --out for script 07 (its default would overwrite the earlier three-source results file); added a Known gaps section. Checked that every script the README names exists.

## 34. Coverage audit (2026-11-25)
Re-read the proposal and the submitted checkpoint PDFs and the 11/20 feedback and compared with plan.md and the report. Gaps recorded in plan.md ("Coverage audit"): combined-source diversity experiment not run (promised in proposal and checkpoint), full 800k GramBeddings not run, reference-list check done by text search of the paper PDF (none of Ahamed, Misiek, Hyla, Rashid, GramBeddings present) but not yet in the report, PR-AUC and class-mix logs not in the report, paper-side critique points (Table 8 cross-dataset accuracy comparison, unverified generalization claim, own batch baselines beat the framework, Table 7 trend) not yet in the report, no feature attribution for source differences, two reference placeholders, and the "written independently" commitment: the report draft was written by Claude and cannot be submitted as the student's own writing.

## 35. Audit re-prioritized against the 11/20 feedback (2026-11-25)
Rereading the checkpoint feedback: the transfer study is the main contribution, results must be shown, source and URL-type differences explained, a larger dataset alone will not resolve them, thresholds stay fixed from source validation. All three asks are covered. The combined-source diversity experiment and the 800k rerun are therefore optional (to be stated as descoped in the report). The feedback-aligned remaining gap is explanation depth for the source and URL-type differences (feature attribution for the source discriminator, by URL type), then report content (PR-AUC, class mix, paper-critique paragraph, reference-list check sentence), then the reference placeholders and independent writing. plan.md audit block edited accordingly.

## 36. Audit items 1-3 done (2026-11-25)
Item 1: scripts/20_source_importance.py, results/source_importance.csv and source_importance_top.csv; on homepages is_https/has_www/path_len carry 82% of the discriminator's permutation importance (path_len equals the trailing slash for every legitimate homepage in all three sources), on deep URLs 32%, the rest on entropy, path_depth, url_len, host_len, n_subdomains, digit_ratio. Item 2: report additions (reference-list sentence, paper-critique paragraph, Table 7 trend, PR-AUC table, class-mix table, training-size range, importance table); scripts/18 extended; report is 12 pages and compiles without unresolved references. Item 3: references [5] and [8] filled from Crossref (GramBeddings matched by PII; Rahman et al. matched by journal, volume, issue, pages; first Crossref call for Rahman hit a 429 rate limit, second succeeded). The Crossref calls sent no email or personal details.

## 37. Combined-source (diversity) experiment (2026-11-26)
scripts/21_combined_sources.py (new; script 07 untouched): leave-one-source-out, pairs pooled at matched total size 11,666 (half from each source), pooled-validation 95%-recall threshold, targets held-out third source, own-source test rows, PhishTank. 5 seeds, 5 models, feature sets all and no_scheme_no_www, 1,050 rows, about 4.5 min. scripts/22_summarize_combined.py compares with the single-source runs in transfer_runs_v2.csv (results/combined_vs_single.csv, combined_in_source.csv). Findings: pooled FPR below the worse single source in 30/30 cells and below both in 9/30; pooled AUROC above both in 15/30 and never when PhiUSIIL is held out; pooling helps ranking on held-out PhreshPhish, little on GramBeddings with all features, and only moves the recall/FPR trade-off on PhiUSIIL; no pooled model transfers an operating point; small in-source cost; single-source n-gram models are competitive but partly read scheme/www. A first draft of the conclusion sentence said pooling improved ranking on only one of three held-out sources, which was wrong for the no_scheme_no_www features (GramBeddings held out, 4 of 5 models above both singles); corrected in the report. Report updated (Section 6 paragraph, Table 9, limitation 9, conclusion), script 18 extended (combined_main table). Smoke outputs deleted.

## 38. Decision: skip the 800k GramBeddings rerun (2026-11-26)
Not required by the 11/20 feedback (a larger dataset alone will not resolve the source differences); the report states the full 800k featurization was not run and treats the sample-size point as an argument from the measurements. Other optional items still not done: A1 source-profile figure, edit-distance check of the USI [80,100) band, Table 7 over shuffled orders, real XGBoost via libomp. Remaining: related-work number check against the papers (student), final report written independently (student), course page limit and AI-assistance policy check.
