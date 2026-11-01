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
