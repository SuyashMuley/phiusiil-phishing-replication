"""A3: canonical-URL feature caches. For every cached source, add `curl` (canonical URL) and recompute the 22 features on it.

Canonical form: strip, lowercase, drop the scheme, drop a leading 'www.', drop one trailing '/'. This removes formatting
that differs by collection pipeline (see results/source_profile.csv) so that what is left is host and path content.
Writes data/cache/<name>_canon.pkl next to each existing cache (same rows, same `url`, `dom`, `phish`; features recomputed).
Note is_https and has_www become constant 0 (no scheme to read). Usage: PYTHONPATH=scripts .venv/bin/python scripts/14_build_canonical_cache.py
"""
import re
import time

import pandas as pd

from common import featurize

SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*://")


def canonical(u):
    u = str(u).strip().lower()
    u = SCHEME.sub("", u)
    u = re.sub(r"^www\.", "", u)
    return u[:-1] if u.endswith("/") else u


if __name__ == "__main__":
    for name in ("phiusiil", "gram_sample", "phreshphish", "phishtank_tranco"):
        t0 = time.time()
        d = pd.read_pickle(f"data/cache/{name}.pkl")
        keep = [c for c in ("url", "phish", "dom") if c in d.columns]
        base = d[keep].reset_index(drop=True)
        base["curl"] = base.url.map(canonical)
        out = pd.concat([base, featurize(base.curl)], axis=1)
        out.to_pickle(f"data/cache/{name}_canon.pkl")
        print(name, out.shape, f"{time.time() - t0:.0f}s; e.g. {base.url.iloc[0]!r} -> {base.curl.iloc[0]!r}", flush=True)
