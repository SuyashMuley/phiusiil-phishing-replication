"""Reproduce the PhiUSIIL paper's protocol (Prasad and Chandra 2024, Computers & Security 136) on the released data.

Paper protocol (Sec 4.2.2, Algorithm 3), paper label convention kept: label 1 = legitimate (positive), 0 = phishing.
  - Features: importance > 0 in an ensemble of tree models, then the top 85% by mutual information.
  - Models: BernoulliNB, PassiveAggressive, SGDClassifier with the paper's tuned hyperparameters.
  - Prequential run: partial_fit on the first record, then for each later record predict, then partial_fit on it.
  - Votes: predict = number of models voting legit. Low: >=1, Best: >=2, High: ==3.
  - Table 5 / 6: metrics over all records after the first. Table 7: classical pre-training on p% of the records,
    then the prequential run on the rest; metrics are on the incremental part (assumption: paper does not say).

Deviations from the paper (state them in the report): LightGBM and XGBoost are not installed, so sklearn
GradientBoosting and ExtraTrees stand in for the importance ensemble; mutual information is estimated on a
random 30k-row subsample; features are not scaled (the paper mentions no scaling); the paper's rows are in
released-file order, which we use by default.

Usage (run from the project folder):
  .venv/bin/python scripts/05_reproduce_phiusiil.py                       # Tables 5 and 6, file order
  .venv/bin/python scripts/05_reproduce_phiusiil.py --order shuffle --seed 1
  .venv/bin/python scripts/05_reproduce_phiusiil.py --table7 sequential   # also Table 7 (or: random)
  .venv/bin/python scripts/05_reproduce_phiusiil.py --max-rows 20000      # smoke test
Outputs: results/repro_*.csv
"""
import argparse
import os
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesClassifier, GradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_selection import mutual_info_classif
from sklearn.linear_model import PassiveAggressiveClassifier, SGDClassifier
from sklearn.naive_bayes import BernoulliNB
from sklearn.tree import DecisionTreeClassifier

# PassiveAggressiveClassifier is deprecated in sklearn 1.8 but is what the paper used; keep it for fidelity
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message="Maximum number of iteration")

ap = argparse.ArgumentParser()
ap.add_argument("--order", choices=["file", "shuffle"], default="file")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--max-rows", type=int, default=0)
ap.add_argument("--drop", default="", help="comma list of feature groups to remove before selection: usi, page, derived")
ap.add_argument("--table7", choices=["sequential", "random"], default=None)
args = ap.parse_args()
os.makedirs("results", exist_ok=True)
tag = (f"{args.order}_s{args.seed}" + (f"_drop-{args.drop.replace(',', '+')}" if args.drop else "")
       + (f"_n{args.max_rows}" if args.max_rows else ""))

PAPER_T5 = {  # Table 5: accuracy, precision, sensitivity, F1, MCC
    "LowSecurity": (0.88258, 0.82966, 0.99999, 0.90690, 0.77595),
    "BestSecurity": (0.99239, 0.98870, 0.99810, 0.99338, 0.98449),
    "HighSecurity": (0.97409, 0.99979, 0.95490, 0.97683, 0.94877),
}
PAPER_T6 = {  # Table 6: TP, TN, FP, FN (legit = positive)
    "LowSecurity": (134849, 73259, 27686, 1),
    "BestSecurity": (134594, 99406, 1539, 256),
    "HighSecurity": (128768, 100918, 27, 6082),
}
PAPER_T7 = {0.1: 0.99573, 0.2: 0.99593, 0.3: 0.99637, 0.4: 0.99708, 0.5: 0.99725,
            0.6: 0.99751, 0.7: 0.99755, 0.8: 0.99763, 0.9: 0.99792}  # accuracy column of Table 7


def make_models():
    return {
        "BernoulliNB": BernoulliNB(alpha=0.01, binarize=0.0, class_prior=None, fit_prior=False, force_alpha=True),
        "PassiveAggressive": PassiveAggressiveClassifier(C=5, fit_intercept=False, n_iter_no_change=50, n_jobs=10,
                                                         shuffle=True, random_state=args.seed),
        "SGDClassifier": SGDClassifier(alpha=0.01, eta0=100, n_iter_no_change=50, n_jobs=1, random_state=args.seed),
    }


