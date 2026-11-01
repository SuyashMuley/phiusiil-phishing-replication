# ML Project Feasibility Plan
## Cross-Dataset Generalization in Phishing URL Detection

### Project Goal
Evaluate how well phishing URL classifiers generalize across independently collected datasets, and determine whether simple techniques such as feature selection, regularization, removal of unstable features, and multi-source training can improve cross-dataset performance.

---

## 1. Datasets

Use three independent datasets that contain raw URLs and labels.

### Dataset A: PhiUSIIL
- Source: https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset
- Approximate size: 235,795 URLs
- Contains raw URLs: Yes
- Contains both legitimate and phishing examples: Yes
- Also contains engineered features
- Main use:
  - Primary dataset
  - Same-dataset baseline
  - Cross-dataset training/testing

### Dataset B: GramBeddings
- Source: https://web.cs.hacettepe.edu.tr/~selman/grambeddings-dataset/
- Approximate size: ~800K URLs
- Contains raw URLs: Yes
- Contains both legitimate and phishing examples: Yes
- Main use:
  - Independent cross-dataset benchmark

### Dataset C: CIC-Trap4Phish
- Source: https://www.unb.ca/cic/datasets/trap4phish2025.html
- URL strings subset only
- Approximate size: >1M URLs
- Contains raw URLs: Yes
- Contains both benign and malicious examples: Yes
- Main use:
  - Modern unseen test dataset
  - Multi-source training experiments

---

# Phase 1: Establish Data Feasibility

## Task 1: Download and Load All Datasets

For each dataset:

- [ ] Download successfully
- [ ] Load into Python/Pandas
- [ ] Identify the URL column
- [ ] Identify the label column
- [ ] Map labels to a common convention:
  - `0 = legitimate`
  - `1 = phishing`
- [ ] Count total examples
- [ ] Count phishing examples
- [ ] Count legitimate examples
- [ ] Check for missing URLs
- [ ] Check for duplicate URLs

Create a summary table:

| Dataset | Total | Legitimate | Phishing | Duplicate URLs | Missing URLs |
|---|---:|---:|---:|---:|---:|
| PhiUSIIL | | | | | |
| GramBeddings | | | | | |
| Trap4Phish | | | | | |

---

# Phase 2: Check Dataset Leakage

## Task 2: Exact URL Overlap

For each pair:

- [ ] PhiUSIIL vs GramBeddings
- [ ] PhiUSIIL vs Trap4Phish
- [ ] GramBeddings vs Trap4Phish

Compute:

```python
overlap = len(set(urls_a) & set(urls_b))
```

Also compute an overlap percentage:

```text
overlap_percentage =
intersection_size / min(size_A, size_B)
```

Record:

| Dataset Pair | Exact URL Overlap | % Overlap |
|---|---:|---:|
| PhiUSIIL ↔ GramBeddings | | |
| PhiUSIIL ↔ Trap4Phish | | |
| GramBeddings ↔ Trap4Phish | | |

---

## Task 3: Domain-Level Overlap

Extract the registered/root domain from every URL.

Example:

```text
https://login.example.com/account?id=1
→ example.com
```

Measure domain overlap between datasets.

Record:

| Dataset Pair | Domain Overlap | % Overlap |
|---|---:|---:|
| PhiUSIIL ↔ GramBeddings | | |
| PhiUSIIL ↔ Trap4Phish | | |
| GramBeddings ↔ Trap4Phish | | |

### Important
For strict cross-dataset experiments, remove URLs or domains from the test dataset that already appear in the training dataset.

---

# Phase 3: Build a Common URL Feature Extractor

## Task 4: Implement One Feature Function

All datasets must use exactly the same feature representation.

Implement:

```python
extract_features(url)
```

Suggested URL-only features:

### Length-Based Features
- [ ] URL length
- [ ] Hostname length
- [ ] Path length
- [ ] Query length

### Character-Based Features
- [ ] Number of dots
- [ ] Number of hyphens
- [ ] Number of digits
- [ ] Digit ratio
- [ ] Number of special characters
- [ ] Number of `@` symbols
- [ ] Number of `%` symbols
- [ ] Number of `=` symbols
- [ ] Number of query parameters

