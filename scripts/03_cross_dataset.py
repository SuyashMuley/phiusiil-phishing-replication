"""Train on PhiUSIIL (URL-only features), test in-distribution and on independent sources.

Test sets:
  in-dist       : PhiUSIIL held-out, eTLD+1-grouped split (no domain shared with train)
  GramBeddings  : balanced 50k phish / 50k legit sample (legit includes deep links)
  PhishTank+Tranco : PhishTank phishing vs Tranco homepages (KNOWN homepage artifact: see report)
Each external set is evaluated with two filters:
  url    : only exact-URL overlap with the training data removed
  domain : every row whose eTLD+1 appears in the training data removed (strict)
Feature sets: 'all' and 'no_scheme' (drops is_https; Tranco URLs are synthetic https://).
"""
import os

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (average_precision_score, f1_score, roc_auc_score, roc_curve)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common import etld1, featurize, load

SEED = 0
N_EXT = 50_000
os.makedirs("data/cache", exist_ok=True)
os.makedirs("results", exist_ok=True)
rng = np.random.RandomState(SEED)


def cached(name, fn):
    path = f"data/cache/{name}.pkl"
    if os.path.exists(path):
        return pd.read_pickle(path)
    out = fn()
    out.to_pickle(path)
    return out


def build(name, df):
    """df: url, phish -> adds dom + feature columns (cached)."""
    def make():
        d = df.drop_duplicates("url").reset_index(drop=True)
        d["dom"] = d.url.map(etld1)
        return pd.concat([d, featurize(d.url)], axis=1)
    return cached(name, make)


D = load()
phi = build("phiusiil", D["PhiUSIIL"])

gram = D["GramBeddings"].drop_duplicates("url")
gram = pd.concat([gram[gram.phish == k].sample(N_EXT, random_state=SEED) for k in (0, 1)])
gram = build("gram_sample", gram)

pt = D["PhishTank"].drop_duplicates("url")
tr = pd.read_csv("data/external/top-1m.csv", header=None, names=["rank", "domain"]).head(100_000)
tr = tr.sample(len(pt), random_state=SEED)
tr = pd.DataFrame({"url": "https://" + tr.domain, "phish": 0})
pt_tr = build("phishtank_tranco", pd.concat([pt, tr]))

FEATS = [c for c in phi.columns if c not in ("url", "phish", "dom")]
FEATSETS = {"all": FEATS, "no_scheme": [c for c in FEATS if c != "is_https"]}

# in-distribution: domain-grouped split
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=SEED)
tr_idx, te_idx = next(gss.split(phi, phi.phish, groups=phi.dom))
train, indist = phi.iloc[tr_idx], phi.iloc[te_idx]
train_urls, train_doms = set(train.url), set(train.dom)


def filt(df, mode):
    df = df[~df.url.isin(train_urls)]
    if mode == "domain":
        df = df[~df.dom.isin(train_doms)]
    return df


TESTS = {"in-dist (domain-disjoint)": [("-", indist)]}
for nm, df in (("GramBeddings", gram), ("PhishTank+Tranco", pt_tr)):
    TESTS[nm] = [("url", filt(df, "url")), ("domain", filt(df, "domain"))]

MODELS = {
    "LR": lambda: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)),
    "RF": lambda: RandomForestClassifier(n_estimators=200, n_jobs=-1, random_state=SEED),
    "HistGB": lambda: HistGradientBoostingClassifier(max_iter=300, random_state=SEED),
}


def metrics(y, p):
    if len(set(y)) < 2:
        return dict(auroc=np.nan, pr_auc=np.nan, f1=np.nan, fpr_at_0_5=np.nan, fpr_at_95rec=np.nan)
    fpr, tpr, _ = roc_curve(y, p)
    pred = p >= 0.5
    return dict(
        auroc=roc_auc_score(y, p),
        pr_auc=average_precision_score(y, p),
        f1=f1_score(y, pred),
        fpr_at_0_5=(pred & (y == 0)).sum() / max((y == 0).sum(), 1),
        fpr_at_95rec=fpr[np.searchsorted(tpr, 0.95)],
    )


rows = []
for fs_name, cols in FEATSETS.items():
    for m_name, mk in MODELS.items():
        model = mk().fit(train[cols], train.phish)
        for t_name, variants in TESTS.items():
            for flt, df in variants:
                p = model.predict_proba(df[cols])[:, 1]
                rows.append(dict(features=fs_name, model=m_name, test=t_name, filter=flt,
                                 n=len(df), pos=int(df.phish.sum()), **metrics(df.phish.values, p)))
        print("done", fs_name, m_name, flush=True)

res = pd.DataFrame(rows)
res.to_csv("results/cross_dataset_results.csv", index=False)
pd.set_option("display.width", 200, "display.max_columns", 20)
print(res.round(4).to_string(index=False))