def select_features(X, y, names):
    """Paper: importance > 0 in an ensemble of tree models, then top 85% by mutual information."""
    rng = np.random.RandomState(args.seed)
    sub = rng.choice(len(X), size=min(len(X), 50_000), replace=False)
    imps = []
    for m in (RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=args.seed),
              DecisionTreeClassifier(random_state=args.seed),
              GradientBoostingClassifier(n_estimators=50, random_state=args.seed),
              ExtraTreesClassifier(n_estimators=100, n_jobs=-1, random_state=args.seed)):
        imps.append(m.fit(X[sub], y[sub]).feature_importances_)
    imp = np.mean(imps, axis=0)
    keep = np.where(imp > 0)[0]
    mi_sub = rng.choice(len(X), size=min(len(X), 30_000), replace=False)
    mi = mutual_info_classif(X[mi_sub][:, keep], y[mi_sub], random_state=args.seed)
    top = keep[np.argsort(-mi)[: int(np.ceil(0.85 * len(keep)))]]
    return sorted(top), pd.DataFrame({"feature": names, "mean_importance": imp,
                                      "kept_importance": np.isin(np.arange(len(names)), keep),
                                      "kept_final": np.isin(np.arange(len(names)), top)})


def prequential(X, y, init_idx, run_idx, classical=False):
    """Pre-train on init_idx (one record = paper's init; many = classical fit), then predict-then-partial_fit run_idx.
    Returns the per-record legit-vote count (0..3) for run_idx, in order."""
    models = make_models()
    for m in models.values():
        if classical:
            m.fit(X[init_idx], y[init_idx])
        else:
            m.partial_fit(X[init_idx], y[init_idx], classes=[0, 1])
    votes = np.zeros(len(run_idx), dtype=np.int8)
    t0 = time.time()
    for k, i in enumerate(run_idx):
        xi, yi = X[i:i + 1], y[i:i + 1]
        v = 0
        for m in models.values():
            v += int(m.predict(xi)[0])
            m.partial_fit(xi, yi)
        votes[k] = v
        if (k + 1) % 20_000 == 0:
            print(f"  {k + 1}/{len(run_idx)} records, {time.time() - t0:.0f}s", flush=True)
    return votes


def profile_metrics(y_true, votes):
    out = {}
    for name, need in (("LowSecurity", 1), ("BestSecurity", 2), ("HighSecurity", 3)):
        pred = (votes >= need).astype(int)
        tp = int(((y_true == 1) & (pred == 1)).sum())
        tn = int(((y_true == 0) & (pred == 0)).sum())
        fp = int(((y_true == 0) & (pred == 1)).sum())  # phishing called legit (paper Table 6 FP)
        fn = int(((y_true == 1) & (pred == 0)).sum())  # legit called phishing (paper Table 6 FN)
        prec = tp / (tp + fp) if tp + fp else float("nan")
        rec = tp / (tp + fn) if tp + fn else float("nan")
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else float("nan")
        denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
        mcc = (tp * tn - fp * fn) / denom if denom else float("nan")
        out[name] = dict(accuracy=(tp + tn) / len(y_true), precision=prec, sensitivity=rec, f1=f1, mcc=mcc,
                         TP=tp, TN=tn, FP=fp, FN=fn)
    return out


df = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", encoding="utf-8-sig")
if args.max_rows:
    df = df.iloc[: args.max_rows]
if args.order == "shuffle":
    df = df.sample(frac=1, random_state=args.seed).reset_index(drop=True)
