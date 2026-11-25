"""Mean +/- std over seeds of a transfer runs file -> summary csv (and printed tables).
Usage: .venv/bin/python scripts/08_summarize_transfer.py [runs.csv] [summary.csv]   (defaults: results/transfer_runs.csv, results/transfer_summary.csv)"""
import sys

import pandas as pd

RUNS = sys.argv[1] if len(sys.argv) > 1 else "results/transfer_runs.csv"
SUMMARY = sys.argv[2] if len(sys.argv) > 2 else "results/transfer_summary.csv"
r = pd.read_csv(RUNS)


def ms(g, c):
    m, s = g[c].mean(), g[c].std()
    return "" if pd.isna(m) else f"{m:.2f}±{s:.2f}"


rows = [dict(variant=v, featset=f, model=m, target=t, n_seeds=g.seed.nunique(), auroc=ms(g, "auroc"),
             pr_auc=ms(g, "pr_auc"), recall=ms(g, "recall"), fpr=ms(g, "fpr"), val_recall=ms(g, "val_recall"))
        for (v, f, m, t), g in r.groupby(["variant", "featset", "model", "target"], sort=False)]
d = pd.DataFrame(rows)
d.to_csv(SUMMARY, index=False)
pd.set_option("display.width", 200, "display.max_rows", 1000)
for t in d.target.unique():
    print("\n##", t)
    print(d[d.target == t].drop(columns="target").to_string(index=False))
