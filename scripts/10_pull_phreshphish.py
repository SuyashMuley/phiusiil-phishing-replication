"""Pull url, label and date for PhreshPhish (HF phreshphish/phreshphish) without downloading page HTML.

Reads each parquet shard's footer and only the url/label/date columns through HTTP range requests
(about 0.1-0.4 MB per shard instead of 55-400 MB). Needs pyarrow. Output: data/phreshphish/phreshphish_url_label_date.csv
Usage (from the project folder): .venv/bin/python scripts/10_pull_phreshphish.py [--limit N] [--out PATH]
The dataset is CC BY 4.0, for anti-phishing research only.
"""
import argparse
import io
import json
import os
import urllib.request

import pandas as pd
import pyarrow.parquet as pq

API = "https://datasets-server.huggingface.co/parquet?dataset=phreshphish/phreshphish"


class RangeFile(io.RawIOBase):
    """Read-only seekable file over HTTP range requests."""

    def __init__(self, url):
        self.url, self.pos, self.bytes_read = url, 0, 0
        self.size = int(urllib.request.urlopen(urllib.request.Request(url, method="HEAD")).headers["Content-Length"])

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        if n <= 0:
            return 0
        req = urllib.request.Request(self.url, headers={"Range": f"bytes={self.pos}-{self.pos + n - 1}"})
        data = urllib.request.urlopen(req).read()
        b[:len(data)] = data
        self.pos += len(data)
        self.bytes_read += len(data)
        return len(data)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="only the first N shards (smoke test)")
    ap.add_argument("--out", default="data/phreshphish/phreshphish_url_label_date.csv")
    args = ap.parse_args()
    shards = json.load(urllib.request.urlopen(API))["parquet_files"]
    shards = shards[:args.limit] if args.limit else shards
    parts = []
    for m in shards:
        f = RangeFile(m["url"])
        d = pq.ParquetFile(f).read(columns=["url", "label", "date"]).to_pandas()
        d["split"], d["shard"] = m["split"], m["filename"]
        parts.append(d)
        print(m["split"], m["filename"], len(d), f"{f.bytes_read / 1e3:.0f} kB", flush=True)
    df = pd.concat(parts, ignore_index=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    df.to_csv(args.out, index=False)
    print(len(df), "rows;", df.label.value_counts().to_dict(), "unique urls", df.url.nunique())
