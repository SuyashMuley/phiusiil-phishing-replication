"""Paper Table 3 baselines (batch models) on a held-out split, kept separate from the prequential run in script 05.

The paper (Table 3) does not state its split, so we use a stratified random 80/20 split per seed. Paper label
convention: label 1 = legitimate (positive). Feature sets:
  selected : the features kept by script 05's selection (results/repro_features_file_s0.csv)
  url_only : the 21 URL-derived columns (no URLSimilarityIndex, no page content)
Substitutions (state in the report): sklearn HistGradientBoosting stands in for LightGBM/XGBoost/CatBoost (not installed);
VotingClassifier and Stacking are not run; MLP is added (not in the paper). LR, KNN and MLP get standardized inputs;
the NB, PassiveAggressive, Perceptron and SGD models run on raw features, as in script 05.
Usage (from the project folder): one process per seed, then merge.
  nice .venv/bin/python scripts/09_table3_baselines.py --seed 0
  .venv/bin/python scripts/09_table3_baselines.py --summarize
"""
import argparse
import glob
import os
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import (AdaBoostClassifier, BaggingClassifier, GradientBoostingClassifier,
                              HistGradientBoostingClassifier, RandomForestClassifier)
from sklearn.linear_model import LogisticRegression, PassiveAggressiveClassifier, Perceptron, SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

warnings.filterwarnings("ignore")
ap = argparse.ArgumentParser()
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--max-rows", type=int, default=0)
ap.add_argument("--summarize", action="store_true")
args = ap.parse_args()
os.makedirs("results", exist_ok=True)

PAPER = {  # Table 3: (accuracy, F1)
    "BernoulliNB": (0.98644, 0.98826), "PassiveAggressive": (0.98021, 0.98291), "SGD": (0.94294, 0.95236),
    "MultinomialNB": (0.68961, 0.78253), "Perceptron": (0.98041, 0.98309), "AdaBoost": (0.99981, 0.99983),
    "GradientBoosting": (0.99978, 0.99981), "KNN": (0.99378, 0.99456), "RF": (0.99982, 0.99984),
    "DT": (0.99866, 0.99883), "LR": (0.99654, 0.99698), "Bagging": (0.99923, 0.99932),
    "HistGB": (0.9999, 0.99992),  # paper's LightGBM row, as the closest stand-in
}

if args.summarize:
    r = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("results/table3_seed*.csv"))])
    rows = []
    for (fs, m), g in r.groupby(["featset", "model"], sort=False):
        rows.append(dict(featset=fs, model=m, n_seeds=g.seed.nunique(),
                         **{k: f"{g[k].mean():.5f} ({g[k].std():.5f})" for k in ("accuracy", "precision", "recall", "f1", "mcc")},
                         paper_accuracy=PAPER.get(m, (np.nan,))[0], paper_f1=PAPER.get(m, (np.nan, np.nan))[1]))
    out = pd.DataFrame(rows)
    out.to_csv("results/table3_summary.csv", index=False)
    pd.set_option("display.width", 230, "display.max_rows", 200)
    print(out.to_string(index=False))
    raise SystemExit

URL_COLS = ["URLLength", "DomainLength", "IsDomainIP", "TLDLength", "NoOfSubDomain", "HasObfuscation", "NoOfObfuscatedChar",
            "ObfuscationRatio", "NoOfLettersInURL", "LetterRatioInURL", "NoOfDegitsInURL", "DegitRatioInURL",
            "NoOfEqualsInURL", "NoOfQMarkInURL", "NoOfAmpersandInURL", "NoOfOtherSpecialCharsInURL",
            "SpacialCharRatioInURL", "IsHTTPS", "CharContinuationRate", "TLDLegitimateProb", "URLCharProb"]
sel = pd.read_csv("results/repro_features_file_s0.csv")
FEATSETS = {"selected": sel[sel.kept_final].feature.tolist(), "url_only": URL_COLS}

df = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", encoding="utf-8-sig")
if args.max_rows:
    df = df.sample(args.max_rows, random_state=0)
y = df["label"].to_numpy()  # 1 = legit
tr, te = train_test_split(np.arange(len(df)), test_size=0.2, random_state=args.seed, stratify=y)
s = args.seed
MODELS = {
    "BernoulliNB": lambda: BernoulliNB(alpha=0.01, binarize=0.0, fit_prior=False, force_alpha=True),
    "MultinomialNB": lambda: MultinomialNB(),
    "PassiveAggressive": lambda: PassiveAggressiveClassifier(C=5, fit_intercept=False, shuffle=True, random_state=s),
    "Perceptron": lambda: Perceptron(random_state=s),
    "SGD": lambda: SGDClassifier(alpha=0.01, random_state=s),
    "LR": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "DT": lambda: DecisionTreeClassifier(random_state=s),
    "RF": lambda: RandomForestClassifier(n_estimators=100, n_jobs=2, random_state=s),
    "AdaBoost": lambda: AdaBoostClassifier(random_state=s),
    "GradientBoosting": lambda: GradientBoostingClassifier(random_state=s),
    "HistGB": lambda: HistGradientBoostingClassifier(random_state=s),
    "Bagging": lambda: BaggingClassifier(random_state=s, n_jobs=2),
    "KNN": lambda: make_pipeline(StandardScaler(), KNeighborsClassifier(n_jobs=2)),
    "MLP": lambda: make_pipeline(StandardScaler(), MLPClassifier((64, 32), early_stopping=True, random_state=s)),
}


def scores(y_true, pred):
    tp = int(((y_true == 1) & (pred == 1)).sum())
    tn = int(((y_true == 0) & (pred == 0)).sum())
    fp = int(((y_true == 0) & (pred == 1)).sum())
    fn = int(((y_true == 1) & (pred == 0)).sum())
    prec, rec = tp / max(tp + fp, 1), tp / max(tp + fn, 1)
    denom = ((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)) ** 0.5
    return dict(accuracy=(tp + tn) / len(y_true), precision=prec, recall=rec,
                f1=2 * prec * rec / max(prec + rec, 1e-12), mcc=(tp * tn - fp * fn) / denom if denom else np.nan,
                TP=tp, TN=tn, FP=fp, FN=fn)


rows, t0 = [], time.time()
for fs, cols in FEATSETS.items():
    X = df[cols].to_numpy(dtype=np.float64)
    for name, mk in MODELS.items():
        t1 = time.time()
        m = mk().fit(X[tr], y[tr])
        rows.append(dict(seed=args.seed, featset=fs, model=name, n_feat=len(cols), n_train=len(tr), n_test=len(te),
                         fit_predict_s=round(time.time() - t1, 1), **scores(y[te], m.predict(X[te]))))
        print(f"seed {args.seed} {fs} {name}: acc {rows[-1]['accuracy']:.5f} ({rows[-1]['fit_predict_s']}s, total {time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(f"results/table3_seed{args.seed}{'_smoke' if args.max_rows else ''}.csv", index=False)