### Structural Features
- [ ] Number of subdomains
- [ ] Uses HTTPS
- [ ] Contains an IP address instead of a domain
- [ ] Port explicitly specified
- [ ] URL entropy

### Suspicious Token Features
Count words such as:

```text
login
verify
account
secure
update
signin
password
bank
confirm
support
```

Possible feature:

```python
suspicious_token_count
```

### Validation
Run the same extractor on sample URLs from all three datasets.

- [ ] PhiUSIIL works
- [ ] GramBeddings works
- [ ] Trap4Phish works
- [ ] No dataset-specific features are required

---

# Phase 4: Build the Minimum Baseline

For feasibility, start with:

1. XGBoost
2. Logistic Regression

Do not start with every model.

For faster initial testing, sample balanced subsets such as:

```text
25,000 phishing
25,000 legitimate
```

from each dataset.

---

## Task 5: Same-Dataset Baseline

Start with PhiUSIIL.

Split:

```text
80% training
20% testing
```

Train XGBoost.

Measure:

- [ ] Accuracy
- [ ] Precision
- [ ] Recall
- [ ] F1
- [ ] ROC-AUC

Record:

| Train | Test | Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---:|---:|---:|---:|---:|
| PhiUSIIL | PhiUSIIL | XGBoost | | | | | |
| PhiUSIIL | PhiUSIIL | Logistic Regression | | | | | |

---

# Phase 5: Cross-Dataset Baseline

## Task 6: Train on PhiUSIIL, Test Elsewhere

Without retraining:

```text
Train: PhiUSIIL
Test: GramBeddings
```

and

```text
Train: PhiUSIIL
Test: Trap4Phish
```

Measure the same metrics.

Record:

| Train | Test | Model | Accuracy | Precision | Recall | F1 | ROC-AUC |
|---|---|---|---:|---:|---:|---:|---:|
| PhiUSIIL | GramBeddings | XGBoost | | | | | |
| PhiUSIIL | Trap4Phish | XGBoost | | | | | |

---

## Task 7: Compute the Generalization Gap

Define:

```text
Generalization Gap =
Within-Dataset F1 - Cross-Dataset F1
```

Example:

```text
Within-dataset F1 = 0.97
Cross-dataset F1  = 0.78

Gap = 0.19
```

Record:

| Train Dataset | Test Dataset | Within F1 | Cross F1 | Generalization Gap |
|---|---|---:|---:|---:|
| PhiUSIIL | GramBeddings | | | |
| PhiUSIIL | Trap4Phish | | | |

If a clear gap exists, the main project premise is established.

---

# Phase 6: Expand the Cross-Dataset Matrix

If the minimum baseline works, run more directions.

Suggested matrix:

| Train ↓ / Test → | PhiUSIIL | GramBeddings | Trap4Phish |
|---|---:|---:|---:|
| PhiUSIIL | | | |
| GramBeddings | | | |
| Trap4Phish | | | |

Run at least:

- [ ] PhiUSIIL → GramBeddings
- [ ] PhiUSIIL → Trap4Phish
- [ ] GramBeddings → PhiUSIIL
- [ ] GramBeddings → Trap4Phish

Optional:

- [ ] Trap4Phish → PhiUSIIL
- [ ] Trap4Phish → GramBeddings

---

# Phase 7: Compare Multiple Models

Once feasibility is confirmed, compare:

- [ ] Logistic Regression
- [ ] Random Forest
- [ ] XGBoost
- [ ] SVM
- [ ] Optional: MLP

Important:

The research question is **not simply which model has the best accuracy**.

The important comparison is:

```text
How much does each model degrade under dataset shift?
```

---

# Phase 8: Analyze Why Generalization Fails

## Task 8: Compare Feature Distributions

For important features, compare distributions across datasets.

Examples:

- URL length
- hostname length
- number of subdomains
- digit ratio
- entropy
- suspicious token count

Possible analysis:

- [ ] Histograms
- [ ] Box plots
- [ ] Mean / standard deviation
- [ ] KS test
- [ ] PCA visualization

Question:

```text
Are features that are predictive in Dataset A distributed differently in Dataset B?
```

---

## Task 9: Feature Importance

Use:

