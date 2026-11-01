# Establishing SOTA: Phishing URL Classifier Generalization

**Project:** How well do phishing URL classifiers generalize beyond the dataset they are trained on?
**Primary dataset:** PhiUSIIL ([UCI #967](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset))
**Original paper:** Prasad & Chandra, *Computers & Security* ([doi:10.1016/j.cose.2023.103545](https://doi.org/10.1016/j.cose.2023.103545))

---

## Background notes

- **Label leak in PhiUSIIL.** `URLSimilarityIndex` is exactly 100 for every legitimate URL. The single rule `URLSimilarityIndex < 100 → phishing` gets about 99.7% accuracy. `NoOfExternalRef` and `LineOfCode` each exceed 95% on their own.
- **Source artifact.** Legitimate URLs are mostly bare homepages from top-site lists. Phishing URLs tend to have long paths. Length, HTTPS, and `www` alone separate the classes well.
- **Closest prior work.** Frontiers in Computer Science (Aug 2026), "An integrated evaluation protocol for adversarial robustness, generalization, and explanation stability in URL-based phishing detection" ([doi:10.3389/fcomp.2026.1834407](https://doi.org/10.3389/fcomp.2026.1834407)).
  - Models: LR, XGBoost, CharCNN, BERT-base on PhiUSIIL, plus PhishTank for external validation.
  - Host-disjoint test accuracy: 0.996–0.998.
  - Fully independent sources (PhishTank phishing + Majestic Million benign): accuracy 0.73–0.87, FPR 0.25–0.54.
- **Label convention.** PhiUSIIL uses `1 = legitimate`, `0 = phishing`. Invert this before merging with other sources.

---

## Phase 1: Literature survey (~1 week)

- [ ] **1. Read recent surveys.** Search Google Scholar, Semantic Scholar, and arXiv for "phishing URL detection survey" from 2024–2026.
- [ ] **2. Build a comparison table of 10–20 key papers** (template below). This is the main deliverable of the SOTA step.
- [ ] **3. Cover each model family:**
  - Classical: RF, XGBoost on engineered features
  - Character-level deep: URLNet, CharCNN
  - Transformers: urlBERT, fine-tuned BERT/DistilBERT
  - Reference-based / visual: Phishpedia, PhishIntention
  - LLM-based: KnowPhish, PhishLLM, zero-shot LLM evaluations
  - *(Names recalled from memory. Verify each paper and its results.)*
- [ ] **4. Collect evaluation-methodology papers:**
  - Frontiers 2026 paper (above)
  - Sabir et al. (2022), adversarial robustness of ML phishing URL detectors
  - Arp et al. (2022), "Dos and Don'ts of Machine Learning in Computer Security"
- [ ] **5. Write down what "SOTA" means for this project.** Proposed definition: *best URL-only model under cross-source and temporal evaluation*, not highest accuracy on PhiUSIIL.

### Comparison table template

| Paper | Year | Dataset(s) | Input (URL / HTML / screenshot) | Model | Split type | Metrics | Reported score | External test? |
|---|---|---|---|---|---|---|---|---|
| Prasad & Chandra | 2024 | PhiUSIIL | URL + HTML | Incremental learning | Random | Accuracy | ~99.2% | No |
| Frontiers (Ahamed et al.) | 2026 | PhiUSIIL + PhishTank + Majestic | URL | LR, XGB, CharCNN, BERT | Host-disjoint + cross-source | Acc, AUROC, AUPRC, FPR | 0.996–0.998 in-dist; 0.73–0.87 cross-source | Yes |
| | | | | | | | | |

---

## Phase 2: Fix the evaluation protocol (before training)

- [ ] **6. Define splits:**
  - Random split (only to reproduce the paper)
  - eTLD+1-disjoint split (stricter than host-disjoint)
  - Cross-source test (independent sources for **both** classes)
  - Temporal test (train on 2023 PhiUSIIL, test on fresh 2026 phishing URLs)
- [ ] **7. Pick metrics:** AUROC, PR-AUC, F1, and FPR at fixed recall (e.g., 95%).
- [ ] **8. Prepare external data:**
  - Phishing: PhishTank, OpenPhish
  - Benign: Tranco or Majestic Million, ideally including deep links, not only homepages
  - Deduplicate against PhiUSIIL
  - Apply the same URL normalization to every source

---

## Phase 3: Run reference baselines

- [ ] **9. Trivial baselines:** the single-rule `URLSimilarityIndex` classifier and a majority-class classifier.
- [ ] **10. Reproduce the paper:** full engineered features, random split. Confirm ~99%.
- [ ] **11. Strong URL-only baselines** under the fair protocol:
  - XGBoost on character n-gram TF-IDF (3–5 grams)
  - CharCNN
  - Fine-tuned small transformer (DistilBERT, or urlBERT if weights are available)
- [ ] **12. Zero-shot LLM baseline:** prompt an LLM with the raw URL on 1–2k URLs from the cross-source test set.
- [ ] **13. Report the gaps:** every model on every split, side by side.

### Results table template

| Model | Features | Random split | eTLD+1-disjoint | Cross-source | Temporal (2026) |
|---|---|---|---|---|---|
| Majority class | n/a | | | | |
| URLSimilarityIndex rule | 1 feature | | | | |
| LR | | | | | |
| Random Forest | | | | | |
| XGBoost | | | | | |
| SVM | | | | | |
| CharCNN | Raw URL | | | | |
| DistilBERT / urlBERT | Raw URL | | | | |
| Zero-shot LLM | Raw URL | n/a | | | |

*(Report AUROC, PR-AUC, and FPR@95% recall in each cell, or use one table per metric.)*

---

## Phase 4: Sanity checks

- [ ] **14. Compare with the literature.** Domain-disjoint in-distribution results should be roughly 0.996–0.998 and cross-source roughly 0.73–0.87 accuracy. If yours are far off, check the pipeline for bugs first.
- [ ] **15. Run SHAP or feature importance** on the best model to make sure it isn't relying on a new shortcut, such as HTTPS or the `www` prefix.

---

## Priorities if time is short

1. Comparison table (step 2)
2. Trivial baselines (step 9)
3. Strong URL-only baselines (step 11)
4. Gap report (step 13)
5. *Most novel extra:* zero-shot LLM baseline (step 12)

## Possible contributions beyond prior work

- **Temporal drift:** 2023-trained models tested on 2026 phishing feeds.
- **Better benign set:** deep, non-homepage benign URLs, to test whether the homepage artifact explains the cross-source drop.
- **LLM reference baseline:** a zero-shot model not trained on PhiUSIIL's artifacts.
- **Stricter splits:** eTLD+1-disjoint rather than host-disjoint.

## Practical warnings

- Phishing pages go offline within days, so HTML features can't be recomputed for new URLs. Stick to URL-only features for cross-dataset tests.
- Public phishing feeds overlap heavily with each other and with PhiUSIIL. Deduplicate.
- Verify any paper or number produced by an LLM (including this plan) against the original source.
