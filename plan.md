# Plan and progress tracker

Project: Replicating and critiquing PhiUSIIL phishing URL detection under dataset shift (Replication and Critique track).
Primary paper: Prasad and Chandra 2024, Computers & Security 136.
Proposal: `proposal/ML_ProjectProposal.pdf` (feedback score 10/20, feasibility "High").
Last updated: 2026-11-01. Checkpoint: **2026-11-10**. Diversity experiments: late November. Final report: **2026-12-08**.

Detailed earlier notes live in `MD/project_log.md`; verified literature is in `MD/sota_verified_table.md`. Run scripts from `Project/` with `.venv/bin/python scripts/<name>.py`.

---

## 1. Proposal feedback and how each point is handled

| # | Feedback | Action | Where it lands |
|---|---|---|---|
| F1 | Is the similarity score using the answer, or a strong dataset shortcut? Check before calling it leakage. | Find how `URLSimilarityIndex` is computed (paper + code). Ablate it. Test the rule on deep-link legit URLs. Use the word "shortcut" until shown otherwise. | **Done 2026-11-01** (section 3.2): construction shortcut, no labels, redundant with page-content and URL-form artifacts |
| F2 | Keep original reproduction separate from URL-only transfer; control size and class mix. | Two separate parts (A, B) with separate tables. Matched train sizes, fixed phishing ratio, report class mix of every split, match or stratify by URL type (homepage vs deep link). | Checkpoint (A and B design), late Nov (full B) |
| F3 | How does a validation-fixed threshold transfer, with no external labels to retune? | Fix the 95%-recall threshold on source validation only. Apply unchanged to the target. Report realized recall and FPR. ROC-AUC and PR-AUC stay as headline metrics. Oracle threshold, if shown, is labeled an upper bound. | Checkpoint |
| F4 | PhishTank supports recall only; keep the model list bounded. | PhishTank: report recall at the validation-fixed threshold only (no FPR or AUC). Model list capped at LR, RF, gradient boosting, MLP, plus char n-gram reference. BERT and CharCNN are cited from Ahamed et al., not rerun. | Checkpoint |

---

## 2. Done so far (as of 2026-11-01)

### Literature and setup
- [x] SOTA reference table built, with unverified claims flagged (`MD/sota_verified_table.md`).
- [x] Related work chosen: Ahamed 2026, Misiek and Hyla 2026, Rashid 2024.
- [x] Datasets obtained: PhiUSIIL (235,795), GramBeddings (800,000), PhishTank snapshot of 2026-10-01 (76,451, phishing only).
- [x] Shared loaders and one URL-only feature extractor (22 lexical features) in `scripts/common.py`.
- [x] Proposal submitted and graded.
- [x] Read the PhiUSIIL paper (2026-11-01); published numbers and protocol recorded in 3.0.
- [x] Shortcut check on `URLSimilarityIndex` (script 06, section 3.2): no labels used, a construction shortcut, and removable without losing accuracy because page-content and URL-form artifacts also separate the classes.

### First-pass results (single seed, untuned, scikit-learn HistGB in place of XGBoost)
- [x] Rule `URLSimilarityIndex < 100 -> phishing`: accuracy 0.9967, F1 0.9961. Every legit PhiUSIIL URL has index 100. (script 01)
- [x] Gradient boosting on all engineered features, random split: accuracy, F1, AUC all 1.0000. (script 01)
- [x] Dataset summary: sizes, duplicates, exact-URL and eTLD+1 overlap across the three sources. (script 02)
- [x] URL-only models trained on PhiUSIIL: in-distribution (domain-disjoint) AUROC 0.998-0.999; on GramBeddings AUROC 0.52-0.78. (script 03)
- [x] Reverse direction (train GramBeddings, test PhiUSIIL): AUROC 0.76-0.90. GramBeddings in-distribution 0.90-0.96. (script 04)
- [x] Feature shift: every PhiUSIIL legit URL is a bare `https://www.` homepage; largest shifts in `path_len`, `path_depth`, `has_www`, `is_https`, `url_len`. (script 04)
- [x] At threshold 0.5, PhiUSIIL-trained models flag about 98.6% of GramBeddings legit URLs as phishing, so F1 and FPR at 0.5 are not meaningful on external data.
- [x] PhishTank + Tranco test judged confounded (synthetic `https://`, homepage artifact). Not citable as generalization.

### Known weaknesses of the first pass (Oct 1), and where each was addressed
- One seed, one split, no tuning -> 5 seeds (shuffled orders for Part A, seeds 0-4 for Part B); models are still untuned.
- 22 hand-built features only; GramBeddings sampled to 100k -> still true; the 800k featurization is deferred until after the checkpoint (3.3).
- No original-feature reproduction against the paper -> done (3.0, 3.1: Tables 3, 5, 6, 7).
- No incremental learning (`partial_fit`) run -> done (3.1).
- Thresholds were 0.5 or oracle -> validation-fixed 95%-recall thresholds in Part B (3.3).
- Class mix and size not matched across training sets -> matched pool size and 50% phishing share, logged (3.3).
- Nothing showed how `URLSimilarityIndex` is built -> paper read, shortcut check done (3.0, 3.2).

---

## 3. Checkpoint deliverables (due 2026-11-10)

Proposal timeline promised: reproduction and baselines done before the checkpoint. Feedback items F1-F4 are folded in.

### 3.0 What the paper says (read 2026-11-01, `1-s2.0-S0167404823004558-main.pdf`)

Positive class in the paper is **legitimate = 1** (TP = legit correctly kept). Pages are Computers & Security 136 (2024) 103545.

**Data collection (Sec 3.1).** Legitimate URLs come from the Open PageRank top-10M list; phishing URLs from PhishTank, OpenPhish, MalwareWorld (collected 2022-10-01 to 2023-05-21). Class mix 57% legit / 43% phishing. Paper states all records are unique.

**URL similarity index, USI (Sec 4.1, Eq. 2, Algorithm 2).**
- USI is computed between the given URL and URLs in "the list of the top 10 million legitimate websites downloaded from Open PageRank". It is a character-by-character match score, 0-100.
- USI = 100 means identical to a listed legitimate URL -> classed legitimate. USI in [80, 100) -> phishing (look-alike). USI < 80 -> passed to the ML model (Phase 2).
- It is a hand-built rule, not a learned feature, and it uses no labels directly.
- **Consequence for F1:** the legitimate class was sampled from the same list USI is matched against, so every legitimate URL matches itself exactly and scores 100 by construction. This is **membership in the list that generated the legit class** (a construction shortcut), not leakage of the label column. Your first-pass numbers agree: legit USI = 100 for all 134,850, rule `< 100 -> phishing` gives 99.67%.
- The paper reports 7,341 phishing URLs caught by the `80 <= USI < 100` rule (Sec 5.4). Its Table 4 shows look-alike domains such as `exampl.com` scoring 83.5 against `example.com`.
- Open question the paper does not answer: whether legit URLs were removed from the reference list before computing USI. The released data says no (all legit = 100).

**Phase 2 (Sec 4.2).** Feature selection: tree-model importance > 0, then top 85% by mutual information. Incremental algorithms: BernoulliNB, PassiveAggressive, SGDClassifier (chosen from Table 2). Hyperparameters via GridSearchCV: BNB alpha 0.01, binarize 0.0, fit_prior False; PA C=5, fit_intercept False, n_iter_no_change 50; SGD alpha 0.01, eta0 100, n_iter_no_change 50.

**Evaluation protocol (Sec 4.2.2, Algorithm 3).** Prequential, one record at a time: initialize on the first record, then for every later record predict, then `partial_fit` on that record. It is **not a held-out test set**; the dataset is in file order with no shuffle shown. Ensemble votes (predict = sum of 3 votes for "legit"):
- LowSecurity: legit if any 1 of 3 says legit. BestSecurity: legit if 2 of 3 agree. HighSecurity: legit only if all 3 agree.
- Pre-training experiment (Sec 5.6): pre-train classically on 10%..90%, incremental on the rest. Whether the split is sequential or random is not stated.

**Published numbers to reproduce.**

| Item | Accuracy | Precision | Recall | F1 | MCC |
|---|---:|---:|---:|---:|---:|
| Table 5, LowSecurity | 0.88258 | 0.82966 | 0.99999 | 0.90690 | 0.77595 |
| Table 5, BestSecurity (headline) | 0.99239 | 0.98870 | 0.99810 | 0.99338 | 0.98449 |
| Table 5, HighSecurity | 0.97409 | 0.99979 | 0.95490 | 0.97683 | 0.94877 |
| Table 7, pre-train 10:90 | 0.99573 | | | | |
| Table 7, pre-train 90:10 (best) | 0.99792 | | | | |

Table 6 confusion matrix (TP/TN/FP/FN, legit = positive): Low 134849 / 73259 / 27686 / 1; Best 134594 / 99406 / 1539 / 256; High 128768 / 100918 / 27 / 6082.

Table 2 incremental algorithm selection, accuracy: BernoulliNB 0.98654, GaussianNB 0.57154, MultinomialNB 0.69085, PassiveAggressive 0.99418, Perceptron 0.94364, SGD 0.94658.
Table 3 (baseline comparison, Table 3 lists accuracy in order): BernoulliNB 0.98644, PassiveAggressive 0.98021, SGD 0.94294, MultinomialNB 0.68961, Perceptron 0.98041; AdaBoost 0.99981, LightGBM 0.9999, XGB 0.99993, CatBoost 0.99987, GradientBoosting 0.99978; KNN 0.99378, RandomForest 0.99982, DecisionTree 0.99866, LogisticRegression 0.99654, Bagging 0.99923; Vote_Hard 0.99874, Vote_Soft 0.99817, Stacking 0.99979. Train/test split for Table 3 is not stated in the sections read.

Notes for the write-up:
- Table 3 batch models (RF 0.99982, XGB 0.99993) beat the paper's own incremental ensemble (0.99239), so the incremental framework does not improve accuracy; its claim is adaptability.
- The prequential protocol means early records are scored by a barely trained model, which pulls the reported accuracy down. A held-out split is not comparable; the reproduction must use the paper's protocol first.
- The paper reports no cross-dataset or domain-disjoint test.
- Sections read: 3.1, 4.1, 4.2, 5.1-5.6, Table 8 header. Not read in detail: feature table (Sec 3.1.2-3.1.3), Table 8 numbers, Sec 5.7 discussion. Check these before the checkpoint.

### 3.1 Part A: reproduction (PhiUSIIL only, original features)

Script `scripts/05_reproduce_phiusiil.py` (run 2026-11-01, file order, seed 0). Outputs `results/repro_table5_*.csv`, `repro_table6_*.csv`, `repro_table7_{sequential,random}_*.csv`, `repro_features_*.csv`; logs in `results/logs/`. Each full run takes about 3 min for Tables 5-6 and about 20 min for Table 7 per mode.

