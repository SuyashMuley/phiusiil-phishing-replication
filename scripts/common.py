"""Shared loaders and the single URL-only feature extractor used for every dataset."""
import math
import re
from collections import Counter
from urllib.parse import urlsplit

import numpy as np
import pandas as pd
import tldextract

ext =tldextract.TLDExtract(suffix_list_urls=())  # offline: bundled snapshot
SUSPICIOUS = ("login", "verify", "account", "secure", "update", "signin",
              "password", "bank", "confirm", "support")
IP_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$|^0x[0-9a-f]+$", re.I)


def read_gram(name):
    # URLs can contain commas, so split each line on the first comma only (label,url)
    path = f"data/grambeddings/grambeddings_dataset_main/{name}.csv"
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\r\n").split(",", 1) for ln in f if ln.strip()]
    return pd.DataFrame(rows, columns=["c", "url"])


def load():
    """All datasets as DataFrame(url, phish) with 1=phishing, 0=legitimate."""
    p = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", usecols=["URL", "label"])
    p = pd.DataFrame({"url": p.URL, "phish": 1 - p.label})  # PhiUSIIL: 1=legit
    g = pd.concat([read_gram(n) for n in ("train", "test")])
    g = pd.DataFrame({"url": g.url, "phish": (g.c == "1").astype(int)})  # 1=Phish, 2=Legit
    t = pd.read_csv("data/external/phishtank_online_valid.csv", usecols=["url"])
    t = pd.DataFrame({"url": t.url, "phish": 1})
    return {"PhiUSIIL": p, "GramBeddings": g, "PhishTank": t}


def etld1(u):
    return ext(u).top_domain_under_public_suffix


def _entropy(s):
    if not s:
        return 0.0
    n = len(s)
    return -sum(c / n * math.log2(c / n) for c in Counter(s).values())


def extract_features(url):
    """URL-only features. Same function for every dataset; no dataset-specific inputs."""
    u = str(url).strip()
    try:
        p = urlsplit(u if "://" in u else "http://" + u)
        host = p.hostname or ""
        has_port = int(p.port is not None)
    except ValueError:
        p, host, has_port = urlsplit("http://invalid"), "", 0
    low = u.lower()
    n = max(len(u), 1)
    n_digits = sum(ch.isdigit() for ch in u)
    n_special = sum(not ch.isalnum() and ch not in "./-" for ch in u)
    e = ext(host) if host else None
    sub = e.subdomain if e else ""
    n_sub = len([s for s in sub.split(".") if s and s != "www"]) if sub else 0
    return {
        "url_len": len(u),
        "host_len": len(host),
        "path_len": len(p.path),
        "query_len": len(p.query),
        "n_dots": u.count("."),
        "n_hyphens": u.count("-"),
        "n_digits": n_digits,
        "digit_ratio": n_digits / n,
        "n_special": n_special,
        "n_at": u.count("@"),
        "n_pct": u.count("%"),
        "n_eq": u.count("="),
        "n_amp": u.count("&"),
        "n_params": len([q for q in p.query.split("&") if q]) if p.query else 0,
        "path_depth": p.path.count("/"),
        "n_subdomains": n_sub,
        "is_https": int(p.scheme == "https"),
        "has_www": int(host.startswith("www.")),
        "is_ip": int(bool(IP_RE.match(host))),
        "has_port": has_port,
        "entropy": _entropy(u),
        "susp_tokens": sum(low.count(t) for t in SUSPICIOUS),
    }


def featurize(urls):
    return pd.DataFrame([extract_features(u) for u in urls])


def metrics(y, p):
    """Threshold-free metrics plus FPR at the default 0.5 threshold and at 95% recall."""
    import numpy as np
    from sklearn.metrics import average_precision_score, f1_score, roc_auc_score, roc_curve
    if len(set(y)) < 2:
        return dict(auroc=np.nan, pr_auc=np.nan, f1=np.nan, fpr_at_0_5=np.nan, fpr_at_95rec=np.nan)
    fpr, tpr, _ = roc_curve(y, p)
    pred = p >= 0.5
    return dict(
        auroc=roc_auc_score(y, p),
        pr_auc=average_precision_score(y, p),
        f1=f1_score(y, pred),
        fpr_at_0_5=(pred & (y == 0)).sum() / max((y == 0).sum(), 1),
        fpr_at_95rec=fpr[np.searchsorted(tpr, 0.95)],
    )


