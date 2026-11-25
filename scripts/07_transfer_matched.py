"""Part B: URL-only transfer with matched size and class mix and validation-fixed thresholds.

Source variants (22 URL-only features, no similarity index, no page content):
  PhiUSIIL/all, GramBeddings/all, GramBeddings/homepage (homepage-only training, to separate URL form from source),
  PhreshPhish/all (third source, added 2026-11-25; --variants selects which to run)
Each source pool is sampled to the same size for every variant (smallest variant sets it) and a 50% phishing share, then split into train/val/test with no shared
registered domain. The 95%-recall threshold is chosen on source validation and applied unchanged to every target.
Targets: source test (in-distribution), every other dataset (all / homepage / deep slices, seen URLs and domains
removed), PhishTank (phishing only: recall is the only valid number there).
Usage (from the project folder):
  nice .venv/bin/python scripts/07_transfer_matched.py --seeds 0 --models LR,RF,HistGB
  nice .venv/bin/python scripts/07_transfer_matched.py --seeds 0,1,2,3,4
Outputs: results/transfer_runs.csv, results/transfer_class_mix.csv
"""
import argparse
import os
import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_curve
from sklearn.neural_network import MLPClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import class_mix, domain_split, drop_seen, matched_sample, transfer_metrics, url_type, val_threshold

warnings.filterwarnings("ignore", category=UserWarning)
ap = argparse.ArgumentParser()
ap.add_argument("--seeds", default="0")
ap.add_argument("--models", default="LR,RF,HistGB,MLP,NGRAM")
ap.add_argument("--featsets", default=None, help="no_scheme drops is_https (feature models) / strips the scheme (NGRAM); no_scheme_no_www also drops has_www / a leading www.")
ap.add_argument("--pool", type=int, default=40_000, help="max matched pool size per source variant")
ap.add_argument("--phish-rate", type=float, default=0.5)
ap.add_argument("--unmatched", action="store_true", help="do not force the same pool size across source variants")
ap.add_argument("--variants", default="PhiUSIIL/all,GramBeddings/all,GramBeddings/homepage,PhreshPhish/all")
ap.add_argument("--canonical", action="store_true", help="A3: features and NGRAM text come from canonical URLs (lowercase, no scheme, no leading www., no trailing /); build the caches with scripts/14_build_canonical_cache.py. Row selection, URL type and 'seen' filters still use the original URL.")
ap.add_argument("--save-scores", default="", help="A4: save the first seed's scores for the feature set 'all' to this .npz (models in --score-models)")
ap.add_argument("--score-models", default="LR,HistGB")
ap.add_argument("--out", default=None)
args = ap.parse_args()
SEEDS = [int(s) for s in args.seeds.split(",")]
args.featsets = args.featsets or ("all" if args.canonical else "all,no_scheme,no_scheme_no_www")
args.out = args.out or ("results/transfer_runs_canon.csv" if args.canonical else "results/transfer_runs.csv")
SUFFIX = "_canon" if args.canonical else ""
os.makedirs("results", exist_ok=True)

MODELS = {
    "LR": lambda s: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "RF": lambda s: RandomForestClassifier(n_estimators=200, n_jobs=4, random_state=s),
    "HistGB": lambda s: HistGradientBoostingClassifier(max_iter=300, random_state=s),
    "NGRAM": lambda s: make_pipeline(TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=100_000,
                                                     sublinear_tf=True, dtype=np.float32),
                                     LogisticRegression(max_iter=1000)),
    "MLP": lambda s: make_pipeline(StandardScaler(), MLPClassifier((64, 32), max_iter=200, early_stopping=True, random_state=s)),
}
models = {m: MODELS[m] for m in args.models.split(",")}
TEXT_MODELS = {"NGRAM"}  # read the raw URL string instead of the 22 features
SCHEME = r"^[a-z][a-z0-9+.-]*://"

phi = pd.read_pickle(f"data/cache/phiusiil{SUFFIX}.pkl")
gram = pd.read_pickle(f"data/cache/gram_sample{SUFFIX}.pkl")
phresh = pd.read_pickle(f"data/cache/phreshphish{SUFFIX}.pkl")
pt = pd.read_pickle(f"data/cache/phishtank_tranco{SUFFIX}.pkl")
pt = pt[pt.phish == 1]  # Tranco rows carry a synthetic https:// and are not used
FEATS = [c for c in phi.columns if c not in ("url", "curl", "phish", "dom")]
for d in (phi, gram, phresh, pt):
    d["utype"] = url_type(d.url)
FEATSETS = {"all": FEATS, "no_scheme": [c for c in FEATS if c != "is_https"],
            "no_scheme_no_www": [c for c in FEATS if c not in ("is_https", "has_www")]}
USED_FS = args.featsets.split(",")


def prep(m_name, d, fs):
    if m_name in TEXT_MODELS:
        col = d.curl if args.canonical else d.url  # canonical text already has no scheme, www or trailing /
        if fs == "no_scheme":
            return col.str.replace(SCHEME, "", regex=True, case=False).values
        if fs == "no_scheme_no_www":
            return col.str.replace(SCHEME + r"(www\.)?", "", regex=True, case=False).values
        return col.values
    return d[FEATSETS[fs]]

ALL_SOURCES = {"PhiUSIIL/all": (phi, None), "GramBeddings/all": (gram, None), "GramBeddings/homepage": (gram, "homepage"),
               "PhreshPhish/all": (phresh, None)}