**Tables 5 and 6 (paper protocol: init on record 1, then predict-then-`partial_fit`, legit = positive)**

| Profile | Accuracy ours / paper | Precision | Sensitivity | F1 ours / paper | MCC ours / paper |
|---|---|---|---|---|---|
| LowSecurity | 0.8944 / 0.8826 | 0.8441 / 0.8297 | 0.9999 / 0.9999 | 0.9155 / 0.9069 | 0.7974 / 0.7760 |
| BestSecurity | 0.9934 / 0.9924 | 0.9911 / 0.9887 | 0.9973 / 0.9981 | 0.9942 / 0.9934 | 0.9864 / 0.9845 |
| HighSecurity | 0.9730 / 0.9741 | 0.9999 / 0.9998 | 0.9528 / 0.9549 | 0.9758 / 0.9768 | 0.9467 / 0.9488 |

Confusion counts (TP / TN / FP / FN), ours vs paper:
- Low: 134846 / 76046 / 24899 / 3 vs 134849 / 73259 / 27686 / 1
- Best: 134489 / 99737 / 1208 / 360 vs 134594 / 99406 / 1539 / 256
- High: 128490 / 100937 / 8 / 6359 vs 128768 / 100918 / 27 / 6082

**Tables 5 and 6 over shuffled row orders** (seeds 1-4, run 2026-11-01; mean and std over 4 runs; file-order run shown for comparison; `results/repro_table5_shuffle_summary.csv`)

| Profile | Accuracy mean (std) | F1 mean (std) | MCC mean (std) | Paper accuracy / F1 |
|---|---|---|---|---|
| LowSecurity | 0.8978 (0.0118) | 0.9180 (0.0086) | 0.8037 (0.0215) | 0.8826 / 0.9069 |
| BestSecurity | 0.9915 (0.0002) | 0.9926 (0.0002) | 0.9826 (0.0005) | 0.9924 / 0.9934 |
| HighSecurity | 0.9716 (0.0006) | 0.9746 (0.0006) | 0.9441 (0.0012) | 0.9741 / 0.9768 |

BestSecurity per run, accuracy: file order 0.99335; shuffled 0.99156, 0.99151, 0.99169, 0.99112.
BestSecurity confusion counts, shuffled mean (std): TP 134402 (30), TN 99382 (47), FP 1564 (47), FN 447 (30). Paper: 134594 / 99406 / 1539 / 256.

What this adds:
- Shuffled orders match the paper's counts for the error cell that matters more closely than file order does (FP 1,564 vs paper 1,539; file order gave 1,208). File order gives a slightly lucky run (+0.002 accuracy over the shuffled mean). The paper's own row order is unknown.
- BestSecurity accuracy reproduces to within 0.001 either way (shuffled mean 0.9915 vs paper 0.9924, about 4 std below; file order 0.9934 is above). Report both and say the paper's order is not stated.
- BestSecurity is stable across orders (std 0.0002). LowSecurity is not (std 0.012), because it depends on how fast the least confident learner catches up.
- FN is higher than the paper's (447 vs 256): our learners call about 190 more legitimate URLs phishing. Not investigated.

**Reproduction with feature groups removed (shortcut tie-in), run 2026-11-01** (`--drop usi|page|usi,page`, feature selection re-run after the drop, file order plus shuffled seeds 1-4; `results/repro_ablation_summary.csv`, `repro_table5_*_drop-*.csv`, logs `results/logs/repro_*drop*.log`). Groups as in script 06: USI = `URLSimilarityIndex`; page = 28 page-content columns; the 21 URL-only columns remain when both are dropped.

BestSecurity, paper protocol, shuffled orders (mean of 4 seeds, std in parentheses; paper: accuracy 0.9924, F1 0.9934):

| Features | n features after selection | Accuracy | F1 | MCC | FP / FN (mean) |
|---|---:|---|---|---|---|
| all (reproduction) | 43 | 0.9915 (0.0002) | 0.9926 (0.0002) | 0.9826 | 1564 / 447 |
| drop USI | 42 | 0.9914 (0.0001) | 0.9925 (0.0001) | 0.9824 | 1671 / 364 |
| drop page content (keeps USI) | 19 | 0.9726 (0.0004) | 0.9760 (0.0003) | 0.9439 | 3408 / 3062 |
| drop USI and page content | 18 | 0.9870 (0.0005) | 0.9887 (0.0004) | 0.9735 | 2046 / 1014 |

File-order runs agree (0.9934 / 0.9932 / 0.9717 / 0.9879).

**What this shows**
1. **The paper's headline number does not depend on `URLSimilarityIndex`.** Dropping it changes BestSecurity accuracy by 0.0001. This matches script 06 (HistGB) and the paper's own design, where USI is a separate Phase 1 rule.
2. **It also barely depends on page content.** With 21 URL-only columns (no USI, no page content) the incremental ensemble still reaches accuracy 0.987 and F1 0.989. Page content adds about 0.5 points, not the bulk of the 99%.
3. **So the 99% is reproducible from URL form alone,** consistent with the collection artifacts found in 3.2 (legit = bare `https://www.` homepages). The paper's result is not evidence of generalization; Part B shows the same kind of URL-only features fail across datasets.
4. **Unexpected: dropping page content while keeping USI is worse (0.9726) than dropping both (0.9870).** With few features, USI seems to hurt the incremental learners. Not investigated; a guess is that the unscaled 0-100 USI dominates the linear learners (PassiveAggressive, SGD). Treat as an open observation, do not state it as a finding.
5. LowSecurity and HighSecurity move less cleanly; BestSecurity is the stable profile (std 0.0001-0.0005).

Caveat: shuffled orders only for the std; the paper's row order is unknown. Selection is re-run per configuration, so the number of features differs (see table).

**Table 3 baselines (batch models, held-out), run 2026-11-01** (`scripts/09_table3_baselines.py`, one process per seed, 5 seeds, about 3 min total; `results/table3_seed*.csv`, `results/table3_summary.csv`, logs `results/logs/table3_*.log`). Stratified random 80/20 split per seed (the paper does not state its split). Legit = positive. Feature sets: `selected` = the 43 features kept by script 05; `url_only` = 21 URL-derived columns (no USI, no page content). Accuracy mean (std) vs paper Table 3:

