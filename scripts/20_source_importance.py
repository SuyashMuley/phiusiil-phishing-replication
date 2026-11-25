"""Item 1 (explanation depth): WHICH URL features let a model tell the sources apart, within a class and within a URL type?

Same setup as script 13 (HistGB, equal numbers per source, registered-domain-disjoint 70/30 split, 3 seeds), now with permutation
importance on the held-out part (drop in AUROC when one feature is shuffled, 5 repeats) for every pair of sources, within each
class, for three subsets: all URLs, homepage URLs only and deep URLs only. A pair/subset is skipped when a source has fewer than
300 rows in it (PhiUSIIL has no deep legitimate URLs).
Outputs: results/source_importance.csv (long), results/source_importance_top.csv (top 3 features per cell, mean over seeds).
Usage (from the project folder): OMP_NUM_THREADS=2 nice .venv/bin/python scripts/20_source_importance.py
"""
import itertools

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from common import url_type

N, MIN_ROWS = 4000, 300
SRC = {"PhiUSIIL": "phiusiil", "GramBeddings": "gram_sample", "PhreshPhish": "phreshphish", "PhishTank": "phishtank_tranco"}
data = {}
for k, f in SRC.items():
    d = pd.read_pickle(f"data/cache/{f}.pkl")
    d = d[d.phish == 1] if k == "PhishTank" else d
    data[k] = d.assign(utype=url_type(d.url))
FEATS = [c for c in data["PhiUSIIL"].columns if c not in ("url", "phish", "dom", "utype")]
rows = []
for cls, cn in ((1, "phish"), (0, "legit")):
    names = [k for k in SRC if not (cn == "legit" and k == "PhishTank")]
    for a, b in itertools.combinations(names, 2):
        for ut in ("all", "homepage", "deep"):
            sub = {k: data[k][(data[k].phish == cls) & ((data[k].utype == ut) | (ut == "all"))] for k in (a, b)}
            if min(len(s) for s in sub.values()) < MIN_ROWS:
                continue
            for seed in range(3):
                n = min(N, *(len(s) for s in sub.values()))
                d = pd.concat([sub[k].sample(n, random_state=seed).assign(src=i) for i, k in enumerate((a, b))])
                tr, te = next(GroupShuffleSplit(1, test_size=0.3, random_state=seed).split(d, groups=d.dom))
                m = HistGradientBoostingClassifier(max_iter=200, random_state=seed).fit(d.iloc[tr][FEATS], d.iloc[tr].src)
                auc = roc_auc_score(d.iloc[te].src, m.predict_proba(d.iloc[te][FEATS])[:, 1])
                pi = permutation_importance(m, d.iloc[te][FEATS], d.iloc[te].src, scoring="roc_auc", n_repeats=5, random_state=seed, n_jobs=1)
                for f, v in zip(FEATS, pi.importances_mean):
                    rows.append(dict(cls=cn, pair=f"{a} vs {b}", utype=ut, seed=seed, n_per_source=n, auroc=auc, feature=f, importance=v))
out = pd.DataFrame(rows)
out.to_csv("results/source_importance.csv", index=False)
g = out.groupby(["cls", "pair", "utype", "feature"]).agg(importance=("importance", "mean"), auroc=("auroc", "mean"), n=("n_per_source", "first")).reset_index()
top = (g.sort_values("importance", ascending=False).groupby(["cls", "pair", "utype"]).head(3)
         .assign(rank=lambda d: d.groupby(["cls", "pair", "utype"]).importance.rank(ascending=False, method="first").astype(int)))
top.sort_values(["cls", "pair", "utype", "rank"]).to_csv("results/source_importance_top.csv", index=False)
pd.set_option("display.width", 220, "display.max_rows", 400)
t = top.sort_values(["cls", "pair", "utype", "rank"])
print(t.assign(top=lambda d: d.feature + " (" + d.importance.round(3).astype(str) + ")").groupby(["cls", "pair", "utype"]).agg(auroc=("auroc", "first"), n=("n", "first"), top=("top", " | ".join)).round(3).to_string())
