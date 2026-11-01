"""Mean +/- std over seeds of results/transfer_runs.csv -> results/transfer_summary.csv (and printed tables)."""
import pandas as pd

r = pd.read_csv("results/transfer_runs.csv")


def ms(g, c):
    m, s = g[c].mean(), g[c].std()
    return "" if pd.isna(m) else f"{m:.2f}±{s:.2f}"


rows = [dict(variant=v, featset=f, model=m, target=t, n_seeds=g.seed.nunique(), auroc=ms(g, "auroc"),
             pr_auc=ms(g, "pr_auc"), recall=ms(g, "recall"), fpr=ms(g, "fpr"), val_recall=ms(g, "val_recall"))
        for (v, f, m, t), g in r.groupby(["variant", "featset", "model", "target"], sort=False)]
d = pd.DataFrame(rows)
d.to_csv("results/transfer_summary.csv", index=False)
pd.set_option("display.width", 200, "display.max_rows", 1000)
for t in d.target.unique():
    print("\n##", t)
    print(d[d.target == t].drop(columns="target").to_string(index=False))