# ---- Part B helpers: matched sampling, domain-disjoint splits, validation-fixed thresholds
# Frames here have columns url, phish (1 = phishing), dom (registered domain) plus features.

def url_type(urls):
    """'homepage' if nothing follows the host (no path, query or fragment), else 'deep'."""
    return np.where(pd.Series(list(urls)).str.match(r"^[a-z][a-z0-9+.-]*://[^/?#]+/?$", case=False), "homepage", "deep")


def class_mix(df, name=""):
    """One row: size, phishing share, homepage share per class. Log this for every train and test set."""
    t = url_type(df.url)
    ph = df.phish.values == 1
    return dict(set=name, n=len(df), phish_share=ph.mean(),
                homepage_share_phish=(t[ph] == "homepage").mean() if ph.any() else np.nan,
                homepage_share_legit=(t[~ph] == "homepage").mean() if (~ph).any() else np.nan)


def matched_sample(df, n, phish_rate, seed, url_kind=None):
    """n rows with an exact phishing share, drawn without replacement. url_kind='deep'/'homepage' restricts both classes."""
    if url_kind:
        df = df[url_type(df.url) == url_kind]
    n_p = int(round(n * phish_rate))
    parts = []
    for k, m in ((1, n_p), (0, n - n_p)):
        pool = df[df.phish == k]
        if len(pool) < m:
            raise ValueError(f"need {m} rows with phish={k}, only {len(pool)} available (url_kind={url_kind})")
        parts.append(pool.sample(m, random_state=seed))
    return pd.concat(parts).sample(frac=1, random_state=seed)


def domain_split(df, seed, val=0.15, test=0.15):
    """train/val/test frames that share no registered domain (df.dom)."""
    from sklearn.model_selection import GroupShuffleSplit
    rest, te = next(GroupShuffleSplit(1, test_size=test, random_state=seed).split(df, groups=df.dom))
    rest_df = df.iloc[rest]
    tr, va = next(GroupShuffleSplit(1, test_size=val / (1 - test), random_state=seed).split(rest_df, groups=rest_df.dom))
    return rest_df.iloc[tr], rest_df.iloc[va], df.iloc[te]


def drop_seen(target, seen):
    """Remove target rows whose URL or registered domain appears in the training frame."""
    return target[~target.url.isin(set(seen.url)) & ~target.dom.isin(set(seen.dom))]


def val_threshold(y_val, p_val, recall=0.95):
    """Threshold fixed on SOURCE validation data only: at least `recall` of validation phishing scores >= it."""
    pos = np.asarray(p_val)[np.asarray(y_val) == 1]
    return float(np.quantile(pos, 1 - recall, method="lower"))


def at_threshold(y, p, thr):
    """Recall, FPR, precision at a fixed threshold. fpr is NaN when the set has no legitimate rows (PhishTank)."""
    y, p = np.asarray(y), np.asarray(p)
    pred = p >= thr
    pos, neg = y == 1, y == 0
    return dict(thr=thr,
                recall=(pred & pos).sum() / pos.sum() if pos.any() else np.nan,
                fpr=(pred & neg).sum() / neg.sum() if neg.any() else np.nan,
                precision=(pred & pos).sum() / pred.sum() if pred.any() else np.nan,
                flagged=pred.mean())


def transfer_metrics(y, p, thr):
    """Threshold-free metrics (NaN if one class) plus the validation-fixed-threshold operating point."""
    from sklearn.metrics import average_precision_score, roc_auc_score
    two = len(set(np.asarray(y))) == 2
    return dict(auroc=roc_auc_score(y, p) if two else np.nan,
                pr_auc=average_precision_score(y, p) if two else np.nan,
                **at_threshold(y, p, thr))
