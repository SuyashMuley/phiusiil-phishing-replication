"""A1: URL-form profile by source, class and URL type (homepage vs deep). Descriptive only, no model.

Columns: share https, share with www, share ending in '/', share with a query string, share IP host, median URL length,
median path depth and the three most common final host labels (TLD-like). Output: results/source_profile.csv
Usage (from the project folder): PYTHONPATH=scripts .venv/bin/python scripts/12_source_profile.py
"""
import pandas as pd

from common import url_type

SRC = {"PhiUSIIL": "phiusiil", "GramBeddings": "gram_sample", "PhreshPhish": "phreshphish", "PhishTank": "phishtank_tranco"}
rows = []
for name, f in SRC.items():
    d = pd.read_pickle(f"data/cache/{f}.pkl")
    if name == "PhishTank":
        d = d[d.phish == 1]  # Tranco rows carry a synthetic https:// and are not used
    d = d.assign(utype=url_type(d.url), tld=d.url.str.extract(r"^[a-z][a-z0-9+.-]*://([^/?#:]+)", expand=False).str.rsplit(".", n=1).str[-1].str.lower())
    for cls, cn in ((1, "phish"), (0, "legit")):
        for ut in ("all", "homepage", "deep"):
            s = d[(d.phish == cls) & ((d.utype == ut) | (ut == "all"))]
            if len(s) == 0:
                continue
            top = s.tld.value_counts(normalize=True).head(3)
            rows.append(dict(source=name, cls=cn, utype=ut, n=len(s), share_of_class_homepage=(s.utype == "homepage").mean(),
                             https=s.is_https.mean(), www=s.has_www.mean(), trailing_slash=s.url.str.endswith("/").mean(),
                             has_query=(s.query_len > 0).mean(), is_ip=s.is_ip.mean(), med_len=s.url_len.median(),
                             med_path_depth=s.path_depth.median(), top_tlds=" ".join(f"{k}:{v:.2f}" for k, v in top.items())))
out = pd.DataFrame(rows)
out.to_csv("results/source_profile.csv", index=False)
pd.set_option("display.width", 250, "display.max_columns", 30)
print(out.round(3).to_string(index=False))
