"""Combined-source (diversity) experiment, leave-one-source-out, matched total training size.

For every pair of sources (PhiUSIIL+GramBeddings, PhiUSIIL+PhreshPhish, GramBeddings+PhreshPhish) draw half of the pool from each
(5,833 rows each, 50% phishing within each source, total 11,666 = the single-source pool size in script 07), split the pooled rows by
registered domain 70/15/15, fit the models, and fix the 95%-recall threshold on the POOLED SOURCE VALIDATION data only. Targets: each
training source's own test rows, the held-out third source (after removing target rows whose URL or domain is in training; all /
homepage / deep slices), and PhishTank (phishing only). Single-source references are in results/transfer_runs_v2.csv (same pool size).
Models and feature sets as in script 07 (LR, RF, HistGB, MLP, char n-gram LR; feature sets all and no_scheme_no_www).
Outputs: results/combined_runs.csv, results/combined_class_mix.csv.
Usage (from the project folder): nice .venv/bin/python scripts/21_combined_sources.py --seeds 0,1,2,3,4
"""
import argparse
import itertools
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import class_mix, domain_split, drop_seen, matched_sample, transfer_metrics, url_type, val_threshold

warnings.filterwarnings("ignore", category=UserWarning)
ap = argparse.ArgumentParser()
ap.add_argument("--seeds", default="0")
ap.add_argument("--models", default="LR,RF,HistGB,MLP,NGRAM")
ap.add_argument("--featsets", default="all,no_scheme_no_www")
ap.add_argument("--total", type=int, default=11_666, help="total pooled training-pool size (matches script 07)")
ap.add_argument("--out", default="results/combined_runs.csv")
args = ap.parse_args()
SEEDS = [int(s) for s in args.seeds.split(",")]

MODELS = {
    "LR": lambda s: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "RF": lambda s: RandomForestClassifier(n_estimators=200, n_jobs=4, random_state=s),
    "HistGB": lambda s: HistGradientBoostingClassifier(max_iter=300, random_state=s),
    "NGRAM": lambda s: make_pipeline(TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=100_000, sublinear_tf=True, dtype=np.float32),
                                     LogisticRegression(max_iter=1000)),
    "MLP": lambda s: make_pipeline(StandardScaler(), MLPClassifier((64, 32), max_iter=200, early_stopping=True, random_state=s)),
}
models = {m: MODELS[m] for m in args.models.split(",")}
SCHEME = r"^[a-z][a-z0-9+.-]*://"

phi = pd.read_pickle("data/cache/phiusiil.pkl")
gram = pd.read_pickle("data/cache/gram_sample.pkl")
phresh = pd.read_pickle("data/cache/phreshphish.pkl")
pt = pd.read_pickle("data/cache/phishtank_tranco.pkl")
pt = pt[pt.phish == 1]
FEATS = [c for c in phi.columns if c not in ("url", "phish", "dom")]
for d in (phi, gram, phresh, pt):
    d["utype"] = url_type(d.url)
FEATSETS = {"all": FEATS, "no_scheme_no_www": [c for c in FEATS if c not in ("is_https", "has_www")]}
SRC = {"PhiUSIIL": phi, "GramBeddings": gram, "PhreshPhish": phresh}


def prep(m_name, d, fs):
    if m_name == "NGRAM":
        if fs == "no_scheme_no_www":
            return d.url.str.replace(SCHEME + r"(www\.)?", "", regex=True, case=False).values
        return d.url.values
    return d[FEATSETS[fs]]


def oracle_fpr95(y, p):
    if len(set(y)) < 2:
        return np.nan
    fpr, tpr, _ = roc_curve(y, p)
    return fpr[np.searchsorted(tpr, 0.95)]


rows, mixes, t0 = [], [], time.time()
for seed in SEEDS:
    for a, b in itertools.combinations(SRC, 2):
        held = [k for k in SRC if k not in (a, b)][0]
        half = args.total // 2
        pool = pd.concat([matched_sample(SRC[k], half, 0.5, seed).assign(src=k) for k in (a, b)]).sample(frac=1, random_state=seed)
        tr, va, te = domain_split(pool, seed)
        combo = f"{a}+{b}"
        t_held = drop_seen(SRC[held], tr)
        targets = {f"{a} test": te[te.src == a], f"{b} test": te[te.src == b], "pooled test": te,
                   f"{held} all": t_held, f"{held} homepage": t_held[t_held.utype == "homepage"], f"{held} deep": t_held[t_held.utype == "deep"],
                   "PhishTank (phish only)": drop_seen(pt, tr)}
        if seed == SEEDS[0]:
            mixes += [dict(combo=combo, **class_mix(d, nm)) for nm, d in {"train": tr, "val": va, **targets}.items() if len(d)]
        for fs in args.featsets.split(","):
            for m_name, mk in models.items():
                model = mk(seed).fit(prep(m_name, tr, fs), tr.phish)
                pv = model.predict_proba(prep(m_name, va, fs))[:, 1]
                thr = val_threshold(va.phish.values, pv)
                p_held = pd.Series(model.predict_proba(prep(m_name, t_held, fs))[:, 1], index=t_held.index)
                for t_name, t in targets.items():
                    if len(t) == 0:
                        continue
                    p = p_held.loc[t.index].values if t_name.startswith(held) else model.predict_proba(prep(m_name, t, fs))[:, 1]
                    rows.append(dict(seed=seed, combo=combo, heldout=held, featset=fs, model=m_name, target=t_name, n=len(t), pos=int(t.phish.sum()),
                                     n_train=len(tr), train_phish_share=float(tr.phish.mean()), val_recall=float((pv[va.phish.values == 1] >= thr).mean()),
                                     oracle_fpr_at_95rec=oracle_fpr95(t.phish.values, p), **transfer_metrics(t.phish.values, p, thr)))
        print(f"seed {seed} {combo} (held out {held}): train {len(tr)} ({time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(args.out, index=False)
pd.DataFrame(mixes).to_csv(args.out.replace("runs", "class_mix"), index=False)
print("done", len(rows), "rows")
