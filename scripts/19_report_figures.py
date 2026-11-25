"""Report version of the operating-point figure: 2x2 panels so the text stays readable at page width.
Reads results/transfer_runs_v2.csv (feature set 'all'); writes results/fig_operating_points_2x2.png. Same encoding as scripts/16 (dataset color, model marker).
Usage (from the project folder): .venv/bin/python scripts/19_report_figures.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

R = pd.read_csv("results/transfer_runs_v2.csv")
R = R[R.featset == "all"]
OTHERS = {"PhiUSIIL": ["GramBeddings", "PhreshPhish"], "GramBeddings": ["PhiUSIIL", "PhreshPhish"], "PhreshPhish": ["PhiUSIIL", "GramBeddings"]}
VARIANTS = ["PhiUSIIL/all", "GramBeddings/all", "GramBeddings/homepage", "PhreshPhish/all"]
MODELS = ["HistGB", "RF", "LR", "MLP", "NGRAM"]
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e5e4e0"
COL = {"PhiUSIIL": "#2a78d6", "GramBeddings": "#eb6834", "PhreshPhish": "#1baf7a"}
MARK = {"HistGB": "o", "RF": "s", "LR": "^", "MLP": "D", "NGRAM": "P"}
plt.rcParams.update({"font.size": 10, "axes.edgecolor": MUTED, "axes.labelcolor": INK, "text.color": INK, "xtick.color": MUTED, "ytick.color": MUTED})

fig, axes = plt.subplots(2, 2, figsize=(8.6, 7.6), sharex=True, sharey=True)
for ax, v in zip(axes.ravel(), VARIANTS):
    ax.plot([0, 1], [0, 1], color=MUTED, lw=0.8, ls=":")
    ax.axhline(0.95, color=MUTED, lw=0.8, ls="--")
    src = v.split("/")[0]
    for t, ent in [("source test", src)] + [(f"{o} all", o) for o in OTHERS[src]]:
        g = R[(R.variant == v) & (R.target == t)].groupby("model")[["recall", "fpr"]].mean()
        for m in MODELS:
            ax.scatter(g.loc[m, "fpr"], g.loc[m, "recall"], marker=MARK[m], s=58, facecolor="white" if t == "source test" else COL[ent],
                       edgecolor=COL[ent], linewidth=1.8, zorder=3)
    ax.set_title("trained on " + v.replace("/all", "").replace("/homepage", " (homepage only)"), fontsize=10.5, loc="left")
    ax.set_xlim(-0.03, 1.03); ax.set_ylim(0.4, 1.02); ax.grid(color=GRID, lw=0.6); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
for ax in axes[1]:
    ax.set_xlabel("false-positive rate on target")
for ax in axes[:, 0]:
    ax.set_ylabel("recall on target")
h1 = [plt.Line2D([], [], marker="o", ls="", markerfacecolor=COL[k], markeredgecolor=COL[k], label=f"tested on {k}") for k in COL]
h1 += [plt.Line2D([], [], marker="o", ls="", markerfacecolor="white", markeredgecolor=MUTED, label="in-source test (hollow)")]
h2 = [plt.Line2D([], [], marker=MARK[m], ls="", markerfacecolor=MUTED, markeredgecolor=MUTED, label=m) for m in MODELS]
h3 = [plt.Line2D([], [], color=MUTED, lw=0.8, ls="--", label="95% recall target"), plt.Line2D([], [], color=MUTED, lw=0.8, ls=":", label="recall = FPR")]
fig.legend(handles=h1 + h2 + h3, loc="lower center", ncol=4, frameon=False, fontsize=9)
fig.tight_layout(rect=(0, 0.13, 1, 1))
fig.savefig("results/fig_operating_points_2x2.png", dpi=170)
print("wrote results/fig_operating_points_2x2.png")
