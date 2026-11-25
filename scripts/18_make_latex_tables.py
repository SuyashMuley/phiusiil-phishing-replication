"""Writes report/tables/*.tex (booktabs tabulars) from the result CSVs, so no number in the report is typed by hand.
Reads results/final_*.csv, results/shortcut_ablation_summary.csv, results/source_profile.csv, results/source_discriminator.csv, results/phishtank files.
Usage (from the project folder): .venv/bin/python scripts/18_make_latex_tables.py
"""
import pandas as pd

R, T = "results/", "report/tables/"
MODELS = ["HistGB", "RF", "LR", "MLP", "NGRAM"]


def esc(x):
    s = str(x)
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#"), ("±", r"$\pm$"), (" (", " ("), ("->", r"$\to$")):
        s = s.replace(a, b)
    return s


def emit(name, header, rows, spec, size=r"\footnotesize", rule_after=()):
    out = [r"{" + size, r"\begin{tabular}{" + spec + "}", r"\toprule", " & ".join(r"\textbf{" + esc(h) + "}" for h in header) + r" \\", r"\midrule"]
    for i, r in enumerate(rows):
        out.append(" & ".join(esc(c) for c in r) + r" \\")
        if i in rule_after:
            out.append(r"\addlinespace")
    out += [r"\bottomrule", r"\end{tabular}", r"}"]
    open(T + name + ".tex", "w").write("\n".join(out) + "\n")


# ---- Part A, Tables 5/6: accuracy, F1, MCC by profile
t5 = pd.read_csv(R + "final_partA_table5.csv")
rows = []
for p in ["LowSecurity", "BestSecurity", "HighSecurity"]:
    for m in ("accuracy", "F1", "MCC"):
        r = t5[(t5.profile == p) & (t5.metric == m)].iloc[0]
        rows.append([p if m == "accuracy" else "", m, f"{float(r['ours, file order']):.4f}", r["ours, shuffled (4 runs)"], f"{float(r['paper']):.4f}"])
emit("partA_table5", ["Profile", "Metric", "Ours, file order", "Ours, shuffled (4 runs)", "Paper"], rows, "llrrr", rule_after=(2, 5))

t6 = pd.read_csv(R + "final_partA_table6.csv")
rows = []
for p in ["LowSecurity", "BestSecurity", "HighSecurity"]:
    g = t6[t6.profile == p].set_index("cell")
    rows.append([p] + [f"{g.loc[c, 'ours, file order']} / {g.loc[c, 'paper']}" for c in ("TP", "TN", "FP", "FN")])
emit("partA_table6", ["Profile", "TP (ours / paper)", "TN", "FP", "FN"], rows, "lrrrr")

ab = pd.read_csv(R + "final_partA_ablation.csv")
emit("partA_ablation", ["Features", "Features kept", "Accuracy, file order", "Accuracy, shuffled", "F1, shuffled", "FP / FN (shuffled mean)"],
     [[r["features"], r["n features after selection"], f"{r['accuracy, file order']:.4f}", r["accuracy, shuffled (4 runs)"], r["F1, shuffled"], r["FP / FN (shuffled mean)"]] for _, r in ab.iterrows()], "lrrrrr")

t7 = pd.read_csv(R + "final_partA_table7.csv")
emit("partA_table7", ["Pre-train", "Paper", "Ours, sequential", "Ours, random"],
     [[r["pre-train share"], f"{r['paper accuracy']:.5f}", f"{r['ours, sequential split']:.5f}", f"{r['ours, random split']:.5f}"] for _, r in t7.iterrows()], "lrrr")

t3 = pd.read_csv(R + "final_partA_table3.csv")
emit("partA_table3", ["Model", "Paper accuracy", "Ours, 43 selected features", "Ours, 21 URL-only features"],
     [[r["model"], "not in paper" if pd.isna(r["paper accuracy"]) else f"{r['paper accuracy']:.5f}", r["accuracy, selected (43)"], r["accuracy, URL-only (21)"]] for _, r in t3.iterrows()], "lrrr")

# ---- Shortcut ablation (script 06), mean over 3 seeds
sa = pd.read_csv(R + "shortcut_ablation_summary.csv", skiprows=3, header=None,
                 names=["split", "features", "n", "auroc_m", "auroc_s", "acc_m", "acc_s", "f1_m", "f1_s"])