SOURCES = {v: ALL_SOURCES[v] for v in args.variants.split(",")}
DATASETS = {"PhiUSIIL": phi, "GramBeddings": gram, "PhreshPhish": phresh}
OTHER = {v: [(n, d) for n, d in DATASETS.items() if n != v.split("/")[0]] for v in ALL_SOURCES}  # every other dataset


def pool_size(df, kind):
    d = df if kind is None else df[df.utype == kind]
    per_class = min((d.phish == 1).sum(), (d.phish == 0).sum())
    return int(min(args.pool, per_class / min(args.phish_rate, 1 - args.phish_rate)))


def oracle_fpr95(y, p):
    if len(set(y)) < 2:
        return np.nan
    fpr, tpr, _ = roc_curve(y, p)
    return fpr[np.searchsorted(tpr, 0.95)]


COMMON_N = min(pool_size(src, kind) for src, kind in ALL_SOURCES.values())  # fixed by all four so runs stay comparable  # same pool size for every variant
print(f"matched pool size {COMMON_N} (largest allowed by the smallest variant)" if not args.unmatched else "unmatched pool sizes", flush=True)
rows, mixes, scores = [], [], {}
SCORE_MODELS = set(args.score_models.split(","))
t0 = time.time()
for seed in SEEDS:
    for variant, (src, kind) in SOURCES.items():
        n = pool_size(src, kind) if args.unmatched else COMMON_N
        pool = matched_sample(src, n, args.phish_rate, seed, url_kind=kind)
        tr, va, te = domain_split(pool, seed)
        targets = {"source test": te}
        t_alls, from_all = {}, {}  # each other dataset is scored once; its slices reuse those scores
        for other_name, other in OTHER[variant]:
            t_alls[other_name] = drop_seen(other, tr)
            for sl in ("all", "homepage", "deep"):
                t_all = t_alls[other_name]
                targets[f"{other_name} {sl}"] = t_all if sl == "all" else t_all[t_all.utype == sl]
                from_all[f"{other_name} {sl}"] = other_name
        targets["PhishTank (phish only)"] = drop_seen(pt, tr)
        if seed == SEEDS[0]:
            mixes += [dict(variant=variant, **class_mix(d, nm)) for nm, d in
                      {"train": tr, "val": va, **targets}.items()]
        for fs in USED_FS:
            for m_name, mk in models.items():
                model = mk(seed).fit(prep(m_name, tr, fs), tr.phish)
                pv = model.predict_proba(prep(m_name, va, fs))[:, 1]
                thr = val_threshold(va.phish.values, pv)
                keep = bool(args.save_scores) and seed == SEEDS[0] and fs == "all" and m_name in SCORE_MODELS
                if keep:
                    scores[f"{variant}|{m_name}|val"] = np.stack([pv, va.phish.values]).astype(np.float32)
                    scores[f"{variant}|{m_name}|thr"] = np.array([thr], dtype=np.float32)
                p_alls = {nm: pd.Series(model.predict_proba(prep(m_name, ta, fs))[:, 1], index=ta.index) for nm, ta in t_alls.items()}
                for t_name, t in targets.items():
                    if len(t) == 0:
                        continue
                    p = p_alls[from_all[t_name]].loc[t.index].values if t_name in from_all else model.predict_proba(prep(m_name, t, fs))[:, 1]
                    if keep and (t_name not in from_all or t_name.endswith(" all")):  # slices are subsets of the 'all' rows
                        scores[f"{variant}|{m_name}|{t_name}"] = np.stack([p, t.phish.values, (t.utype == "deep").values]).astype(np.float32)
                    rows.append(dict(seed=seed, variant=variant, featset=fs, model=m_name, target=t_name, n=len(t),
                                     pos=int(t.phish.sum()), n_train=len(tr),
                                     val_recall=float((pv[va.phish.values == 1] >= thr).mean()),
                                     oracle_fpr_at_95rec=oracle_fpr95(t.phish.values, p),
                                     **transfer_metrics(t.phish.values, p, thr)))
        print(f"seed {seed} {variant}: pool {n}, train {len(tr)} ({time.time() - t0:.0f}s)", flush=True)
        pd.DataFrame(rows).to_csv(args.out, index=False)

if scores:
    np.savez_compressed(args.save_scores, **scores)
    print(f"saved {len(scores)} score arrays to {args.save_scores}", flush=True)
res = pd.DataFrame(rows)
mix_path = os.path.join(os.path.dirname(args.out), (os.path.basename(args.out).replace("runs", "class_mix") if "runs" in os.path.basename(args.out)
                                                    else os.path.splitext(os.path.basename(args.out))[0] + "_class_mix.csv"))
pd.DataFrame(mixes).to_csv(mix_path, index=False)
pd.set_option("display.width", 220, "display.max_columns", 30)
print("\nClass mix (seed %d)" % SEEDS[0])
print(pd.DataFrame(mixes).round(3).to_string(index=False))
cols = ["variant", "model", "target", "n", "pos", "auroc", "pr_auc", "recall", "fpr", "oracle_fpr_at_95rec"]
print("\nTransfer results (mean over seeds)")
print(res.groupby(["variant", "featset", "model", "target"], sort=False)[cols[3:]].mean().round(3).to_string())