- [ ] XGBoost feature importance
- [ ] Permutation importance
- [ ] Mutual information
- [ ] Optional: SHAP

Compare:

```text
Important features on Dataset A
vs.
Important features on Dataset B
```

Identify features that appear dataset-specific.

---

# Phase 9: Improve Cross-Dataset Generalization

After establishing the baseline, test improvements one at a time.

## Experiment A: Feature Selection

Try:

```text
All features
Top 15
Top 10
Top 5
```

Measure same-dataset and cross-dataset F1.

---

## Experiment B: Remove Unstable Features

Identify features whose distributions differ strongly between datasets.

Compare:

```text
Baseline feature set
vs.
Feature set without unstable features
```

---

## Experiment C: Regularization

For Logistic Regression:

- [ ] L1
- [ ] L2
- [ ] Different values of C

Measure whether stronger regularization improves transfer.

---

## Experiment D: Multi-Source Training

This is one of the strongest project experiments.

Compare:

```text
Train(A) → Test(C)
```

against:

```text
Train(B) → Test(C)
```

against:

```text
Train(A + B) → Test(C)
```

Example:

```text
PhiUSIIL → Trap4Phish
GramBeddings → Trap4Phish
PhiUSIIL + GramBeddings → Trap4Phish
```

Research question:

> Does training-data diversity improve cross-dataset generalization more than simply increasing model complexity?

---

# Published Baselines / External Ground Truth

## Rashid et al. — Computer Networks, 2024

Paper:

https://doi.org/10.1016/j.comnet.2024.110398

Main observation:

```text
Same-dataset F1 ≈ 0.98–1.00
Cross-dataset F1 can drop to ≈ 0.67–0.94
```

Unsupervised domain adaptation improves F1 by roughly:

```text
+0.06 average
```

with larger gains in some dataset combinations.

Use this as a conceptual cross-dataset reference.

---

## Misiek & Hyla — IEEE Access, 2026

Paper:

https://doi.org/10.1109/ACCESS.2026.3672690

Modern classical-ML reference using XGBoost.

Reported approximate cross-dataset average:

```text
Accuracy ≈ 77.84%
F1       ≈ 77.93%
```

Use this as a strong practical baseline.

---

# Minimum Work Needed Before Proposal

You do **not** need to finish the full project before the proposal.

Complete the following:

- [ ] Download PhiUSIIL
- [ ] Download GramBeddings
- [ ] Download CIC-Trap4Phish URL dataset
- [ ] Verify URL and label columns
- [ ] Produce dataset summary statistics
- [ ] Check exact URL overlap
- [ ] Check domain overlap
- [ ] Implement common URL feature extractor
- [ ] Train XGBoost on PhiUSIIL
- [ ] Evaluate XGBoost on held-out PhiUSIIL
- [ ] Evaluate the same model on GramBeddings OR Trap4Phish
- [ ] Compute the generalization gap
- [ ] Compare the observed result with published cross-dataset baselines

---

# Feasibility Success Criteria

The project is feasible if you can truthfully state:

> I downloaded multiple independent labeled URL datasets, verified access to raw URLs and labels, implemented a common URL-only feature extraction pipeline, checked cross-dataset overlap, and successfully trained a baseline model on one dataset and evaluated it both within-dataset and on an independent dataset.

A large cross-dataset performance drop is **not required** for feasibility.

If there is little or no drop, that itself becomes an interesting result that should be investigated.

---

# Proposed Final Research Question

> **How well do classical phishing URL classifiers generalize across independently collected datasets, and can feature stability, regularization, or multi-source training improve performance under dataset shift?**

---

# Possible Project Title

**Cross-Dataset Generalization in Phishing URL Detection: Evaluating and Improving Classical ML Under Dataset Shift**

---

# Suggested Implementation Order

1. Download datasets
2. Inspect labels and raw URLs
3. Check duplicates and overlap
4. Build common feature extractor
5. Run XGBoost within-dataset baseline
6. Run first cross-dataset test
7. Compute generalization gap
8. Add Logistic Regression and Random Forest
9. Build full train-test dataset matrix
10. Analyze feature distributions
11. Test feature selection
12. Test removal of unstable features
13. Test regularization
14. Test multi-source training
15. Compare against published baselines
16. Generate final plots/tables