| Model | Paper | selected (43) | url_only (21) |
|---|---:|---|---|
| BernoulliNB | 0.98644 | 0.98789 (0.0005) | 0.93714 (0.0011) |
| MultinomialNB | 0.68961 | 0.67323 (0.0023) | 0.77806 (0.0018) |
| PassiveAggressive | 0.98021 | 0.97728 (0.0148) | 0.99698 (0.0002) |
| Perceptron | 0.98041 | 0.97985 (0.0115) | 0.99513 (0.0026) |
| SGD | 0.94294 | 0.98365 (0.0127) | 0.99645 (0.0003) |
| LR | 0.99654 | 0.99992 (0.00003) | 0.99635 (0.0004) |
| Decision tree | 0.99866 | 1.00000 | 0.99534 (0.0002) |
| Random forest | 0.99982 | 1.00000 | 0.99681 (0.0003) |
| AdaBoost | 0.99981 | 0.99998 | 0.98966 (0.0006) |
| GradientBoosting | 0.99978 | 1.00000 | 0.99561 (0.0005) |
| HistGB (vs paper's LightGBM) | 0.99990 | 1.00000 | 0.99740 (0.0004) |
| Bagging | 0.99923 | 1.00000 | 0.99652 (0.0003) |
| KNN | 0.99378 | 0.99888 (0.0001) | 0.99673 (0.0003) |
| MLP (not in paper) | | 0.99992 | 0.99806 (0.0002) |

**What this shows**
1. **Table 3 reproduces in spirit.** The incremental-type models match the paper closely (BernoulliNB 0.988 vs 0.986, MultinomialNB 0.673 vs 0.690, Perceptron 0.980 vs 0.980, PassiveAggressive 0.977 vs 0.980). SGD is much higher than the paper's 0.943 and unstable across seeds on unscaled features (std 0.013). Batch models are at or above the paper's values; on the 43-feature set the tree models are saturated at 1.0000, so the 4th-decimal comparison with the paper says little.
2. **Held-out accuracy on these features is about 1.0000,** which fits the shortcuts in 3.2: with USI and page content, a random split is trivially separable.
3. **URL-only batch models (no USI, no page content) mostly still reach 0.995-0.998** (MLP 0.9981, HistGB 0.9974; AdaBoost 0.9897, Naive Bayes lower), above the paper's incremental BestSecurity result (0.992). Matches the incremental-ensemble ablation above (0.987 with URL-only features).
4. **Naive Bayes models lose on URL-only** (BernoulliNB 0.937, MultinomialNB 0.778): they need the page-content features.

Caveats: split unknown in the paper; LR/KNN/MLP use standardized inputs while the paper's preprocessing is not stated; LightGBM, XGBoost, CatBoost, Voting and Stacking not run (HistGB stands in for the boosting rows); PassiveAggressive and SGD are high-variance on unscaled features.

**Table 7 (classical pre-train on p%, then predict-then-`partial_fit` on the rest; BestSecurity accuracy on the incremental part)**

| Pre-train | Paper | Ours, sequential split | Ours, random split |
|---|---:|---:|---:|
| 10% | 0.99573 | 0.99545 | 0.99622 |
| 20% | 0.99593 | 0.99630 | 0.99709 |
| 30% | 0.99637 | 0.99741 | 0.99747 |
| 40% | 0.99708 | 0.99712 | 0.99721 |
| 50% | 0.99725 | 0.99747 | 0.99759 |
| 60% | 0.99751 | 0.99799 | 0.99799 |
| 70% | 0.99755 | 0.99785 | 0.99808 |
| 80% | 0.99763 | 0.99813 | 0.99796 |
| 90% | 0.99792 | 0.99839 | 0.99796 |

Mean absolute gap to the paper: 0.0004 (sequential) and 0.0005 (random). Neither split mode matches clearly better.

**Reading of the results**
- The headline BestSecurity result reproduces to within about 0.001 accuracy (0.9934 vs 0.9924). Rankings across the three profiles match.
- Counts differ by a few hundred rows in the error cells (for example Best FP 1,208 vs 1,539). Likely causes, none tested: different feature subset, randomness in PassiveAggressive and SGD, no scaling choice made in the paper.
- Table 7 is reproduced to within about 0.001 at every split. Ours is slightly higher for most splits; our metric is on the incremental part only, which the paper does not specify.
- The Table 7 trend (accuracy rises with pre-training) is partly reproduced: the sequential split rises from 0.9955 to 0.9984; the random split is flat after 60%.
- Protocol caveat for the report: this is a prequential test on a file whose class order is already mixed (115k class changes in 236k rows), not a held-out test, and the data has the shortcuts found in 3.2. Matching the paper's number does not show the model generalizes.

**Paper check (2026-11-01):** the abstract's two headline numbers, 99.24% (fully incremental) and 99.79% (pre-training), are the Table 5 BestSecurity accuracy (0.99239) and the Table 7 90:10 row (0.99792) that we reproduced; so those two tables are the right reproduction targets.

**Feature selection (ours):** 43 of 50 candidate features kept; `URLSimilarityIndex` is kept. Dropped: IsDomainIP, HasObfuscation, NoOfObfuscatedChar, ObfuscationRatio, NoOfURLRedirect, NoOfSelfRedirect, Crypto. The paper's final feature count was not found in the sections read; check Sec 4.2.1 and compare.

**Deviations from the paper (state in the report):** LightGBM and XGBoost not installed (sklearn GradientBoosting and ExtraTrees stand in for importance); mutual information on a 30k-row subsample; no feature scaling; deprecated `PassiveAggressiveClassifier` kept for fidelity.

- [x] Re-read the PhiUSIIL paper: published numbers recorded in 3.0.
- [x] Reproduce the paper's protocol (Tables 5 and 6), file order, seed 0.
- [x] Reproduce Table 7 with both sequential and random pre-train splits.
- [x] Feature selection as described; kept features recorded; `URLSimilarityIndex` is kept.
- [x] Compare with published numbers and explain gaps (above).
- [x] Seeds: `--order shuffle --seed 1..4` for Tables 5-6, mean and std reported above.
- [ ] Optional: Table 7 over shuffled orders (about 20 min per run); only if time allows.
- [x] Check the paper's final feature count (Sec 4.2.1): **not stated.** The text gives only the procedure (importance > 0 in RF, DT, LightGBM, XGBoost; then top 85% by mutual information) and passes the result to Algorithm 3 as an unnamed "Reduced feature set" (RFS). Neither a count nor a list appears anywhere in the extracted text (feature importance is mentioned at Sec 4.2.1 only); a figure or table that lists it, if one exists, was not in the text extraction. Our 43 of 50 candidates cannot be compared with a paper number. The 50 candidates equal the 56 released columns minus FILENAME, URL, Domain, TLD, Title and label. Report this as an unspecified detail, with our 43 as our choice.
- [x] Reproduce Table 3 baselines on a held-out stratified 80/20 split, 5 seeds, separate from the prequential run (`scripts/09_table3_baselines.py`); results above.
- [x] Rerun the reproduction without `URLSimilarityIndex` and without page-content features: `--drop` option added to script 05; results above.
- [ ] Optional: install `libomp` and use real XGBoost, only if the published pipeline needs it.

### 3.2 Shortcut check on `URLSimilarityIndex` (F1) - DONE 2026-11-01

Script `scripts/06_shortcut_ablation.py`; outputs `results/shortcut_*.csv`, full log `results/shortcut_log.txt`. Seeds 0-2, HistGB (200 iterations).

**Results**

| Check | Result |
|---|---|
| USI bands, legit | 134,850 / 134,850 at exactly 100 |
| USI bands, phishing | 786 at 100; 7,341 in [80,100); 92,818 below 80 |
| Paper cross-check | Paper Sec 5.4 reports 7,341 phishing caught by the [80,100) rule. Ours is exactly 7,341, so we have the same data and score. |
| Single-feature AUROC (strength) | USI 0.996; LineOfCode 0.990; NoOfExternalRef 0.988; NoOfImage 0.980; NoOfSelfRef 0.972; NoOfJS 0.971 |
| Rule `USI<100 -> phish` | acc 0.9967, F1 0.9961, 0% of legit flagged |
| Rule `not https://www.<host>[/] homepage -> phish` | acc 0.9956, F1 0.9948, 0% of legit flagged (no list, no labels) |
| Rule `has path -> phish` | acc 0.6935, 0% of legit flagged |
| Page content | 83.4% of phishing pages have 0 images (legit 1.0%); 77.1% have 0 JS (legit 1.1%); median LineOfCode 12 (phish) vs 1,105 (legit) |
| URL form | 100% of legit URLs match `https://www.<host>` and none ends with `/`; 36.5% of phishing URLs end with `/` |

Ablation, HistGB, mean over 3 seeds (AUROC / accuracy):

| Feature set | n | Random split | Domain-disjoint split |
|---|---:|---|---|
| all | 50 | 1.0000 / 1.0000 | 1.0000 / 1.0000 |
| no USI | 49 | 1.0000 / 0.9999 | 1.0000 / 1.0000 |
| no page content (keeps USI) | 22 | 0.9999 / 0.9998 | 0.9998 / 0.9998 |
| page content only | 28 | 1.0000 / 0.9984 | 0.9999 / 0.9977 |
| no USI, no page content | 21 | 0.9988 / 0.9971 | 0.9990 / 0.9971 |
| URL columns only (no derived) | 18 | 0.9985 / 0.9976 | 0.9986 / 0.9979 |
| USI only | 1 | 0.9946 / 0.9954 | 0.9927 / 0.9940 |

**What this shows**
1. **USI uses no labels.** The paper defines it as a character-match score against the Open PageRank top-10M list (Sec 4.1). So "label leakage" is not the right word for it.
2. **USI is a strong shortcut but not a necessary one.** Dropping it changes nothing (AUROC 1.0000). The dataset is separable by at least three redundant artifacts: USI, empty page captures for phishing, and URL form (legit = bare `https://www.` homepages).
3. **The [80,100) band is mostly an artifact of short bare URLs, not typosquats of famous sites.** 99.7% of those phishing URLs are bare homepages, only 8.1% have a registered domain in Tranco, and a sample of 25 shows names like `http://www.bombtire.com`. This is consistent with short `http://www.<name>.com` strings sharing characters with some entry among 10M listed URLs. It is not proven (no edit-distance test was run).
4. **Domain-disjoint splits change nothing**, so the shortcut is not domain memorization.

**What this does not show (caveats to state in the report)**
- The Tranco proxy was inconclusive. Only 33.1% of legit registered domains are in Tranco top-1M, which is expected for a 1M list against a 10M list. So "all legit URLs are in the Open PageRank list" rests on the paper's Sec 3.1 text, not on our data.
- Tranco membership for phishing is not clean evidence either (48% of the <80 band are in Tranco, probably phishing on free-hosting domains).
- The "empty phishing pages" finding is a failed-capture pattern in the released data; we did not test why.
- The `www`-homepage rule and USI are perfectly confounded for legit URLs, so we cannot say which of the two a model uses.

**Wording for the report:** "URLSimilarityIndex is a construction shortcut: legitimate URLs were drawn from the same list the index is matched against, and it uses no labels. It is also redundant: URL form and page-content artifacts separate the classes without it."

- [x] Find how the index is computed (paper Sec 4.1).
- [x] Distribution by class and band; matches the paper's 7,341.
- [x] Tranco membership proxy (inconclusive, see caveats).
- [x] Characterize the [80,100) phishing band (sample plus domain share).
- [x] Single-feature AUROC for every numeric feature.
- [x] Ablation with and without USI, page content, derived features; random and domain-disjoint splits; 3 seeds.
- [x] Rule baselines including the homepage rule.
- [x] Conclusion worded as "construction shortcut".
- [ ] Optional, only if time: edit-distance check of the [80,100) band against Tranco domains to confirm they are not typosquats.
- [ ] Optional, only if time: test the rules and models on deep-link legitimate URLs from GramBeddings (this is the transfer experiment in 3.3, so do it there rather than here).
- [ ] Carry the finding forward: Part A must report results with and without USI and page content, and Part B uses URL-only features and never USI.

### 3.3 Part B: URL-only transfer (separate from Part A) (F2, F3, F4)

**Helpers done 2026-11-01** (`scripts/common.py`, sanity-checked on the cached feature tables): `url_type`, `class_mix`, `matched_sample` (exact phishing share, optional homepage/deep restriction), `domain_split` (train/val/test with no shared registered domain), `drop_seen`, `val_threshold` (source validation only), `at_threshold` (recall, FPR, precision; FPR is NaN without legit rows), `transfer_metrics`.

Sanity-check findings that shape the design:
- **PhiUSIIL has zero deep-link legitimate URLs** (legit homepage share 1.000; phishing 0.716). A deep-link-only PhiUSIIL training set cannot be class-balanced, so URL type cannot be matched for PhiUSIIL as a source. Plan: train PhiUSIIL on all data, and evaluate every target sliced by URL type (homepage-only, deep-only) so the homepage artifact is visible instead of controlled away. For GramBeddings as source, train both on all URLs and on homepage-only (about 15% legit / 12% phishing homepages, so homepage-only sets are small: about 11k rows in the 100k cached sample; featurize more of the 800k if needed).
- **Validation-fixed threshold already shows the F3 effect.** LR trained on PhiUSIIL, threshold set for 95% recall on PhiUSIIL validation: in-distribution test recall 0.933, FPR 0.000; on GramBeddings (after dropping seen URLs and domains) recall 0.996 but FPR 0.947 and AUROC 0.569. The threshold does not transfer: it keeps recall and flags almost everything.
- The domain-disjoint split verified: zero shared domains between train, val and test.

**Transfer run done 2026-11-01** (`scripts/07_transfer_matched.py`; 5 seeds, LR / RF / HistGB / MLP, about 70 s total on the laptop; `results/transfer_runs.csv`, `transfer_summary.csv`, `transfer_class_mix.csv`, log `results/logs/transfer_5seeds.log`).

Design as run: 22 URL-only features, all variants sampled to the same pool (11,666 rows, 50% phishing), then domain-disjoint 70/15/15 split (train 7.7k-8.5k rows because grouped splits are uneven). Threshold = 95% recall on source validation, applied unchanged. Target rows whose URL or registered domain appear in training are dropped. Mean over 5 seeds (std in `transfer_summary.csv`).

| Train variant | Target | AUROC (LR / RF / HistGB / MLP) | Recall at fixed threshold | FPR at fixed threshold |
|---|---|---|---|---|
| PhiUSIIL/all | PhiUSIIL test | 1.00 for all | 0.93-0.94 | 0.00 |
| PhiUSIIL/all | GramBeddings all | 0.78 / 0.61 / 0.76 / 0.77 | 0.98-0.99 | 0.81-0.95 |
| PhiUSIIL/all | GramBeddings homepage only | 0.78 / 0.65 / 0.80 / 0.76 | 0.94-0.96 | 0.66-0.79 |
| GramBeddings/all | GramBeddings test | 0.91 / 0.94 / 0.94 / 0.94 | 0.94-0.95 | 0.29-0.47 |
| GramBeddings/all | PhiUSIIL all | 0.84 / 0.83 / 0.83 / 0.91 | 0.53-0.58 | 0.00-0.02 |
| GramBeddings/all | PhiUSIIL homepage only | 0.78 / 0.77 / 0.76 / 0.87 | 0.38-0.46 | 0.00-0.02 |
| GramBeddings/homepage | GramBeddings test | 0.94-0.96 | 0.95-0.97 | 0.29-0.33 |
| GramBeddings/homepage | PhiUSIIL all | 0.87 / 0.82 / 0.82 / 0.84 | 0.52-0.57 | 0.00-0.01 |
| GramBeddings/homepage | PhiUSIIL homepage only | 0.82 / 0.74 / 0.74 / 0.78 | 0.34-0.39 | 0.00-0.01 |

PhishTank, recall only, at the fixed threshold: PhiUSIIL/all 0.94-0.97; GramBeddings/all 0.68 (LR), 0.87 (RF), 0.84 (HistGB), 0.80 (MLP); GramBeddings/homepage 0.84-0.94. PhiUSIIL deep-link slice (phishing only): GramBeddings/all 0.89-0.93, GramBeddings/homepage 0.93-0.99.

**Char n-gram reference and scheme-free ablation added 2026-11-01** (same script, `--featsets all,no_scheme`, 5 seeds, 5 models, about 5 min; summary via `scripts/08_summarize_transfer.py` -> `results/transfer_summary.csv`; log `results/logs/transfer_5seeds_ngram_ablation.log`). NGRAM = TF-IDF over characters (2-4 grams, 100k features) + LR, untuned. `no_scheme` drops `is_https` for the feature models and strips `http(s)://` from the URL for NGRAM. `has_www` / the `www.` text stays in both, so this removes only the scheme shortcut.

AUROC / recall / FPR at the validation-fixed threshold, mean of 5 seeds (full mean +/- std in `transfer_summary.csv`):

| Train -> Target | Model | all features | no scheme |
|---|---|---|---|
| PhiUSIIL -> PhiUSIIL test | LR | 1.00 / 0.94 / 0.00 | 0.93 / 0.94 / 0.41 |
| | HistGB | 1.00 / 0.93 / 0.00 | 1.00 / 0.94 / 0.00 |
| | NGRAM | 1.00 / 0.93 / 0.00 | 0.91 / 0.94 / 0.57 |
| PhiUSIIL -> GramBeddings all | LR | 0.78 / 0.98 / 0.86 | 0.79 / 1.00 / 0.99 |
| | HistGB | 0.76 / 0.98 / 0.81 | 0.75 / 1.00 / 0.98 |
| | NGRAM | 0.73 / 0.95 / 0.66 | 0.87 / 1.00 / 0.98 |
| GramBeddings -> GramBeddings test | LR | 0.91 / 0.95 / 0.47 | 0.91 / 0.95 / 0.46 |
| | NGRAM | 0.97 / 0.93 / 0.15 | 0.97 / 0.94 / 0.16 |
| GramBeddings -> PhiUSIIL all | LR | 0.84 / 0.53 / 0.01 | 0.77 / 0.53 / 0.02 |
| | HistGB | 0.83 / 0.53 / 0.00 | 0.82 / 0.53 / 0.00 |
| | MLP | 0.91 / 0.58 / 0.01 | 0.82 / 0.58 / 0.01 |
| | NGRAM | 0.92 / 0.50 / 0.00 | 0.86 / 0.52 / 0.00 |
| GramBeddings -> PhiUSIIL homepage only | NGRAM | 0.89 / 0.33 / 0.00 | 0.80 / 0.35 / 0.00 |

**`no_scheme_no_www` ablation added 2026-11-01** (`--featsets ... no_scheme_no_www`: drops `is_https` and `has_www` for the feature models; strips `http(s)://` and a leading `www.` for NGRAM; 5 seeds, about 2 min; rows merged into `results/transfer_runs.csv`, summary via script 08). Mean AUROC / recall / FPR over 5 seeds; "all" / no scheme / no scheme and no www:

| Train -> Target | Model | all | no scheme | no scheme, no www |
|---|---|---|---|---|
| PhiUSIIL -> PhiUSIIL test | RF | 1.00 / 0.94 / 0.00 | 0.99 / 0.94 / 0.02 | 1.00 / 0.94 / 0.02 |
| | HistGB | 1.00 / 0.93 / 0.00 | 1.00 / 0.94 / 0.00 | 1.00 / 0.94 / 0.00 |
| | LR | 1.00 / 0.94 / 0.00 | 0.93 / 0.94 / 0.41 | 0.93 / 0.95 / 0.41 |
| | NGRAM | 1.00 / 0.93 / 0.00 | 0.91 / 0.94 / 0.57 | 0.90 / 0.95 / 0.58 |
| PhiUSIIL -> GramBeddings all | HistGB | 0.76 / 0.98 / 0.81 | 0.75 / 1.00 / 0.98 | 0.67 / 1.00 / 0.97 |
| | RF | 0.61 / 0.99 / 0.95 | 0.61 / 1.00 / 0.98 | 0.56 / 1.00 / 0.98 |
| | NGRAM | 0.73 / 0.95 / 0.66 | 0.87 / 1.00 / 0.98 | 0.84 / 1.00 / 0.97 |
| GramBeddings -> GramBeddings test | LR | 0.91 / 0.95 / 0.47 | 0.91 / 0.95 / 0.46 | 0.87 / 0.95 / 0.66 |
| | HistGB | 0.94 / 0.94 / 0.29 | 0.94 / 0.94 / 0.30 | 0.92 / 0.94 / 0.39 |
| | NGRAM | 0.97 / 0.93 / 0.15 | 0.97 / 0.94 / 0.16 | 0.96 / 0.93 / 0.19 |
| GramBeddings -> PhiUSIIL all | LR | 0.84 / 0.53 / 0.01 | 0.77 / 0.53 / 0.02 | 0.75 / 0.67 / 0.30 |
| | NGRAM | 0.92 / 0.50 / 0.00 | 0.86 / 0.52 / 0.00 | 0.83 / 0.68 / 0.16 |
| | HistGB | 0.83 / 0.53 / 0.00 | 0.82 / 0.53 / 0.00 | 0.81 / 0.54 / 0.01 |

**What it shows**
1. **Trees do not rely on `has_www` to separate PhiUSIIL.** Without the scheme and without `www`, RF and HistGB still score AUROC 1.00 in distribution. My earlier guess that they recover through `has_www` is wrong: other URL-form columns (path length, URL and host length, dot count; all legit PhiUSIIL URLs are bare homepages) carry it. This matches script 06, where 18 URL columns alone gave AUROC 0.9985.
2. **`has_www` is real signal on GramBeddings, not only a PhiUSIIL shortcut.** GramBeddings in-distribution AUROC drops 0.02-0.04 (LR 0.91 -> 0.87, HistGB 0.94 -> 0.92) and FPR rises (LR 0.46 -> 0.66) without it.
3. **PhiUSIIL-trained transfer gets no better:** AUROC on GramBeddings falls further for HistGB (0.75 -> 0.67), RF (0.61 -> 0.56) and NGRAM (0.87 -> 0.84), and the fixed threshold still flags 97-98% of legitimate URLs.
4. **GramBeddings-trained linear and text models shift operating point on PhiUSIIL:** LR FPR 0.02 -> 0.30 and NGRAM 0.00 -> 0.16 while recall rises (0.53 -> 0.67, 0.52 -> 0.68). Trees barely move. The headline conclusion (the fixed threshold does not transfer) is unchanged.

Caveats: means over 5 seeds only; MLP is noisy, so I only quote effects well above that noise. Removing `has_www` and the scheme does not remove all traces (host length, URL length and dot count still encode them), so this is a partial ablation.

**What the n-gram model and the ablation add**
1. **A stronger URL-only model helps ranking in one direction only.** On GramBeddings, NGRAM is the best in-distribution (AUROC 0.97 vs 0.91-0.94) and the best GramBeddings -> PhiUSIIL transfer (0.92 vs 0.83-0.91). It is not better PhiUSIIL -> GramBeddings (0.73, same range as the feature models). Neither fixes the threshold: GramBeddings -> PhiUSIIL recall is still 0.50 at FPR 0.00.
2. **PhiUSIIL's near-perfect in-distribution score depends on the scheme for linear and text models.** Without it, LR drops to AUROC 0.93 with FPR 0.41 and NGRAM to 0.91 with FPR 0.57. Trees (RF 0.99, HistGB 1.00) recover, presumably through `has_www` and other URL-form features; not verified.
3. **Without the scheme, PhiUSIIL-trained thresholds flag essentially everything on GramBeddings** (recall 1.00, FPR 0.97-0.99; PhishTank recall also 1.00). The AUROC for NGRAM rises (0.73 -> 0.87) while the operating point gets worse, so AUROC and the fixed threshold tell different stories. Report both.
4. **Part of the GramBeddings -> PhiUSIIL ranking success comes from the scheme.** LR 0.84 -> 0.77, MLP 0.91 -> 0.82, NGRAM 0.92 -> 0.86 when the scheme is removed, because every PhiUSIIL legitimate URL is https. Trees are unchanged (0.82-0.83). So the PhiUSIIL-as-target numbers are partly inflated by a PhiUSIIL artifact.
5. GramBeddings in-distribution results do not change without the scheme (no shortcut there).

**Caveats added:** NGRAM is untuned (one n-gram range, one feature cap). `has_www` is ablated in the next block (`no_scheme_no_www`); it does not change the conclusions. Std across seeds is large for MLP and for no-scheme LR/NGRAM on PhiUSIIL (FPR std up to 0.35).

**What this shows**
1. **The validation-fixed threshold does not transfer, and it fails in opposite directions.** Trained on PhiUSIIL, it keeps recall (0.98) and flags 81-95% of GramBeddings legitimate URLs. Trained on GramBeddings, it keeps FPR near 0 and recall falls to 0.53-0.58 on PhiUSIIL. Source validation recall is 0.95 in every case, so the failure is invisible without a target.
2. **PhiUSIIL-trained models fail even on homepage-only GramBeddings** (AUROC 0.65-0.80, FPR 0.66-0.79). The homepage artifact is not the whole story: PhiUSIIL legitimate homepages look different from GramBeddings legitimate homepages.
3. **Training GramBeddings on homepages only does not rescue transfer to PhiUSIIL** (recall on PhiUSIIL homepage slice 0.34-0.39). URL form alone does not explain the gap either.
4. **PhishTank recall alone is misleading.** PhiUSIIL-trained models get 0.94-0.97 recall on PhishTank, but the same models flag 81-95% of GramBeddings legitimate URLs at that threshold. High recall from a model that flags almost everything is not detection. Report PhishTank recall next to the FPR on a legitimate target at the same threshold.
5. In-distribution, PhiUSIIL is trivial (AUROC 1.00, FPR 0.00); GramBeddings is harder (AUROC 0.91-0.96, FPR 0.29-0.47 at 95% recall).
6. The four models behave similarly, except RF is clearly worst when trained on PhiUSIIL (AUROC 0.61-0.65 on GramBeddings) and MLP is noisy across seeds.

**Caveats**
- Train sizes match only to within about 10% (domain grouping). The phishing share is about 0.5 in train but varies in the source test (0.48-0.63) and in the targets (0.29-0.48, except the phishing-only PhiUSIIL deep-link slice), so precision and flagged-share are not comparable across rows; AUROC, recall and FPR are.
- GramBeddings is the cached 100k sample, not all 800k. Homepage-only GramBeddings sets are small (pool 11,666 caps every variant).
- The PhiUSIIL "deep" slice has no legitimate URLs, so only recall is defined there.
- Char n-gram reference model not run yet; `is_https` is a known shortcut and no scheme-free ablation is run in this table (the Oct 1 results showed it matters).
- `oracle_fpr_at_95rec` is saved in `transfer_runs.csv` as a labeled upper bound only; RF shows 1.0 in some rows (score ties), not investigated.
- [x] Model list: LR, RF, gradient boosting, MLP, char n-gram TF-IDF + LR (5 models, bounded).
- [x] Split protocol: registered-domain-disjoint splits (eTLD+1). Source data gets train / validation / test; target data is test only.
- [x] Control size and class mix (train within about 10% of equal size, 50% phishing; class mix logged in `transfer_class_mix.csv`): subsample every training set to the same N and the same phishing ratio; log the class mix and URL-type mix (homepage vs deep link) of every set.
- [x] Run PhiUSIIL-only and GramBeddings-only training at matched size, both directions. (Combined training comes later, see section 4.)
- [x] Threshold protocol: choose the 95%-recall threshold on source validation, apply unchanged to the target, report realized recall and FPR. Never retune on target labels.
- [x] Metrics: ROC-AUC, PR-AUC (headline), FPR at validation-fixed 95% recall. 5 seeds; mean and std in `transfer_summary.csv`.
- [x] PhishTank: recall at the validation-fixed threshold only, for each trained model. State plainly that it cannot measure FPR.
- [x] Redo old script 03/04 outputs under this protocol (script 07 supersedes them; old CSVs stay as "first pass").
- [x] Scheme-free ablation (`is_https` dropped / scheme stripped) in script 07.
- [x] Char n-gram reference model in script 07.
- [x] `no_scheme_no_www` variant: trees do not rely on `has_www`; see the block above.
- [ ] Demoted to optional after the 11/20 feedback (a larger dataset will not resolve the source / URL-type differences; see 3b): featurize all 800k GramBeddings rows so targets and homepage-only training sets are not capped by the 100k sample. Featurizing takes about 20 s; the Part B rerun is estimated at 30-60 min (not measured) and changes every Part B number, so redo tables, report and README together. Fold it into the diversity experiment.

### 3.4 Code and housekeeping
- [x] New scripts 05 to 09 (`05_reproduce_phiusiil.py`, `06_shortcut_ablation.py`, `07_transfer_matched.py`, `08_summarize_transfer.py`, `09_table3_baselines.py`), with shared sampling, split and threshold helpers in `common.py`.
- [x] Write every result table to `results/` as CSV.
- [x] `MD/project_log.md` updated through section 17 (2026-11-01); keep updating after each step.

### 3.5 Checkpoint report or slides content

Version for the Nov 10 check-in (professor's guidance: show feasibility and that the pieces are in place, state conceptual issues, no performance analysis, say what is changing or new): `checkpoint/checkpoint_revised.tex` and `.pdf` (2 pages, formal style, no result numbers). The earlier version with all result tables, `checkpoint/checkpoint.pdf`, is kept as backup.

Draft written 2026-11-01: `checkpoint/checkpoint.tex` and `checkpoint/checkpoint.pdf` (2 pages, same style as the proposal). Needs a read-through and the course's required format check; numbers come from the tables in this file.

- [x] Reproduction table: ours vs published, with explanation of gaps.
- [x] Shortcut finding (F1) with the evidence.
- [x] Transfer table with matched size and class mix, and validation-fixed thresholds.
- [x] What changed since the proposal because of the feedback (one short paragraph).
- [x] Remaining plan and risks.

---

## 3b. Checkpoint feedback (11/20) and revised priorities (2026-11-23)

Feedback: (1) good clarification of shortcut vs label leakage; the transfer study now looks like the main contribution. (2) Show the results and explain the remaining source / URL-type differences; a larger dataset alone will not resolve those. Keep thresholds fixed from source validation.

What it changes:
- **The transfer study (Part B) is the main contribution;** the diversity experiment is secondary.
- **Explaining the source / URL-type differences is now the main open work.** Part B shows the failure; the report has to say why.
- **The 800k GramBeddings rerun is demoted** to an optional robustness check (it does not address the stated problem).
- **Thresholds stay fixed on source validation.** Oracle numbers (`oracle_fpr_at_95rec`) stay out of every headline table.
- **The final report must show results** (the checkpoint deliberately did not).

Quick profile run 2026-11-23 (`url_type`; 100k GramBeddings sample) showing that even the "homepage" URL type differs by source and class:

| Source / class | Homepage share | Homepage URLs ending with `/` | Homepage `www` | Homepage `https` |
|---|---:|---:|---:|---:|
| PhiUSIIL legit | 1.000 | 0.000 | 1.000 | 1.000 |
| PhiUSIIL phishing | 0.716 | 0.437 | 0.536 | 0.393 |
| GramBeddings legit | 0.151 | 0.530 | 0.393 | 0.492 |
| GramBeddings phishing | 0.117 | 0.991 | 0.100 | 0.449 |
| PhishTank phishing | 0.365 | 0.806 | 0.026 | 0.820 |

So a trailing slash (path length 1 in the 22 features) is a formatting artifact that points toward "phishing" in all three sources (PhiUSIIL legit homepages never end with `/`; 99% of GramBeddings phishing homepages do), and `www` / `https` composition differs by source even within the homepage type. Homepage-only GramBeddings training may learn the slash. This is a first look, not yet a result.

**Revised task list**

A. Explain the source / URL-type differences (core). Status 2026-11-23: not started; held at the user's request until the third-source question is settled; the user has not yet said when to start.

- [x] A1. DONE 2026-11-25. Source profile table per dataset x class x URL type: trailing slash, `www`, `https`, length, TLD mix (`scripts/12_source_profile.py`, `results/source_profile.csv`; PhreshPhish added).
- [x] A2. DONE 2026-11-25 (AUROC only; top features not extracted). Source discriminator (adversarial validation): within each class, can a model tell the sources apart? `scripts/13_source_discriminator.py`, `results/source_discriminator.csv`. Results in "A1/A2 results" below.
- [x] A3. DONE 2026-11-25 (5 seeds, 5 models; results in "A3 and cross-model results" below). Code notes: `scripts/14_build_canonical_cache.py` writes `data/cache/*_canon.pkl` (canonical URL = strip, lowercase, no scheme, no leading www., no trailing /; features recomputed; is_https and has_www become constant 0); `scripts/07_transfer_matched.py --canonical` reads them (NGRAM reads the canonical text; default out `results/transfer_runs_canon.csv`, default featset `all`). Row selection, homepage/deep type and seen-URL filters still use the original URL. Smoke run (LR, seed 0) works. To run after the v2 job: `PYTHONPATH=scripts nice .venv/bin/python scripts/07_transfer_matched.py --canonical --seeds 0,1,2,3,4`. Original: lowercase, strip scheme, leading `www.` and trailing `/` before extracting features (and for NGRAM).
- [~] A4. CODE AND SEED-0 FIGURES DONE 2026-11-25, 5-seed not needed. `07 --save-scores` stores seed-0 scores (feature set all, LR and HistGB) in `results/scores_seed0.npz`; `scripts/15_plot_scores.py` draws `results/fig_scores_HistGB.png` and `results/fig_scores_LR.png` (rows = training source, columns = source validation, source test, other datasets, PhishTank; dashed line = threshold fixed at 95% recall on source validation). Original: save scores for seed 0 and plot source-validation vs target score distributions with the fixed threshold. Explains the opposite failure directions.
- [x] A5. DONE 2026-11-25 (dataset page and GitHub README/Dataset.md read through a subagent; see "A5 results" below). Most collection details are NOT stated, so the report must not claim them.

B. Show the results:
- [x] B1. Part B DONE 2026-11-25: `scripts/16_final_tables_figures.py` writes `results/final_tables.md` and `results/final_table_{main,slices,phishtank_recall,canonical}.csv` (5-seed mean±sd, fixed-threshold numbers; also the source discriminator table). Part A DONE 2026-11-25: `scripts/17_final_table_partA.py` computes Tables 5, 6, 3, 7 and the feature-group ablation from the per-run CSVs (file order and 4 shuffled orders, mean and sample sd; Table 3 over 5 seeds) into `results/final_partA_tables.md` and `results/final_partA_{table5,table6,ablation,table3,table7}.csv`; it cross-checks against `repro_ablation_summary.csv` and `table3_summary.csv` (no mismatches above 5e-4; Table 7 mean abs gap 0.0004 sequential, 0.0005 random, same as 3.1). Original: final Part A and Part B tables with mean and std over seeds, fixed-threshold numbers only.
- [~] B2. Done 2026-11-25: `results/fig_operating_points.png` (recall vs FPR at the fixed threshold, per training source and model), `results/fig_canonical_vs_raw.png`, `results/fig_scores_HistGB.png` / `fig_scores_LR.png` (A4). Dataset colors are fixed (PhiUSIIL blue #2a78d6, GramBeddings orange #eb6834, PhreshPhish aqua #1baf7a; first three validated slots of the dataviz palette; light mode only). Not built: a source-profile (A1) figure (the A1/A2 tables exist). Original: Figures: transfer matrix (AUROC, recall, FPR by train -> target), score distributions (A4), source profile (A1). Use the dataviz skill.

C. Diversity experiment (secondary), needs a decision:
- [~] C1. **Steps 2-4 DONE 2026-11-25 (see "C1 results" below); step 5 (third-source transfer run) DONE 2026-11-25 as transfer v2 (PhreshPhish as target and as source).** **Decision 2026-11-23: option 1, find and vet a third independent two-class source.** Without one there is no independent target for combined training (only per-source held-out sets and PhishTank recall). Vetting done on paper (details below, "C1 vetting"): best candidate PhreshPhish; LegitPhish weak; D4V rejected; others unverified. Still to do, in order: (1) send the questions to the professor (draft message written 2026-11-23); (2) install `pyarrow` and test a column-pruned read of one PhreshPhish shard; (3) pull `url`/`label`/`date` into `data/phreshphish/`; (4) profile it and measure URL and registered-domain overlap with PhiUSIIL, GramBeddings and the PhishTank snapshot; (5) only if overlap is small, use it as a third source with the same protocol (matched pools, domain-disjoint splits, thresholds fixed on source validation). If it fails the overlap check or cannot be read in time, fall back to option 2 (combined training with a pooled-source validation threshold, reported on per-source held-out sets, URL-type slices and PhishTank recall only, clearly caveated). Threshold rule for any combined or third-source run: fixed on the training sources' pooled validation data, never on the target.

**C1 vetting of a third independent two-class source (2026-11-23).** Read via search results, dataset pages and subagent reads; several papers were blocked (ScienceDirect 403, ResearchGate 403, PMC bot challenge), so "unverified" marks what rests on summaries or snippets. Nothing has been downloaded or checked against our data yet.

| Candidate | Fit | Main reasons |
|---|---|---|
| **PhreshPhish** (Hugging Face `phreshphish/phreshphish`, arXiv 2507.10854) | **Best candidate, conditional** | Collected Jul 2024 to Dec 2025 (later than PhiUSIIL's 2022-23). Phishing from PhishTank, APWG eCrime Exchange and NetCraft. Benign from Webroot browsing telemetry plus Google search results for targeted brands, explicitly not Tranco/Alexa or Common Crawl, so benign URLs likely include deep links (paper summary: median path length 29 benign vs 1 phishing; unverified, check the paper's Fig. 6; the HF viewer sample shows benign URLs with paths). 666,315 rows: train 498,255 (276,729 benign, 221,526 phish), test 168,060 (91,260 benign, 76,800 phish; temporal split, leakage-filtered). Labels via human-in-the-loop clustering; the authors say they do not claim it is error-free (redirects to brand pages can be mislabeled; scrapable pages may be easier). CC BY 4.0, "anti-phishing research only". Columns: sha256, url, html, label, target, date, lang, lang_score. |
| LegitPhish (Mendeley hx4m73v2sf, Data in Brief 2025) | Weak | 101,219 URLs stated, but 63,678 phishing + 37,540 legitimate = 101,218. Phishing from URLHaus (a malware-distribution feed) plus "verified" repositories. Legitimate URLs only from Wikipedia and Stack Overflow, so very low domain diversity (a model can learn the two sites). CC BY 4.0. Paper unread. A derivative, PhiLegit-100K, merges it with PhiUSIIL: avoid. |
| PhishBench-External D4V (Mendeley 2ctjcnm9kn) | Reject | 1,000 rows, Tranco legit (domain-level) plus PhishTank, a 27-feature table, label column has three values. |
| "Realistic Large-Scale Dataset" (579,920 URLs, legit with deep links) | Unverified | Paper blocked, no download link found. |
| ISCX-URL2016 | Backup, only snippet-level | 2016; benign from Alexa (about 35k), phishing from OpenPhish (about 10k); old, so time and source differences are confounded; OpenPhish overlap with PhiUSIIL possible. |

PhreshPhish specifics to resolve before using it:
- **Size:** 36.6 GB in total (train 27.4 GB, test 9.2 GB; shards of about 350 MB), almost all of it HTML. `url`, `label` and `date` are small. The dataset-viewer rows API returns HTML too (about 730 KB for 2 rows), so it is not a bulk route. The practical route is a column-pruned read of the parquet shards (`url`, `label`, `date` only); not yet tested. A direct shard request redirects (HTTP 302) to a CDN; anonymous range reads are unverified.
- **Independence:** phishing partly from PhishTank like PhiUSIIL and our PhishTank snapshot, so URL and registered-domain overlap is possible. Measure it (exact URL, eTLD+1) against PhiUSIIL, GramBeddings and the PhishTank snapshot before calling it independent.
- **Benign bias:** browsing telemetry plus targeted-brand search results may over-represent popular and brand pages. Report URL-type and domain profiles with A1.
- **Base rate:** the test split is 46% phishing, which the authors call unrealistically high; we use matched 50% pools anyway.

Next step if approved: install `pyarrow` into the venv (add to `requirements.txt`), test a column-pruned read of one shard, then pull `url`/`label`/`date` into `data/phreshphish/` (gitignored), profile it and measure overlap. Do not use it as a source until the overlap check is done.

D. Optional: [ ] 800k GramBeddings rerun as a robustness check only, after A.

E. Writing: **Draft 1 DONE 2026-11-25** (`report/outline.md`, `report/report.tex`, `report/report.pdf`, 10 pages with appendix; tables generated by `scripts/18_make_latex_tables.py` into `report/tables/`, report figure by `scripts/19_report_figures.py`; compile with `cd report && tectonic report.tex`). Still to do before submission: (a) complete reference [5] Rahman et al. (title, first names) and [8] GramBeddings paper (authors, venue, year; the repo README gives only the title "Grambeddings: An End-To-End Neural Model for Phishing URL-Classification Through N-Gram Embeddings" and a ScienceDirect link, not fetched); (b) check the related-work sentences against the papers where readable (Ahamed 0.996-0.998 / 0.73-0.87 / FPR 0.25-0.54, Misiek and Hyla 77.8%, Rashid +0.06 F1 are abstract-level); (c) read the draft end to end and cut or expand to the course page limit (unknown); (d) decide whether to add a limitation line on LLM-assisted work if the course requires disclosure; (e) README updated 2026-11-25 for scripts 10-19, three sources, report and run commands (DONE); (f) commit and push. Original item: [ ] related-work comparison (Ahamed, Misiek and Hyla, Rashid; check against the paper's reference list), verify flagged items in `MD/sota_verified_table.md`, final report by 2026-12-08.

**C1 results (2026-11-25).** `pyarrow==26.0.1` installed (added to requirements.txt). Column-pruned read works through HTTP range requests: about 0.1-0.4 MB per shard instead of 55-400 MB, 56 shards (train and test splits), all 666,315 rows pulled into `data/phreshphish/phreshphish_url_label_date.csv` (url, label, date, split, shard; gitignored with data/). Counts match the dataset card (298,326 phish, 367,989 benign; all URLs unique; dates 2024-07-02 to 2025-12-16). Pull script and range reader live in the scratchpad (not in the repo yet; move into scripts/ if PhreshPhish is used).

Overlap with our sources (share of PhreshPhish rows found in the other source):

| vs | PhreshPhish class | exact URL | registered domain |
|---|---|---|---|
| PhiUSIIL | phish | 0.05% | 55.0% |
| PhiUSIIL | legit | 0.00% | 20.6% |
| GramBeddings | phish | 0.00% | 40.0% |
| GramBeddings | legit | 0.02% | 35.0% |
| PhishTank snapshot | phish | 4.3% | 52.6% |

Reading: URLs are independent (only the PhishTank snapshot overlaps, 4.3%, as expected since PhreshPhish draws on PhishTank). The domain overlap comes from shared hosting platforms: 884 of 63,846 phishing domains account for 164k phishing rows against PhiUSIIL (gitbook.io, webflow.io, pages.dev, google.com, weeblysite.com, vercel.app, weebly.com, github.io; top 20 domains give 75% of those rows). Our `drop_seen` removes target rows by domain, so a run would keep 134,355 phishing and 292,082 legitimate rows after removing PhiUSIIL-trained domains: enough, but it drops the hosting-platform phishing that is common in recent data, so state that caveat.

Form profile (share of rows; PhreshPhish is different from both existing sources again):

| source | class | homepage | https | www | trailing / | median length |
|---|---|---|---|---|---|---|
| PhreshPhish | legit | 0.073 | 0.978 | 0.572 | 0.344 | 55 |
| PhreshPhish | phish | 0.449 | 0.862 | 0.071 | 0.336 | 39 |
| PhiUSIIL | legit | 1.000 | 1.000 | 1.000 | 0.000 | 27 |
| PhiUSIIL | phish | 0.716 | 0.487 | 0.414 | 0.365 | 34 |
| GramBeddings | legit | 0.151 | 0.593 | 0.442 | 0.493 | 41 |
| GramBeddings | phish | 0.119 | 0.468 | 0.139 | 0.307 | 65 |
| PhishTank | phish | 0.365 | 0.911 | 0.042 | 0.329 | 39 |

Go/no-go: PASS on independence (URL level) and on access. Still open: PhreshPhish legit are mostly deep links (92.7%) while its phishing is 44.9% homepage, so the URL-type confound runs the opposite way from PhiUSIIL; it is a useful third target for that reason, but score it with the homepage/deep slices and the no_scheme_no_www feature set, and check the paper's benign-collection description (paper-summary claims remain unverified). Pull script is now `scripts/10_pull_phreshphish.py`; cache builder `scripts/11_build_phreshphish_cache.py` wrote `data/cache/phreshphish.pkl` (100,000 rows, 50,000 per class, seed 0, dup-free, same 25 columns as gram_sample.pkl; 123 rows with empty registered domain, i.e. IP hosts). Script 07 now takes `--variants` and tests each source on every other dataset (PhreshPhish added as target and as a source `PhreshPhish/all`; matched pool unchanged at 11,666 per variant so old and new runs are comparable; PhreshPhish homepage-only source dropped because only about 3,600 legit homepages in the 50k-per-class cache). Single-seed smoke run OK (18 s for LR/RF/HistGB, featset all). Full 5-seed run started 2026-11-25 into `results/transfer_runs_v2.csv` (log `results/transfer_v2.log`; old `transfer_runs.csv` untouched). Caveat found in the smoke run: domain-disjoint splits are lumpy because a few hosting domains (gitbook.io, webflow.io, firebaseapp.com, 000webhostapp.com) hold 2-3% of a pool each; validation phishing share ranged 0.35-0.57 across sources and seeds (PhreshPhish seed 0: val 0.35, test 0.58), so single-seed fixed-threshold numbers are noisy, which is why we average 5 seeds. Next: summarize v2 (script 08 with the new file), then A1-A5 (smoke cache DONE 2026-11-25), thresholds fixed on source validation.

**A1/A2 results (2026-11-25).** A1, form profile (cells that matter; full table in `results/source_profile.csv`):

| source | class | homepage-only: trailing / | homepage-only: www | homepage-only: https | share of class that is homepage |
|---|---|---|---|---|---|
| PhiUSIIL | legit | 0.00 | 1.00 | 1.00 | 1.00 |
| PhiUSIIL | phish | 0.44 | 0.54 | 0.39 | 0.72 |
| GramBeddings | legit | 0.53 | 0.39 | 0.49 | 0.15 |
| GramBeddings | phish | 0.99 | 0.10 | 0.45 | 0.12 |
| PhreshPhish | legit | 1.00 | 0.52 | 0.98 | 0.07 |
| PhreshPhish | phish | 0.66 | 0.07 | 0.83 | 0.45 |
| PhishTank | phish | 0.81 | 0.03 | 0.82 | 0.37 |

Same URL type, different formatting by source and class: homepage legit URLs end in "/" 0% (PhiUSIIL), 53% (GramBeddings), 100% (PhreshPhish); the phishing side shows the same spread (44%, 99%, 66%, 81%). Deep URLs also differ in length (phish median 62 / 69 / 51 / 43; legit 44 / 57 deep in GramBeddings / PhreshPhish).

A2, source discriminator (HistGB, URL-only features, same n per source, domain-disjoint train/test, AUROC mean of 3 seeds; `all` / `no_scheme_no_www` / homepage only):

| class | pair | all | no scheme, no www | homepage only |
|---|---|---|---|---|
| legit | PhiUSIIL vs GramBeddings | 0.993 | 0.988 | 0.961 |
| legit | PhiUSIIL vs PhreshPhish | 1.000 | 1.000 | 1.000 |
| legit | GramBeddings vs PhreshPhish | 0.864 | 0.804 | 0.872 |
| phish | PhiUSIIL vs GramBeddings | 0.920 | 0.909 | 0.892 |
| phish | PhiUSIIL vs PhreshPhish | 0.856 | 0.850 | 0.850 |
| phish | PhiUSIIL vs PhishTank | 0.864 | 0.847 | 0.862 |
| phish | GramBeddings vs PhreshPhish | 0.926 | 0.902 | 0.885 |
| phish | GramBeddings vs PhishTank | 0.904 | 0.867 | 0.856 |
| phish | PhreshPhish vs PhishTank | 0.707 | 0.695 | 0.701 |

Reading: within the same class the source is recoverable from URL-only features (legit PhiUSIIL almost perfectly, even on homepages only and without scheme/www), so the sources differ beyond phishing vs legitimate and a bigger sample of the same source cannot remove that. The closest pair is PhreshPhish vs PhishTank phishing (0.71), consistent with PhreshPhish drawing on PhishTank. Caveats: AUROC measures separability, not which feature drives it (no feature attribution yet); source also correlates with collection period and hosting mix, not only URL style; phishing-pair AUROCs vary by seed (sd up to 0.12 on homepage pairs) because of lumpy domain splits.

**A5 results: what the GramBeddings pages say (read 2026-11-25; https://web.cs.hacettepe.edu.tr/~selman/grambeddings-dataset/, github.com/fcdalgic/GramBeddings and its data/Dataset.md).**
- Stated: 400K phishing and 400K legitimate URLs (800,000 total, balanced by adjusting counts); crawled "in the long term between May 2019 to June 2021" (2.5 years), one collection session per week; legitimate URLs selected with the authors' "custom crawler" plus a manual filter of URLs with "almost identical domain information"; duplicates avoided; the authors criticize datasets whose legitimate samples are mainly homepages and whose phishing comes from PhishTank or OpenPhish over a short window.
- NOT stated on the pages: the phishing feed or verification method, the crawler's seed list (any Alexa/Tranco/ranking list), whether its legitimate URLs are homepages or deep links (our own profile shows 15% homepage), per-class collection dates, any URL preprocessing (scheme/www/slash), any limitations.
- Label convention: Dataset.md says -1 legitimate and 1 phish with tab delimiter; our files use the first comma-separated field with 1 = phish and 2 = legit (classes.txt), parsed in `common.read_gram`. Treat our file as the authority and do not cite Dataset.md for labels.
- Use in the report: cite only the stated items; describe GramBeddings legit/phish provenance as "not documented" where it matters. Because of the 2019-2021 crawl, PhiUSIIL (2022-23, per our notes) and PhreshPhish (2024-25) differ in time period too, which A2 cannot separate from URL style.

**A3/A4 first look (2026-11-25, single seed 0, preliminary).** A3 smoke (LR, canonical URLs vs raw): PhiUSIIL-trained in-source AUROC 0.999 -> 0.870 (its separation leaned on https/www/slash formatting); PhiUSIIL->GramBeddings AUROC 0.779 -> 0.769, PhiUSIIL->PhreshPhish 0.488 -> 0.285; GramBeddings->PhiUSIIL 0.847 -> 0.756; GramBeddings/homepage->PhreshPhish 0.192 -> 0.434; PhreshPhish->PhiUSIIL 0.948 -> 0.659. So canonicalizing does not close the transfer gap; most pairs get worse or stay about equal. SUPERSEDED by the 5-seed results in "A3 and cross-model results" below; do not cite these single-seed numbers. A4 figure (HistGB, seed 0): the PhiUSIIL-trained model puts almost every URL from the other sources at score about 1.0 (legit and phishing alike), so the validation-fixed threshold flags nearly all of them (FPR about 0.86); the GramBeddings-trained models score PhiUSIIL legit URLs near 0 and about 0.5 of PhiUSIIL phishing near 0 as well (recall 0.59), i.e. the opposite failure; PhreshPhish-trained scores almost every PhiUSIIL URL near 1 (legit and phishing) and spreads GramBeddings legit URLs between 0 and 1 with a large mass near 1. Also: matplotlib 3.11.2 added to requirements.txt; fixed a bug in script 07 where an --out name without "runs" made the class-mix file overwrite the results file.

**Transfer v2 (4 sources, 5 seeds, 2026-11-25; `results/transfer_runs_v2.csv`, summary `results/transfer_summary_v2.csv` via `scripts/08_summarize_transfer.py runs.csv summary.csv`).** The three older sources reproduce the earlier `transfer_runs.csv` exactly (max abs diff 1e-6 over 1,125 matched rows). Headline, HistGB, feature set `all`, mean over 5 seeds, threshold fixed at 95% recall on source validation (oracle = FPR at 95% recall if the threshold were chosen on the target, diagnostic only):

| trained on | tested on | AUROC | recall | FPR | oracle FPR |
|---|---|---|---|---|---|
| PhiUSIIL | source test | 1.00 | 0.93 | 0.00 | 0.00 |
| PhiUSIIL | GramBeddings | 0.76 | 0.98 | 0.81 | 0.72 |
| PhiUSIIL | PhreshPhish | 0.67 | 0.88 | 0.73 | 0.96 |
| GramBeddings | source test | 0.94 | 0.94 | 0.29 | 0.32 |
| GramBeddings | PhiUSIIL | 0.83 | 0.53 | 0.00 | 0.84 |
| GramBeddings | PhreshPhish | 0.80 | 0.77 | 0.28 | 0.70 |
| GramBeddings (homepage only) | source test | 0.95 | 0.96 | 0.30 | 0.26 |
| GramBeddings (homepage only) | PhiUSIIL | 0.82 | 0.52 | 0.00 | 0.88 |
| GramBeddings (homepage only) | PhreshPhish | 0.46 | 0.81 | 0.85 | 1.00 |
| PhreshPhish | source test | 0.97 | 0.98 | 0.28 | 0.16 |
| PhreshPhish | PhiUSIIL | 0.49 | 0.97 | 1.00 | 1.00 |
| PhreshPhish | GramBeddings | 0.73 | 0.94 | 0.68 | 0.70 |

Reading: no pair transfers. The threshold's 95% recall holds in-source (0.93-0.98) but target recall ranges 0.52-0.98 and FPR 0.00-1.00. PhiUSIIL-trained and PhreshPhish-trained models flag almost everything on other sources (FPR 0.68-1.00); GramBeddings-trained models miss about half of PhiUSIIL phishing (recall 0.52-0.53 with FPR 0.00). Where target AUROC is about 0.5 (PhreshPhish -> PhiUSIIL 0.49, homepage-trained GramBeddings -> PhreshPhish 0.46) the score has no ranking value at all. Homepage-only training does not help. This is the third independent target the 11/20 feedback pointed to. PhishTank recall (phishing only, so not a detection metric on its own), HistGB feature set `all`: GramBeddings-trained 0.84, homepage-trained 0.84, PhiUSIIL-trained 0.95, PhreshPhish-trained 0.96 (other models 0.68-0.97, NGRAM 0.73-0.95). The headline table rests on HistGB only: check LR, RF, MLP and NGRAM agree (in `transfer_summary_v2.csv`) before stating it as general.

**A3 and cross-model results (2026-11-25; `results/transfer_runs_canon.csv`, comparison table `results/canonical_vs_raw.csv`; 5 seeds, 5 models, feature set `all` for raw and canonical, plus raw `no_scheme_no_www`).**

Cross-source AUROC, mean over the 8 source/other-dataset cells (4 sources x 2 other datasets; in-source and PhishTank excluded), by model:

| model | raw | raw no scheme/www | canonical | canonical minus raw |
|---|---|---|---|---|
| HistGB | 0.694 | 0.651 | 0.667 | -0.027 |
| LR | 0.693 | 0.593 | 0.618 | -0.074 |
| MLP | 0.683 | 0.623 | 0.662 | -0.021 |
| NGRAM | 0.819 | 0.754 | 0.757 | -0.063 |
| RF | 0.651 | 0.607 | 0.665 | +0.014 |

In-source (source test) AUROC, raw -> canonical: HistGB 0.965 -> 0.908, LR 0.949 -> 0.889, MLP 0.965 -> 0.912, NGRAM 0.977 -> 0.942, RF 0.961 -> 0.899. PhiUSIIL-trained HistGB: in-source 0.997 -> 0.847, to PhreshPhish 0.665 -> 0.432.

Reading: removing the formatting (scheme, www, case, trailing slash) lowers in-source accuracy, most for PhiUSIIL (the PhiUSIIL class separation relies on formatting), but does not improve cross-source transfer: mean cross-source AUROC falls for four of five models and is about equal for RF; mean cross-source FPR at the fixed threshold rises (HistGB 0.55 -> 0.74, NGRAM 0.31 -> 0.59). Per pair it is mixed (HistGB: PhreshPhish -> PhiUSIIL 0.49 -> 0.69, PhiUSIIL -> PhreshPhish 0.67 -> 0.43). So formatting is part of the source differences but is not what causes the transfer failure; what remains after canonicalizing (host and path content, topic and brand mix, hosting mix) is not removed by normalizing URLs. Caveat: canonical form also removes legitimate signal (https and www), so it is not a pure "formatting only" control; do not call it that.

Cross-model check of the v2 headline (raw, `all`, 5 seeds; HistGB, LR, MLP, NGRAM, RF): the fixed-threshold pattern agrees across models. GramBeddings-trained models detect only 0.50-0.58 of PhiUSIIL phishing with FPR 0.00-0.02 (homepage-trained 0.52-0.57). PhiUSIIL-trained models give FPR 0.66-0.95 on GramBeddings and 0.40-0.97 on PhreshPhish (NGRAM lowest). PhreshPhish-trained models flag nearly all PhiUSIIL URLs (FPR 0.95-1.00) except NGRAM (0.05). In-source recall is 0.93-0.98 for all models. Pair-level AUROC is NOT stable across models: PhreshPhish -> PhiUSIIL ranges from 0.27 (RF) through 0.49 (HistGB), 0.70 (MLP), 0.94 (LR) to 0.99 (NGRAM), and homepage-trained GramBeddings -> PhreshPhish from 0.19 (MLP) to 0.67 (NGRAM). So the report should lead with the fixed-threshold recall/FPR pattern and state that AUROC at chance or far below it for a given pair is model-dependent. The NGRAM result for PhreshPhish -> PhiUSIIL (AUROC 0.99, FPR 0.05) is a formatting effect, tested: with the scheme and www stripped it becomes AUROC 0.716 / FPR 0.893 (raw no_scheme_no_www) and 0.744 / 0.817 (canonical), so the char n-grams were reading `https://www.` (every PhiUSIIL legit URL has it). This also explains why NGRAM has the highest raw cross-source AUROC (0.819) and loses 0.06 when formatting is removed.

**Coverage audit against proposal, submitted checkpoint and 11/20 feedback (2026-11-25).** Sources re-read from the PDFs. **Re-prioritized after rereading the 11/20 feedback (same day):** the feedback re-scoped the project (transfer study is the main contribution; show results; explain the remaining source and URL-type differences; a larger dataset alone will not resolve them; keep thresholds fixed from source validation). All three asks are covered, so items 1 and 2 below are OPTIONAL, not required; the report should say the combined-source experiment and the 800k rerun were descoped following that feedback. The feedback-aligned gap is item 6 (explanation depth: which features and which URL types drive the source differences), then item 3 to 5 (report content), then item 7 and 8. Original list follows.
NOT covered yet (original order, before re-prioritizing):
1. **OPTIONAL (descoped by the 11/20 feedback). Diversity experiment (proposal Sec 3 and 1; checkpoint Sec 8 "Late Nov").** Proposal: train on PhiUSIIL alone, GramBeddings alone and BOTH COMBINED at matched training size, compare with the char n-gram reference, to test whether diversity helps more than a more sophisticated classifier. Not run. Demoted to secondary after the 11/20 feedback but still promised in two submitted documents: run it (suggested design: leave-one-source-out over PhiUSIIL, GramBeddings, PhreshPhish; train on two pooled at the same total size as one source, threshold fixed on pooled source validation, test on the held-out third source; compare with single-source and n-gram) or state in the report that it was dropped and why.
2. **OPTIONAL (feedback says a larger dataset alone will not resolve the differences). Full 800k GramBeddings** (checkpoint Sec 8 says the diversity experiment uses all 800k rows). Not run; demoted. Run (featurization about 20 s, rerun estimated 30-60 min, not measured) or state the 100k-sample limit (already in report limitations).
3. **Reference-list check (proposal Sec 2, checkpoint Sec 8).** DONE 2026-11-25 by text search of the paper PDF: Ahamed, Misiek, Hyla, Rashid, Seneviratne, GramBeddings, Majestic, Tranco all absent (paper received 2023-06-26, available online 2023-10-20, so the 2024-26 papers cannot be in it). NOT yet stated in the report: add one sentence.
4. **Missing from the report though available in results:** PR-AUC (proposal Sec 4 asks for it; in `transfer_summary_v2.csv`); class and URL-type mix of every train/test set (checkpoint says it is logged; `results/transfer_class_mix_v2.csv`); the fact that training sizes differ (7.7k-8.5k) because domain splits are uneven even though pools match.
5. **Critique points from the paper itself not yet in the report:** Sec 5.7 and Table 8 claim "outperforms state-of-the-art" by comparing accuracy across ten studies that each used a different dataset (3,000 to 100,000 URLs); Sec 5.7 says the diverse dataset "enhances model generalization" but no external test is reported; the paper's own Table 3 batch models (RF 0.99982, XGB 0.99993) beat its incremental framework (0.99239); Sec 5.7 says Table 7 shows a direct correlation between data size and accuracy, while our random-split Table 7 is flat after 60%. Sec 6 (limitations) lists over-training, executable-download URLs and attacks, not cross-source behaviour.
6. **Explanation depth:** no feature attribution for what separates the sources (A2 gives AUROC only); the extra false negatives in the reproduction (447 vs 256) and "drop page content but keep USI is worse" are unexplained; optional edit-distance check of the USI [80,100) band not done; no quantitative side-by-side with Ahamed (0.73-0.87), Misiek and Hyla (77.8%), Rashid (+0.06 F1) beyond citing them.
7. **Placeholders:** references [5] Rahman et al. (title, first names) and [8] GramBeddings paper (authors, venue, year); related-work numbers are abstract-level.
8. **Independent writing.** The proposal and checkpoint both say the final report is "written independently". `report/report.tex` was drafted by Claude, so it should be treated as notes and structure, not as the submission; the final text must be written by the student in their own words, and the course's AI-assistance policy checked before anything derived from the draft is submitted.
Covered: reproduction of Tables 3, 5, 6, 7 with row-order variation and ablations; shortcut vs leakage; 22-feature extractor, matched pools, domain-disjoint splits, validation-fixed thresholds, five seeds, bounded model list, char n-gram reference, scheme/www ablations, URL-type slices, PhishTank recall paired with FPR; third independent source (PhreshPhish) vetted and used; 11/20 feedback points (results shown, source and URL-type differences measured, thresholds fixed from source validation); ROC-AUC and FPR at 95% recall.

**Audit items done later on 2026-11-25.** Item 6 (explanation depth): `scripts/20_source_importance.py` (permutation importance of the source discriminator, HistGB, 3 seeds, within class, for all / homepage / deep URLs; `results/source_importance.csv`, `source_importance_top.csv`). Findings: summed over all pairs and classes, `is_https`, `has_www` and `path_len` carry 82% of the importance on homepage URLs but 32% on deep URLs; on legitimate homepages `path_len` is exactly the trailing slash (checked for all three sources); deep-URL differences fall on `entropy`, `path_depth`, `url_len`, `host_len`, `n_subdomains`, `digit_ratio`. Reading: canonical URLs remove the homepage formatting but not the path/host structure, which fits the canonical result. Caveats: permutation importance splits across correlated features, three seeds, importance for separating sources is not proof of causing a transfer failure. Item 3, 4, 5 (report content): added to the report: reference-list sentence, paper-critique paragraph (Table 8 cross-dataset accuracy, untested generalization claim, Table 7 trend, own batch baselines above the framework), PR-AUC table with phishing shares, class-mix table, training-size range (7,728-8,566), importance paragraph and table; report is now 12 pages. Item 7 (placeholders): both references resolved from Crossref and the dataset PII, not from the papers: [8] Bozkir, Dalgic and Aydos, "GramBeddings: A New Neural Network for URL Based Identification of Phishing Web Pages Through N-gram Embeddings", Computers & Security 124:102964 (2023), doi 10.1016/j.cose.2022.102964 (matched by PII S016740482200356X; the GitHub README uses a different title, "Grambeddings: An End-To-End Neural Model for Phishing URL-Classification Through N-Gram Embeddings"); [5] M. H. Rahman, Z. Abidin, M. A. Hariyadi, "Enhancing Phishing Website Detection Using Artificial Neural Network with Logic Gate-Based Feature Interaction Modeling", G-Tech 10(3):1276-1289, 2026, doi 10.70609/g-tech.v10i3.10280 (matched on journal, volume, issue and pages; content not read by me beyond the earlier full-text read recorded in the sota table). Still open: related-work numbers at abstract level, the final report written independently by the student, optional items 1, 2 and the A1 figure.

Schedule (revised 2026-11-23; dates move if the professor's reply or the data access slips): Nov 23-25 professor message, PhreshPhish read test and overlap check (C1 steps 1-4); Nov 24-28 A1-A5; Nov 29-Dec 1 decide C from the overlap result, run the third-source transfer if approved, regenerate tables (B1); Dec 2-3 figures (B2); Dec 4-7 write and polish; Dec 8 submit. If PhreshPhish is dropped, skip the third-source run and spend that time on A and B.

---

## 4. After the checkpoint (late November to 2026-12-08)

- [ ] Diversity experiment (now secondary, see 3b item C1): train on PhiUSIIL alone, GramBeddings alone, and both combined at matched total size. Compare with the char n-gram reference.
- [ ] Third independent two-class source (open risk). Fallback: domain-disjoint GramBeddings holdout plus the PhishTank recall check. Decide by about 2026-11-15 whether a third source is realistic. CIC Trap4Phish has no URLs; its "Source Files > QR Codes" folder is uninspected.
- [ ] Compare against related work: Ahamed 2026 (cross-source accuracy 0.73-0.87), Misiek and Hyla 2026 (77.8% average), Rashid 2024 (about +0.06 F1 from domain adaptation). Confirm none of them is in the target paper's reference list.
- [ ] Verify the flagged items in `MD/sota_verified_table.md` (Frontiers Table 12 by hand, PhiUSIIL abstract numbers).
- [ ] Final report, written independently, by 2026-12-08.

---

## 5. Open questions and risks

- ~~Whether the similarity index uses labels~~ Resolved: no labels, but legit URLs come from the same list it matches against (3.0). Still unverified: the paper's Table 3 split and Sec 5.7 discussion; the paper's feature list was not read in detail.
- Third two-class source not secured.
- Matching class mix and URL type may shrink the usable PhiUSIIL set a lot, since its legit URLs are all bare homepages.
- Domain-disjoint filtering removes large chunks of PhishTank (about 15k unique domains over 76k URLs).
- MLP runtime on a 100k-row sample is fine on CPU, but incremental `partial_fit` runs multiply cost by seeds.

## 6. Suggested schedule to 2026-11-10

| Dates | Work |
|---|---|
| Oct 24-Nov 1 | DONE: read the paper, recorded published numbers, shortcut check (3.0, 3.2) |
| Nov 1 | DONE: Tables 5-7 reproduction, file order, seed 0 (3.1) |
| Nov 1 | DONE: shuffled-order seeds 1-4 for Tables 5-6 |
| Nov 2-3 | Part A leftovers: Table 3 baselines, rerun without USI and page content, check paper feature count |
| Nov 1 | DONE: Part B first full run (script 07, 5 seeds, 4 models) |
| Nov 1 | DONE: char n-gram model and scheme-free ablation in Part B |
| Nov 1 | DONE: reproduction rerun without USI / page content (script 05 `--drop`) |
| Nov 1 | DONE: Table 3 baselines (script 09, 5 seeds, two feature sets) |
| Nov 1 | DONE: `no_scheme_no_www` ablation |
| Nov 2-5 | Checkpoint write-up review |
| Nov 7-9 | Tables, write-up, update the log |
| Nov 10 | Checkpoint |
