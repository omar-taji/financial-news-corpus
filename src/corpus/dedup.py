"""
dedup.py: remove duplicate headlines.

Two rows are only compared if they have the SAME ticker and were published
within `window_days` of each other. This is called "blocking". It does two jobs:
  - it avoids the template trap: "X Maintains Buy on AAPL" and "X Maintains Buy
    on MSFT" look alike but are different events (different tickers);
  - it avoids recurring headlines like "Stocks That Hit 52-Week Highs On Friday",
    which repeat every week but are new news each time (far apart in time);
  - it keeps the work small: we never compare all rows with all rows.

In every group of duplicates we keep the EARLIEST row: the first publication.
"""

import pandas as pd


# ---------------------------------------------------------------- similarity

def shingles(text, k=5):
    """Set of all overlapping k-character pieces of the text."""
    if len(text) <= k:
        return {text}
    return {text[i:i + k] for i in range(len(text) - k + 1)}


def jaccard(a, b):
    """Shared pieces / all pieces. 1.0 = identical sets, 0.0 = nothing in common."""
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------- grouping

class UnionFind:
    """
    Keeps track of groups. union(a, b) says "a and b are the same story";
    find(x) returns the representative of x's group. If A~B and B~C, then
    A, B and C all end up in one group.
    """

    def __init__(self, items):
        self.parent = {x: x for x in items}

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]   # shortcut, speeds up later finds
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.parent[max(ra, rb)] = min(ra, rb)   # smaller index (= earlier row) stays the root


# ---------------------------------------------------------------- candidate pairs

def candidate_pairs(df, window_days, k):
    """
    Yield (i, j, similarity) for every pair of rows with the same ticker,
    published at most `window_days` apart. Rows must be sorted by time.
    """
    window = pd.Timedelta(days=window_days)
    for _, group in df.groupby("ticker", sort=False):
        idx = group.index.to_list()
        times = group["ts_utc"].to_list()
        sets = [shingles(t, k) for t in group["headline_norm"]]
        for a in range(len(idx)):
            b = a + 1
            # rows are sorted by time, so we can stop as soon as we leave the window
            while b < len(idx) and times[b] - times[a] <= window:
                yield idx[a], idx[b], jaccard(sets[a], sets[b])
                b += 1


def similar_pairs(df, window_days=2, k=5, min_sim=0.5):
    """
    Table of pairs with similarity >= min_sim, most similar first.
    Use it in the notebook to READ pairs and choose the threshold.
    """
    df = df.sort_values("ts_utc").reset_index(drop=True)
    rows = [(i, j, s) for i, j, s in candidate_pairs(df, window_days, k) if s >= min_sim]
    pairs = pd.DataFrame(rows, columns=["i", "j", "similarity"])
    pairs["ticker"] = df.loc[pairs["i"], "ticker"].to_numpy()
    pairs["headline_a"] = df.loc[pairs["i"], "headline"].to_numpy()
    pairs["headline_b"] = df.loc[pairs["j"], "headline"].to_numpy()
    return pairs.sort_values("similarity", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------- dedup

def _dedup(df, window_days, k, threshold):
    """Group rows whose similarity >= threshold, keep the earliest of each group."""
    df = df.sort_values("ts_utc", kind="stable").reset_index(drop=True)
    uf = UnionFind(df.index)
    for i, j, sim in candidate_pairs(df, window_days, k):
        if sim >= threshold:
            uf.union(i, j)
    roots = pd.Series([uf.find(i) for i in df.index], index=df.index)
    keep = roots == df.index          # a row is kept if it is the root of its group
    df["n_duplicates"] = roots.value_counts().reindex(df.index, fill_value=1).to_numpy() - 1
    return df[keep].reset_index(drop=True), int((~keep).sum())


def remove_exact_duplicates(df, window_days=2):
    """Same ticker + same headline_norm + within the window."""
    # Exact duplicates are just the special case "similarity == 1 on the full text";
    # k=10**9 makes shingles() return the whole string as a single piece.
    out, removed = _dedup(df, window_days, k=10**9, threshold=1.0)
    return out.drop(columns="n_duplicates"), {"exact_removed": removed, "rows_out": len(out)}


def remove_near_duplicates(df, window_days=2, k=5, threshold=0.8):
    """Same ticker + Jaccard similarity >= threshold + within the window."""
    out, removed = _dedup(df, window_days, k, threshold)
    return out, {"near_removed": removed, "rows_out": len(out)}
