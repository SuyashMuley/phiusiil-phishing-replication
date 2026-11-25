"""A4: score distributions for source validation vs each target, with the fixed threshold, from scripts/07 --save-scores.

One figure per model: rows = training source, columns = source validation, source test and every target, histograms of the
model score for phishing and legitimate rows, vertical line = the threshold fixed on source validation (95% recall).
PhishTank has phishing only. Output: results/fig_scores_<model>.png
Usage: PYTHONPATH=scripts .venv/bin/python scripts/15_plot_scores.py [results/scores_seed0.npz]
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

path = sys.argv[1] if len(sys.argv) > 1 else "results/scores_seed0.npz"
Z = np.load(path)
variants = ["PhiUSIIL/all", "GramBeddings/all", "GramBeddings/homepage", "PhreshPhish/all"]
models = sorted({k.split("|")[1] for k in Z.files})
bins = np.linspace(0, 1, 41)
for m in models:
    cols = ["val", "source test"] + [f"{o} all" for o in ("PhiUSIIL", "GramBeddings", "PhreshPhish")] + ["PhishTank (phish only)"]
    fig, axes = plt.subplots(len(variants), len(cols), figsize=(2.3 * len(cols), 2.1 * len(variants)), sharex=True, squeeze=False)
    titled = set()
    for i, v in enumerate(variants):
        thr = float(Z[f"{v}|{m}|thr"][0])
        for j, c in enumerate(cols):
            ax = axes[i][j]
            key = f"{v}|{m}|{c}"
            if i == 0:
                ax.set_title(c, fontsize=11)  # every column is titled on the top row, even where that cell is blank
            if key not in Z.files:
                ax.axis("off")  # the source itself is not its own external target
                continue
            a = Z[key]
            p, y = a[0], a[1]
            for lab, color, name in ((0, "#2a7ab0", "legit"), (1, "#c8553d", "phish")):
                if (y == lab).any():
                    ax.hist(p[y == lab], bins=bins, weights=np.full((y == lab).sum(), 1 / (y == lab).sum()), color=color, alpha=0.6, label=name)
            ax.axvline(thr, color="k", lw=1, ls="--")
            ax.set_yticks([])
            if j == 0:
                ax.set_ylabel(v.replace("/", "\n"), fontsize=11)
            if i == len(variants) - 1:
                ax.set_xlabel("score")
    axes[0][1].legend(fontsize=7)
    fig.suptitle(f"{m}: score distributions, threshold (dashed) fixed at 95% recall on source validation", fontsize=10)
    fig.tight_layout()
    fig.savefig(f"results/fig_scores_{m}.png", dpi=130)
    print("wrote", f"results/fig_scores_{m}.png")
