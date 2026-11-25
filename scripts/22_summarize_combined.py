"""Compare combined-source training with the two single-source models on each HELD-OUT source (script 21 vs script 07 v2 runs).

Held-out X, training sources A and B: for each model and feature set, the same matched total pool size (11,666) and the same
validation-fixed 95%-recall threshold rule (single: source validation; combined: pooled validation). Reports mean±sd over five seeds
of AUROC, recall, FPR and oracle FPR on the target "X all" for: A alone, B alone, A+B. Second table: combined model on its own
training sources' test rows against the single-source model on its own test split.
Outputs: results/combined_vs_single.csv, results/combined_in_source.csv.
Usage (from the project folder): .venv/bin/python scripts/22_summarize_combined.py
"""
import itertools

import pandas as pd

C = pd.read_csv("results/combined_runs.csv")
S = pd.read_csv("results/transfer_runs_v2.csv")
SRC = ["PhiUSIIL", "GramBeddings", "PhreshPhish"]
MODELS = ["HistGB", "RF", "LR", "MLP", "NGRAM"]


def ms(g, c):
    return f"{g[c].mean():.2f}±{g[c].std():.2f}"


def cells(g):
    return dict(n_seeds=g.seed.nunique(), auroc=ms(g, "auroc"), recall=ms(g, "recall"), fpr=ms(g, "fpr"), oracle_fpr=ms(g, "oracle_fpr_at_95rec"),
                _auroc=g.auroc.mean(), _recall=g.recall.mean(), _fpr=g.fpr.mean())


rows = []
for held in SRC:
    a, b = [k for k in SRC if k != held]
    for fs in ("all", "no_scheme_no_www"):
        for m in MODELS:
            for label, g in ((f"{a} alone", S[(S.variant == f"{a}/all") & (S.target == f"{held} all")]),
                             (f"{b} alone", S[(S.variant == f"{b}/all") & (S.target == f"{held} all")]),
                             (f"{a}+{b}", C[(C.combo == f"{a}+{b}") & (C.target == f"{held} all")])):
                g = g[(g.featset == fs) & (g.model == m)]
                rows.append(dict(heldout=held, featset=fs, model=m, trained_on=label, **cells(g)))
cmp = pd.DataFrame(rows)
cmp.to_csv("results/combined_vs_single.csv", index=False)

rows = []
for a, b in itertools.combinations(SRC, 2):
    for fs in ("all", "no_scheme_no_www"):
        for m in MODELS:
            for k in (a, b):
                gc = C[(C.combo == f"{a}+{b}") & (C.target == f"{k} test") & (C.featset == fs) & (C.model == m)]
                gs = S[(S.variant == f"{k}/all") & (S.target == "source test") & (S.featset == fs) & (S.model == m)]
                rows.append(dict(source=k, combo=f"{a}+{b}", featset=fs, model=m, single=ms(gs, "auroc"), combined=ms(gc, "auroc"),
                                 single_recall=ms(gs, "recall"), combined_recall=ms(gc, "recall"), single_fpr=ms(gs, "fpr"), combined_fpr=ms(gc, "fpr")))
pd.DataFrame(rows).to_csv("results/combined_in_source.csv", index=False)

pd.set_option("display.width", 220, "display.max_rows", 300)
print(f"seeds per cell: combined {C.groupby(['combo']).seed.nunique().to_dict()}")
v = cmp[(cmp.featset == "all")]
for held in SRC:
    print(f"\n== held-out {held}, features all (mean±sd over seeds)")
    print(v[v.heldout == held].drop(columns=["heldout", "featset", "_auroc", "_recall", "_fpr"]).to_string(index=False))
# does combining help? fraction of (model, featset) cells where the combined FPR is below BOTH single-source FPRs, and AUROC above both
win = []
for (held, fs, m), g in cmp.groupby(["heldout", "featset", "model"]):
    comb, sing = g[g.trained_on.str.contains(r"\+")].iloc[0], g[~g.trained_on.str.contains(r"\+")]
    win.append(dict(heldout=held, featset=fs, model=m, fpr_below_both=bool(comb._fpr < sing._fpr.min()), fpr_below_worse=bool(comb._fpr < sing._fpr.max()),
                    auroc_above_both=bool(comb._auroc > sing._auroc.max()), auroc_above_worse=bool(comb._auroc > sing._auroc.min())))
w = pd.DataFrame(win)
print("\nCells (3 held-out x 2 feature sets x 5 models = 30): combined FPR below both singles:", int(w.fpr_below_both.sum()),
      "| below the worse single:", int(w.fpr_below_worse.sum()), "| AUROC above both singles:", int(w.auroc_above_both.sum()),
      "| above the worse single:", int(w.auroc_above_worse.sum()))
print(w.groupby("heldout")[["fpr_below_both", "fpr_below_worse", "auroc_above_both", "auroc_above_worse"]].sum())
