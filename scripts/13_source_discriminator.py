"""A2: can a classifier tell WHICH SOURCE a URL came from, within one class? (the sources differ beyond phishing vs legit)

Within the phishing class (PhiUSIIL, GramBeddings, PhreshPhish, PhishTank) and within the legitimate class (PhiUSIIL,
GramBeddings, PhreshPhish): for every pair of sources, draw the same number of URLs from each, split by registered domain
(no domain in both train and test) and fit HistGradientBoosting on the URL-only features. AUROC 0.5 means the sources look
alike; near 1 means the source is recoverable from the URL alone. Feature sets: all, no_scheme_no_www, and
'homepage' (homepage URLs only, all features).
Output: results/source_discriminator.csv (3 seeds). Usage: PYTHONPATH=scripts OMP_NUM_THREADS=2 .venv/bin/python scripts/13_source_discriminator.py
"""
import itertools

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupShuffleSplit

from common import url_type

N = 4000  # per source per pair
SRC = {"PhiUSIIL": "phiusiil", "GramBeddings": "gram_sample", "PhreshPhish": "phreshphish", "PhishTank": "phishtank_tranco"}
data = {}
for k, f in SRC.items():
    d = pd.read_pickle(f"data/cache/{f}.pkl")
    data[k] = d[d.phish == 1] if k == "PhishTank" else d
    data[k] = data[k].assign(utype=url_type(data[k].url))
FEATS = [c for c in data["PhiUSIIL"].columns if c not in ("url", "phish", "dom", "utype")]
FS = {"all": FEATS, "no_scheme_no_www": [c for c in FEATS if c not in ("is_https", "has_www")], "homepage": FEATS}
rows = []
for cls, cn in ((1, "phish"), (0, "legit")):
    names = [k for k in SRC if not (cn == "legit" and k == "PhishTank")]
    for a, b in itertools.combinations(names, 2):
        for fs, cols in FS.items():
            for seed in range(3):
                parts = []
                for lab, k in enumerate((a, b)):
                    s = data[k][data[k].phish == cls]
                    s = s[s.utype == "homepage"] if fs == "homepage" else s
                    parts.append(s.sample(min(N, len(s)), random_state=seed).assign(src=lab))
                n = min(len(p) for p in parts)  # equal size per source
                d = pd.concat([p.iloc[:n] for p in parts])
                tr, te = next(GroupShuffleSplit(1, test_size=0.3, random_state=seed).split(d, groups=d.dom))
                m = HistGradientBoostingClassifier(max_iter=200, random_state=seed).fit(d.iloc[tr][cols], d.iloc[tr].src)
                rows.append(dict(cls=cn, pair=f"{a} vs {b}", featset=fs, seed=seed, n_per_source=n,
                                 auroc=roc_auc_score(d.iloc[te].src, m.predict_proba(d.iloc[te][cols])[:, 1])))
out = pd.DataFrame(rows)
out.to_csv("results/source_discriminator.csv", index=False)
print(out.groupby(["cls", "pair", "featset"]).agg(n=("n_per_source", "first"), auroc=("auroc", "mean"), sd=("auroc", "std")).round(3).to_string())