drop = ["FILENAME", "URL", "Domain", "TLD", "Title", "label"]
names = [c for c in df.columns if c not in drop]
# Feature groups (same split as scripts/06_shortcut_ablation.py): USI, URL-derived probabilities, page content
GROUPS = {"usi": ["URLSimilarityIndex"], "derived": ["CharContinuationRate", "TLDLegitimateProb", "URLCharProb"]}
URL_COLS = {"URLLength", "DomainLength", "IsDomainIP", "TLDLength", "NoOfSubDomain", "HasObfuscation", "NoOfObfuscatedChar",
            "ObfuscationRatio", "NoOfLettersInURL", "LetterRatioInURL", "NoOfDegitsInURL", "DegitRatioInURL",
            "NoOfEqualsInURL", "NoOfQMarkInURL", "NoOfAmpersandInURL", "NoOfOtherSpecialCharsInURL",
            "SpacialCharRatioInURL", "IsHTTPS"}
GROUPS["page"] = [c for c in names if c not in URL_COLS | set(GROUPS["usi"]) | set(GROUPS["derived"])]
removed = sorted({c for g in filter(None, args.drop.split(",")) for c in GROUPS[g]})
names = [c for c in names if c not in removed]
X_all = df[names].to_numpy(dtype=np.float64)
y = df["label"].to_numpy()  # 1 = legit, as in the paper
print(f"dropped groups [{args.drop}]: {len(removed)} columns removed")
print(f"rows {len(df)}, candidate features {len(names)}, legit share {y.mean():.3f}, order {args.order}", flush=True)

sel, fs = select_features(X_all, y, names)
fs.to_csv(f"results/repro_features_{tag}.csv", index=False)
print(f"selected {len(sel)} of {len(names)} features; URLSimilarityIndex kept: "
      f"{'URLSimilarityIndex' in [names[i] for i in sel]}", flush=True)
X = X_all[:, sel]

# ---- Tables 5 and 6
print("Prequential run (Tables 5 and 6)", flush=True)
votes = prequential(X, y, np.array([0]), np.arange(1, len(y)))
res = profile_metrics(y[1:], votes)
rows5, rows6 = [], []
for prof, r in res.items():
    pa = PAPER_T5[prof]
    pt = PAPER_T6[prof]
    rows5.append(dict(profile=prof, **{k: r[k] for k in ("accuracy", "precision", "sensitivity", "f1", "mcc")},
                      **{f"paper_{k}": v for k, v in zip(("accuracy", "precision", "sensitivity", "f1", "mcc"), pa)}))
    rows6.append(dict(profile=prof, TP=r["TP"], TN=r["TN"], FP=r["FP"], FN=r["FN"],
                      paper_TP=pt[0], paper_TN=pt[1], paper_FP=pt[2], paper_FN=pt[3]))
t5, t6 = pd.DataFrame(rows5), pd.DataFrame(rows6)
t5.to_csv(f"results/repro_table5_{tag}.csv", index=False)
t6.to_csv(f"results/repro_table6_{tag}.csv", index=False)
print("\nTable 5 (ours vs paper_)\n", t5.round(5).to_string(index=False))
print("\nTable 6 (ours vs paper_; legit = positive)\n", t6.to_string(index=False), flush=True)

# ---- Table 7
if args.table7:
    print(f"\nTable 7, pre-train split = {args.table7}", flush=True)
    rng = np.random.RandomState(args.seed)
    rows7 = []
    for p in sorted(PAPER_T7):
        n_pre = int(round(p * len(y)))
        if args.table7 == "sequential":
            pre, run = np.arange(n_pre), np.arange(n_pre, len(y))
        else:
            perm = rng.permutation(len(y))
            pre, run = np.sort(perm[:n_pre]), np.sort(perm[n_pre:])
        v = prequential(X, y, pre, run, classical=True)
        r = profile_metrics(y[run], v)["BestSecurity"]
        rows7.append(dict(pretrain=p, n_pre=n_pre, n_run=len(run), **{k: r[k] for k in ("accuracy", "precision", "sensitivity", "f1", "mcc")},
                          paper_accuracy=PAPER_T7[p]))
        print(f"  {p:.1f}: acc {r['accuracy']:.5f} (paper {PAPER_T7[p]:.5f})", flush=True)
    pd.DataFrame(rows7).to_csv(f"results/repro_table7_{args.table7}_{tag}.csv", index=False)
