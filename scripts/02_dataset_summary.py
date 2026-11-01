"""Load all datasets to a common schema (url, phish: 1=phish 0=legit), print summary + overlap."""
import pandas as pd, tldextract

ext = tldextract.TLDExtract(suffix_list_urls=())  # offline: bundled snapshot


def read_gram(name):
    # URLs can contain commas, so split each line on the first comma only (label,url)
    path = f"data/grambeddings/grambeddings_dataset_main/{name}.csv"
    with open(path, encoding="utf-8", errors="replace") as f:
        rows = [ln.rstrip("\r\n").split(",", 1) for ln in f if ln.strip()]
    return pd.DataFrame(rows, columns=["c", "url"])


def load():
    p = pd.read_csv("data/PhiUSIIL_Phishing_URL_Dataset.csv", usecols=["URL", "label"])
    p = pd.DataFrame({"url": p.URL, "phish": 1 - p.label})  # PhiUSIIL: 1=legit
    g = pd.concat([read_gram(n) for n in ("train", "test")])
    g = pd.DataFrame({"url": g.url, "phish": (g.c == "1").astype(int)})  # 1=Phish, 2=Legit
    t = pd.read_csv("data/external/phishtank_online_valid.csv", usecols=["url"])
    t = pd.DataFrame({"url": t.url, "phish": 1})
    return {"PhiUSIIL": p, "GramBeddings": g, "PhishTank": t}


def etld1(u):
    return ext(u).top_domain_under_public_suffix


if __name__ == "__main__":
    D = load()
    for k, d in D.items():
        print(f"{k:13s} total {len(d):7d} phish {d.phish.sum():7d} legit {(d.phish == 0).sum():7d} "
              f"dupURL {d.url.duplicated().sum():6d} missing {d.url.isna().sum()}")
        d["dom"] = d.url.dropna().map(etld1)
    names = list(D)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = D[names[i]], D[names[j]]
            ua, ub = set(a.url.dropna()), set(b.url.dropna())
            da, db = set(a.dom.dropna()), set(b.dom.dropna())
            print(f"{names[i]} <-> {names[j]}: URL overlap {len(ua & ub)} "
                  f"({len(ua & ub) / min(len(ua), len(ub)):.2%}) | "
                  f"eTLD+1 overlap {len(da & db)} ({len(da & db) / min(len(da), len(db)):.2%})")
