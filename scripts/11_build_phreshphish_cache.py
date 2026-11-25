"""Build data/cache/phreshphish.pkl: a balanced sample with registered domain and the 22 URL-only features.

Same recipe as the GramBeddings cache in script 03 (50,000 per class, seed 0, duplicates dropped), so script 07 can
use it the same way. label 'phish' -> phish=1, 'benign' -> phish=0.
Usage (from the project folder): nice .venv/bin/python scripts/11_build_phreshphish_cache.py [--per-class 50000]
"""
import argparse
import time

import pandas as pd

from common import etld1, featurize

ap = argparse.ArgumentParser()
ap.add_argument("--per-class", type=int, default=50_000)
ap.add_argument("--seed", type=int, default=0)
args = ap.parse_args()

t0 = time.time()
df = pd.read_csv("data/phreshphish/phreshphish_url_label_date.csv")
df = pd.DataFrame({"url": df.url, "phish": (df.label == "phish").astype(int)}).drop_duplicates("url")
df = pd.concat([df[df.phish == k].sample(args.per_class, random_state=args.seed) for k in (0, 1)]).reset_index(drop=True)
df["dom"] = df.url.map(etld1)
out = pd.concat([df, featurize(df.url)], axis=1)
out.to_pickle("data/cache/phreshphish.pkl")
print(out.shape, out.phish.value_counts().to_dict(), f"{time.time() - t0:.0f}s")
