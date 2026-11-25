"""B1 (Part A): final tables for the paper reproduction, computed from the per-run CSVs. Writes only NEW files:
results/final_partA_tables.md and results/final_partA_{table5,table6,ablation,table3,table7}.csv. Reads results/repro_*.csv and results/table3_seed*.csv.
It also cross-checks its means against results/repro_ablation_summary.csv and results/table3_summary.csv and prints any mismatch (> 5e-4).
Conventions as in script 05/09: label 1 = legitimate is the positive class (the paper's convention); shuffled = row orders with seeds 1-4,
file = the dataset's own order (seed 0). Std is the sample std (ddof=1) over runs.
Usage (from the project folder): .venv/bin/python scripts/17_final_table_partA.py
"""
import glob

import numpy as np
import pandas as pd

R = "results/"
PROFILES = ["LowSecurity", "BestSecurity", "HighSecurity"]
CFG = {"all": "", "drop USI": "_drop-usi", "drop page content": "_drop-page", "drop USI and page content": "_drop-usi+page"}
bad = []


def read(kind, order, cfgsuffix):
    if order == "file":
        return [pd.read_csv(f"{R}repro_{kind}_file_s0{cfgsuffix}.csv").set_index("profile")]
    return [pd.read_csv(f"{R}repro_{kind}_shuffle_s{s}{cfgsuffix}.csv").set_index("profile") for s in (1, 2, 3, 4)]


def ms(vals, d=4):
    v = np.asarray(vals, float)
    return f"{v.mean():.{d}f} ({v.std(ddof=1):.{d}f})" if len(v) > 1 else f"{v[0]:.{d}f}"


# ---- Table 5: profiles, ours (file order and shuffled) vs paper
file5, shuf5 = read("table5", "file", "")[0], read("table5", "shuffle", "")
rows = []
for p in PROFILES:
    for m, nm in (("accuracy", "accuracy"), ("precision", "precision"), ("sensitivity", "sensitivity"), ("f1", "F1"), ("mcc", "MCC")):
        rows.append({"profile": p, "metric": nm, "ours, file order": f"{file5.loc[p, m]:.4f}", "ours, shuffled (4 runs)": ms([s.loc[p, m] for s in shuf5]),
                     "paper": f"{file5.loc[p, 'paper_' + m]:.4f}"})
t5 = pd.DataFrame(rows)
t5.to_csv(R + "final_partA_table5.csv", index=False)

# ---- Table 6: confusion counts
file6, shuf6 = read("table6", "file", "")[0], read("table6", "shuffle", "")
rows = []
for p in PROFILES:
    for c in ("TP", "TN", "FP", "FN"):
        v = [s.loc[p, c] for s in shuf6]
        rows.append({"profile": p, "cell": c, "ours, file order": int(file6.loc[p, c]), "ours, shuffled mean (sd)": f"{np.mean(v):.0f} ({np.std(v, ddof=1):.0f})",
                     "paper": int(file6.loc[p, "paper_" + c])})
t6 = pd.DataFrame(rows)
t6.to_csv(R + "final_partA_table6.csv", index=False)

# ---- Ablation: BestSecurity under feature-group removal (+ cross-check with repro_ablation_summary.csv)
summ = pd.read_csv(R + "repro_ablation_summary.csv")
key = {"all": "all", "drop USI": "usi", "drop page content": "page", "drop USI and page content": "usi+page"}
rows = []
for name, suf in CFG.items():
    f5, s5, s6 = read("table5", "file", suf)[0], read("table5", "shuffle", suf), read("table6", "shuffle", suf)
    nfeat = int(pd.read_csv(f"{R}repro_features_file_s0{suf}.csv").kept_final.sum())
    for m in ("accuracy", "f1"):
        mean = np.mean([s.loc["BestSecurity", m] for s in s5])
        ref = float(summ[(summ.cfg == key[name]) & (summ.order == "shuffle") & (summ.profile == "BestSecurity")][m].iloc[0].split()[0])
        if abs(mean - ref) > 5e-4:
            bad.append(f"ablation {name} {m}: ours {mean:.4f} vs summary {ref:.4f}")
    rows.append({"features": name, "n features after selection": nfeat,
                 "accuracy, file order": f"{f5.loc['BestSecurity', 'accuracy']:.4f}",
                 "accuracy, shuffled (4 runs)": ms([s.loc["BestSecurity", "accuracy"] for s in s5]),
                 "F1, shuffled": ms([s.loc["BestSecurity", "f1"] for s in s5]),
                 "MCC, shuffled": ms([s.loc["BestSecurity", "mcc"] for s in s5]),
                 "FP / FN (shuffled mean)": f"{np.mean([s.loc['BestSecurity', 'FP'] for s in s6]):.0f} / {np.mean([s.loc['BestSecurity', 'FN'] for s in s6]):.0f}"})