lab = {"all": "all features", "no_USI": "without USI", "no_page": "without page content (keeps USI)", "page_only": "page content only",
       "no_USI_no_page": "without USI and page content", "no_USI_no_page_no_derived": "URL columns only", "USI_only": "USI only"}
rows = []
for k in lab:
    a = sa[(sa.split == "random") & (sa.features == k)].iloc[0]
    d = sa[(sa.split == "domain-disjoint") & (sa.features == k)].iloc[0]
    rows.append([lab[k], int(a.n), f"{a.auroc_m:.4f} / {a.acc_m:.4f}", f"{d.auroc_m:.4f} / {d.acc_m:.4f}"])
emit("shortcut_ablation", ["Feature set", "n", "Random split (AUROC / accuracy)", "Domain-disjoint split"], rows, "lrrr")

# ---- Part B main table
mt = pd.read_csv(R + "final_table_main.csv")
rows = []
for i, (_, r) in enumerate(mt.iterrows()):
    rows.append([r["trained on"] if (i % 3 == 0) else "", r["tested on"], r["AUROC (HistGB)"], r["recall (HistGB)"], r["FPR (HistGB)"],
                 f"{r['oracle FPR@95% (HistGB)']:.2f}", r["recall range, 5 models"], r["FPR range, 5 models"]])
emit("transfer_main", ["Trained on", "Tested on", "AUROC", "Recall", "FPR", "Oracle FPR", "Recall, 5 models", "FPR, 5 models"], rows, "llrrrrrr",
     size=r"\scriptsize\setlength{\tabcolsep}{3.5pt}", rule_after=tuple(range(2, len(rows), 3)))

sl = pd.read_csv(R + "final_table_slices.csv")
emit("transfer_slices", ["Trained on", "Tested on", "n", "AUROC", "Recall", "FPR"],
     [[r["trained on"], r["tested on"], f"{int(r['n (seed mean)']):,}".replace(",", "{,}"), r["AUROC"], r["recall"], r["FPR"]] for _, r in sl.iterrows()], "llrrrr")

runs = pd.read_csv(R + "transfer_runs_v2.csv")
runs = runs[(runs.featset == "all") & runs.target.str.startswith("PhishTank")]
g = runs.groupby(["variant", "model"]).recall.agg(["mean", "std"])  # same numbers as final_table_phishtank_recall.csv, fixed 2-decimal format
emit("phishtank_recall", ["Trained on"] + MODELS,
     [[v] + [f"{g.loc[(v, m), 'mean']:.2f}±{g.loc[(v, m), 'std']:.2f}" for m in MODELS] for v in ["PhiUSIIL/all", "GramBeddings/all", "GramBeddings/homepage", "PhreshPhish/all"]], "lrrrrr")

cv = pd.read_csv(R + "final_table_canonical.csv").set_index("model").loc[MODELS]
rows = [[m, f"{cv.loc[m, 'cross-source AUROC: raw']:.3f}", f"{cv.loc[m, 'cross-source AUROC: raw_no_scheme_no_www']:.3f}", f"{cv.loc[m, 'cross-source AUROC: canonical']:.3f}",
         f"{cv.loc[m, 'in-source AUROC: raw']:.3f}", f"{cv.loc[m, 'in-source AUROC: raw_no_scheme_no_www']:.3f}", f"{cv.loc[m, 'in-source AUROC: canonical']:.3f}"] for m in MODELS]
emit("canonical", ["Model", "Cross: raw", "Cross: no scheme/www", "Cross: canonical", "In-source: raw", "In-source: no scheme/www", "In-source: canonical"], rows, "lrrrrrr",
     size=r"\scriptsize\setlength{\tabcolsep}{3.5pt}")

# ---- Source discriminator and form profile
sd = pd.read_csv(R + "source_discriminator.csv").groupby(["cls", "pair", "featset"]).auroc.mean().unstack()
rows = [[c, p, f"{sd.loc[(c, p), 'all']:.3f}", f"{sd.loc[(c, p), 'no_scheme_no_www']:.3f}", f"{sd.loc[(c, p), 'homepage']:.3f}"] for c, p in sd.index]
emit("source_discriminator", ["Class", "Pair of sources", "All features", "No scheme, no www", "Homepages only"], rows, "llrrr")

