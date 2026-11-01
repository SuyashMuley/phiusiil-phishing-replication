"""(1) Feature distribution shift across datasets; (2) both training directions.

Needs the caches written by 03_cross_dataset.py (data/cache/*.pkl).

Part 2 trains on PhiUSIIL and on GramBeddings in turn, tests on the other dataset (both classes)
and on PhishTank (phishing only). PhishTank has no benign class, so for it we report the
detection rate at the threshold that gives 5% FPR on the *source* dataset's held-out legitimate
URLs (a deployment-style operating point), plus the share flagged at the default 0.5 threshold.
"""
import os

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import metrics

SEED = 0
for f in ("phiusiil", "gram_sample", "phishtank_tranco"):
    if not os.path.exists(f"data/cache/{f}.pkl"):
        raise SystemExit(f"data/cache/{f}.pkl missing - run scripts/03_cross_dataset.py first")
os.makedirs("results", exist_ok=True)
pd.set_option("display.width", 220, "display.max_columns", 30, "display.max_rows", 200)

phi = pd.read_pickle("data/cache/phiusiil.pkl")
gram = pd.read_pickle("data/cache/gram_sample.pkl")
ptr = pd.read_pickle("data/cache/phishtank_tranco.pkl")
pt = ptr[ptr.phish == 1]  # PhishTank phishing only (Tranco rows are phish == 0)

FEATS = [c for c in phi.columns if c not in ("url", "phish", "dom")]
DATA = {"PhiUSIIL": phi, "GramBeddings": gram, "PhishTank": pt}

# ---------------------------------------------------------------- Part 1: distribution shift
KEY = ["url_len", "path_len", "has_www", "is_https", "n_subdomains", "digit_ratio", "entropy", "n_hyphens"]
rows = []
for ds, df in DATA.items():
    for cls, cname in ((0, "legit"), (1, "phish")):
        sub = df[df.phish == cls]
        if len(sub):
            rows.append({"dataset": ds, "class": cname, "n": len(sub),
                         "no_path": (sub.path_len == 0).mean(), **{k: sub[k].mean() for k in KEY}})
summary = pd.DataFrame(rows)
print("== Per dataset x class: feature means (no_path = share of URLs with empty path) ==")
print(summary.round(3).to_string(index=False))
summary.to_csv("results/feature_means.csv", index=False)

ks_rows = []
for a, b, cls, cname in (("PhiUSIIL", "GramBeddings", 0, "legit"), ("PhiUSIIL", "GramBeddings", 1, "phish"),
                         ("PhiUSIIL", "PhishTank", 1, "phish"), ("GramBeddings", "PhishTank", 1, "phish")):
    xa, xb = DATA[a][DATA[a].phish == cls], DATA[b][DATA[b].phish == cls]
    for f in FEATS:
        ks_rows.append({"A": a, "B": b, "class": cname, "feature": f, "KS": ks_2samp(xa[f], xb[f]).statistic})
ks = pd.DataFrame(ks_rows)
ks.to_csv("results/feature_ks.csv", index=False)
print("\n== Top-8 most shifted features (KS statistic, same class, different datasets) ==")
for (a, b, c), g in ks.groupby(["A", "B", "class"]):
    top = g.sort_values("KS", ascending=False).head(8)
    print(f"{a} vs {b} [{c}]: " + ", ".join(f"{r.feature}={r.KS:.2f}" for r in top.itertuples()))

# ---------------------------------------------------------------- Part 2: both directions
MODELS = {
    "LR": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "RF": lambda: RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=SEED),
    "HistGB": lambda: HistGradientBoostingClassifier(max_iter=300, random_state=SEED),
}
FEATSETS = {"all": FEATS, "no_scheme": [c for c in FEATS if c != "is_https"]}
rows = []
for src, tgt in (("PhiUSIIL", "GramBeddings"), ("GramBeddings", "PhiUSIIL")):
    S, T = DATA[src], DATA[tgt]
    tr_i, ho_i = next(GroupShuffleSplit(1, test_size=0.2, random_state=SEED).split(S, S.phish, groups=S.dom))
    train, held = S.iloc[tr_i], S.iloc[ho_i]
    urls, doms = set(train.url), set(train.dom)
    for fs, cols in FEATSETS.items():
        for mn, mk in MODELS.items():
            model = mk().fit(train[cols], train.phish)
            held_p = model.predict_proba(held[cols])[:, 1]
            thr = np.quantile(held_p[held.phish.values == 0], 0.95)  # 5% FPR on source legit
            rows.append(dict(train=src, features=fs, model=mn, test=f"{src} held-out", filter="-",
                             n=len(held), **metrics(held.phish.values, held_p)))
            for flt in ("url", "domain"):
                for tname, df in ((tgt, T), ("PhishTank", pt)):
                    d = df[~df.url.isin(urls)]
                    if flt == "domain":
                        d = d[~d.dom.isin(doms)]
                    p = model.predict_proba(d[cols])[:, 1]
                    r = dict(train=src, features=fs, model=mn, test=tname, filter=flt, n=len(d),
                             **metrics(d.phish.values, p))
                    if tname == "PhishTank":
                        r["detect_at_src_fpr5"] = (p > thr).mean()
                        r["flagged_at_0_5"] = (p >= 0.5).mean()
                    rows.append(r)
            print("done", src, fs, mn, flush=True)

res = pd.DataFrame(rows)
res.to_csv("results/reverse_directions.csv", index=False)
print("\n== Two-class tests (AUROC / PR-AUC are the numbers to cite) ==")
print(res[res.test != "PhishTank"].round(4).to_string(index=False))
print("\n== PhishTank (phishing only): detection rate at the source's 5%-FPR threshold ==")
print(res[res.test == "PhishTank"][["train", "features", "model", "filter", "n", "detect_at_src_fpr5",
                                    "flagged_at_0_5"]].round(4).to_string(index=False))