tab = pd.DataFrame(rows)
tab.to_csv(R + "final_partA_ablation.csv", index=False)

# ---- Table 3: batch baselines, 5 seeds, selected (43) vs url_only (21) vs paper (+ cross-check with table3_summary.csv)
t3s = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(R + "table3_seed*.csv"))])
ref = pd.read_csv(R + "table3_summary.csv")
paper = ref.drop_duplicates("model").set_index("model")[["paper_accuracy", "paper_f1"]]
rows = []
for m in paper.index:
    r = {"model": m, "paper accuracy": paper.loc[m, "paper_accuracy"], "paper F1": paper.loc[m, "paper_f1"]}
    for fs, lab in (("selected", "selected (43)"), ("url_only", "URL-only (21)")):
        g = t3s[(t3s.featset == fs) & (t3s.model == m)]
        r[f"accuracy, {lab}"], r[f"F1, {lab}"] = ms(g.accuracy, 5), ms(g.f1, 5)
        refv = float(ref[(ref.featset == fs) & (ref.model == m)].accuracy.iloc[0].split()[0])
        if abs(g.accuracy.mean() - refv) > 5e-4:
            bad.append(f"table3 {fs} {m}: ours {g.accuracy.mean():.5f} vs summary {refv:.5f}")
    r["n seeds"] = t3s[t3s.model == m].seed.nunique()
    rows.append(r)
t3 = pd.DataFrame(rows)
t3.to_csv(R + "final_partA_table3.csv", index=False)

# ---- Table 7: pre-training, sequential vs random split vs paper
sq, rd = pd.read_csv(R + "repro_table7_sequential_file_s0.csv"), pd.read_csv(R + "repro_table7_random_file_s0.csv")
t7 = pd.DataFrame({"pre-train share": (sq.pretrain * 100).round().astype(int).astype(str) + "%", "paper accuracy": sq.paper_accuracy.round(5),
                   "ours, sequential split": sq.accuracy.round(5), "ours, random split": rd.accuracy.round(5),
                   "gap sequential": (sq.accuracy - sq.paper_accuracy).round(5), "gap random": (rd.accuracy - rd.paper_accuracy).round(5)})
t7.to_csv(R + "final_partA_table7.csv", index=False)
mae = lambda c: float(np.abs(t7[c]).mean())

with open(R + "final_partA_tables.md", "w") as f:
    f.write("# Part A final tables (auto-generated by scripts/17_final_table_partA.py)\n\nLabel 1 = legitimate is the positive class (the paper's convention). Single run in the dataset's own row order, and 4 runs over shuffled row orders (mean, sample sd). The paper's row order is not stated.\n")
    for title, d in (("Table 5. Voting profiles (accuracy, precision, sensitivity, F1, MCC)", t5), ("Table 6. Confusion counts", t6),
                     ("Ablation. BestSecurity with feature groups removed (selection re-run after each removal)", tab),
                     ("Table 3. Batch baselines on a held-out stratified 80/20 split (accuracy and F1, mean (sd) over 5 seeds)", t3),
                     ("Table 7. BestSecurity accuracy after pre-training on the first p% (incremental part only)", t7)):
        f.write(f"\n## {title}\n\n{d.to_markdown(index=False)}\n")
    f.write(f"\nTable 7 mean absolute gap to the paper: sequential {mae('gap sequential'):.4f}, random {mae('gap random'):.4f}.\n")
print("tables written; Table 7 MAE seq/random:", round(mae("gap sequential"), 4), round(mae("gap random"), 4))
print("cross-check mismatches:", bad if bad else "none")