sp = pd.read_csv(R + "source_profile.csv")
rows = []
for s in ["PhiUSIIL", "GramBeddings", "PhreshPhish", "PhishTank"]:
    for c in ("legit", "phish"):
        a = sp[(sp.source == s) & (sp.cls == c) & (sp.utype == "all")]
        h = sp[(sp.source == s) & (sp.cls == c) & (sp.utype == "homepage")]
        if len(a) and len(h):
            a, h = a.iloc[0], h.iloc[0]
            rows.append([s if c == "legit" or s == "PhishTank" else "", "legitimate" if c == "legit" else "phishing", f"{int(a.n):,}".replace(",", "{,}"),
                         f"{a.share_of_class_homepage:.2f}", f"{h.trailing_slash:.2f}", f"{h.www:.2f}", f"{h.https:.2f}", f"{a.https:.2f}"])
emit("source_profile", ["Source", "Class", "Rows", "Homepage share", "Trailing / (hp)", "www (hp)", "https (hp)", "https (all)"], rows, "llrrrrrr",
     size=r"\footnotesize\setlength{\tabcolsep}{4pt}")
# ---- Which features separate the sources (script 20): top two per class, pair and URL type
ti = pd.read_csv(R + "source_importance_top.csv")
rows = []
for (c, p), g in ti.groupby(["cls", "pair"], sort=False):
    cells = []
    for ut in ("homepage", "deep"):
        h = g[g.utype == ut].sort_values("rank")
        cells += [f"{h.auroc.iloc[0]:.2f}", ", ".join(h.feature.iloc[:2])] if len(h) else ["n/a", "n/a"]
    rows.append([c, p] + cells)
emit("source_importance", ["Class", "Pair of sources", "Homepage AUROC", "Top features, homepages", "Deep AUROC", "Top features, deep URLs"], rows, "llrlrl", size=r"\footnotesize\setlength{\tabcolsep}{4pt}")

# ---- PR-AUC with the phishing share of each target (PR-AUC depends on prevalence, so it is not comparable across targets)
pr = pd.read_csv(R + "transfer_runs_v2.csv")
pr = pr[(pr.featset == "all") & (pr.model == "HistGB")]
rows = []
for v in ["PhiUSIIL/all", "GramBeddings/all", "GramBeddings/homepage", "PhreshPhish/all"]:
    src = v.split("/")[0]
    for t, nm in [("source test", "in-source test")] + [(f"{o} all", o) for o in ("PhiUSIIL", "GramBeddings", "PhreshPhish") if o != src]:
        g = pr[(pr.variant == v) & (pr.target == t)]
        rows.append([v.replace("/all", "").replace("/homepage", " (homepage only)") if nm == "in-source test" else "", nm, f"{(g.pos / g.n).mean():.2f}",
                     f"{g.auroc.mean():.2f}±{g.auroc.std():.2f}", f"{g.pr_auc.mean():.2f}±{g.pr_auc.std():.2f}"])
emit("transfer_prauc", ["Trained on", "Tested on", "Phishing share", "AUROC", "PR-AUC"], rows, "llrrr", rule_after=(2, 5, 8))

# ---- Class and URL-type mix of every set used in Part B (seed 0, from the class-mix log)
cm = pd.read_csv(R + "transfer_class_mix_v2.csv")
rows = []
for v in ["PhiUSIIL/all", "GramBeddings/all", "GramBeddings/homepage", "PhreshPhish/all"]:
    src = v.split("/")[0]
    for s in ["train", "val", "source test"] + [f"{o} all" for o in ("PhiUSIIL", "GramBeddings", "PhreshPhish") if o != src]:
        r = cm[(cm.variant == v) & (cm.set == s)].iloc[0]
        rows.append([v if s == "train" else "", s, f"{int(r.n):,}".replace(",", "{,}"), f"{r.phish_share:.2f}", f"{r.homepage_share_phish:.2f}", f"{r.homepage_share_legit:.2f}"])
emit("class_mix", ["Trained on", "Set", "Rows", "Phishing share", "Homepage share, phishing", "Homepage share, legitimate"], rows, "llrrrr", size=r"\footnotesize\setlength{\tabcolsep}{4pt}", rule_after=(4, 9, 14))
print("wrote", T)
