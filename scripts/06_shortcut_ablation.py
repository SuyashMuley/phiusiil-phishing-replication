"""Is URLSimilarityIndex (USI) a label leak or a construction shortcut? Evidence on the released PhiUSIIL data.

Paper (Sec 3.1, 4.1): legit URLs come from the Open PageRank top-10M list; USI is a character-match score of a URL
against that same list, so a listed legit URL scores exactly 100. Checks here:
  A  USI distribution by class, with the paper's three bands (100 / [80,100) / <80)
  B  Tranco top-1M membership (proxy for the unavailable Open PageRank list) by class and USI band
  C  What phishing URLs in the [80,100) band are (sample + domain-in-Tranco share)
  D  Single-feature AUROC for every numeric feature (which columns carry the label)
  E  Ablation: HistGB on feature groups, random split and eTLD+1-disjoint split, several seeds
  F  Simple homepage rule baseline (https://www.<host>/ with no path)
Outputs: results/shortcut_*.csv
"""
import os
import re

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import GroupShuffleSplit, train_test_split

from common import etld1

SEEDS = (0, 1, 2)
os.makedirs("results", exist_ok=True)

df = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", encoding="utf-8-sig")
df["phish"] = 1 - df["label"]  # PhiUSIIL: 1=legit -> ours 1=phish
usi = df["URLSimilarityIndex"]
df["band"] = np.where(usi == 100, "=100", np.where(usi >= 80, "80-100", "<80"))

# ---- A: USI distribution
print("== A. USI bands by class (rows)")
a = pd.crosstab(df["phish"].map({0: "legit", 1: "phish"}), df["band"])
print(a, "\n")
a.to_csv("results/shortcut_usi_bands.csv")
n_p80 = int(((df.phish == 1) & (df.band == "80-100")).sum())
print(f"phishing with 80<=USI<100: {n_p80}  (paper Sec 5.4 reports 7,341 caught by this rule)\n")

# ---- B: Tranco membership
tr = pd.read_csv("data/external/top-1m.csv", header=None, names=["rank", "domain"])
tr_set = set(tr.domain.str.lower())
df["reg"] = [etld1(u) for u in df.URL]  # registered domain, used for grouping and membership
df["in_tranco"] = df["reg"].str.lower().isin(tr_set)
print("== B. share whose registered domain is in Tranco top-1M (lower bound on Open PageRank top-10M)")
b = df.groupby([df["phish"].map({0: "legit", 1: "phish"}), "band"])["in_tranco"].agg(["mean", "size"])
print(b, "\n")
b.to_csv("results/shortcut_tranco_membership.csv")

# ---- C: what are phishing URLs in the 80-100 band
print("== C. sample of phishing URLs with 80<=USI<100")
c = df[(df.phish == 1) & (df.band == "80-100")]
print(c[["URL", "URLSimilarityIndex", "in_tranco"]].sample(25, random_state=0).to_string(index=False), "\n")
print("share with registered domain in Tranco (abuse of a real domain, not a typosquat):", round(c.in_tranco.mean(), 3))
print("share that are bare homepages (no path):",
      round(c.URL.str.match(r"^https?://[^/]+/?$").mean(), 3), "\n")

# ---- feature groups
URL_COLS = ["URLLength", "DomainLength", "IsDomainIP", "TLDLength", "NoOfSubDomain", "HasObfuscation",
            "NoOfObfuscatedChar", "ObfuscationRatio", "NoOfLettersInURL", "LetterRatioInURL", "NoOfDegitsInURL",
            "DegitRatioInURL", "NoOfEqualsInURL", "NoOfQMarkInURL", "NoOfAmpersandInURL",
            "NoOfOtherSpecialCharsInURL", "SpacialCharRatioInURL", "IsHTTPS"]
DERIVED = ["CharContinuationRate", "TLDLegitimateProb", "URLCharProb"]  # derived from URL, fit on the corpus
USI = ["URLSimilarityIndex"]
non_feat = {"FILENAME", "URL", "Domain", "TLD", "Title", "label", "phish", "band", "reg", "in_tranco"}
PAGE = [c for c in df.columns if c not in non_feat | set(URL_COLS + DERIVED + USI)]
ALL = USI + URL_COLS + DERIVED + PAGE
groups = {
    "all": ALL,
    "no_USI": [c for c in ALL if c not in USI],
    "no_page": USI + URL_COLS + DERIVED,
    "no_USI_no_page": URL_COLS + DERIVED,
    "no_USI_no_page_no_derived": URL_COLS,
    "USI_only": USI,
    "page_only": PAGE,
}

# ---- D: single-feature AUROC
print("== D. single-feature AUROC (phish=1), top 12 by max(auc, 1-auc)")
d = pd.DataFrame({c: [roc_auc_score(df.phish, df[c])] for c in ALL}).T.rename(columns={0: "auroc"})
d["strength"] = np.maximum(d.auroc, 1 - d.auroc)
d = d.sort_values("strength", ascending=False)
print(d.head(12), "\n")
d.to_csv("results/shortcut_single_feature_auroc.csv")

# ---- F: rules
rules = {
    "USI<100 -> phish": (usi < 100).astype(int),
    "not(https://www.<host>/ homepage) -> phish": (~df.URL.str.match(r"^https://www\.[^/]+/?$")).astype(int),
    "has path -> phish": df.URL.str.replace(r"^[a-z]+://", "", regex=True).str.contains("/.+", regex=True).astype(int),
}
print("== F. rule baselines")
f = pd.DataFrame([{"rule": k, "acc": accuracy_score(df.phish, v), "f1": f1_score(df.phish, v),
                   "legit_flagged": ((v == 1) & (df.phish == 0)).sum() / (df.phish == 0).sum()}
                  for k, v in rules.items()])
print(f.to_string(index=False), "\n")
f.to_csv("results/shortcut_rules.csv", index=False)

# ---- E: ablation
rows = []
for seed in SEEDS:
    splits = {
        "random": train_test_split(df.index, test_size=0.2, random_state=seed, stratify=df.phish),
        "domain-disjoint": next(GroupShuffleSplit(1, test_size=0.2, random_state=seed).split(df, groups=df.reg)),
    }
    for sp, (tri, tei) in splits.items():
        for name, cols in groups.items():
            m = HistGradientBoostingClassifier(max_iter=200, random_state=seed).fit(df.loc[tri, cols], df.phish[tri])
            p = m.predict_proba(df.loc[tei, cols])[:, 1]
            rows.append(dict(seed=seed, split=sp, features=name, n_feat=len(cols), auroc=roc_auc_score(df.phish[tei], p),
                             acc=accuracy_score(df.phish[tei], p > .5), f1=f1_score(df.phish[tei], p > .5)))
        print("done seed", seed, sp, flush=True)
e = pd.DataFrame(rows)
e.to_csv("results/shortcut_ablation_runs.csv", index=False)
s = e.groupby(["split", "features", "n_feat"])[["auroc", "acc", "f1"]].agg(["mean", "std"]).round(4)
print("\n== E. ablation, HistGB, mean/std over seeds", SEEDS)
print(s.to_string())
s.to_csv("results/shortcut_ablation_summary.csv")
