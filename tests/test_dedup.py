import pandas as pd

from corpus.dedup import (jaccard, remove_exact_duplicates, remove_near_duplicates,
                          shingles, similar_pairs)


def make_df(rows):
    df = pd.DataFrame(rows, columns=["ticker", "ts", "headline"])
    df["ts_utc"] = pd.to_datetime(df.pop("ts"), utc=True)
    df["headline_norm"] = df["headline"].str.lower()
    return df


def test_jaccard_values():
    assert jaccard(shingles("apple rises"), shingles("apple rises")) == 1.0
    assert jaccard(shingles("aaaaa"), shingles("bbbbb")) == 0.0


def test_exact_keeps_earliest():
    df = make_df([
        ("AAPL", "2020-01-01 15:00", "Apple beats"),
        ("AAPL", "2020-01-01 10:00", "Apple beats"),   # earlier copy
    ])
    out, stats = remove_exact_duplicates(df, window_days=2)
    assert len(out) == 1 and stats["exact_removed"] == 1
    assert out.loc[0, "ts_utc"] == pd.Timestamp("2020-01-01 10:00", tz="UTC")


def test_same_headline_far_apart_is_kept():
    # recurring headline, one week apart: two different news items
    df = make_df([
        ("AAPL", "2020-01-03", "Stocks that hit 52-week highs on Friday"),
        ("AAPL", "2020-01-10", "Stocks that hit 52-week highs on Friday"),
    ])
    out, _ = remove_exact_duplicates(df, window_days=2)
    assert len(out) == 2


def test_template_on_other_ticker_is_kept():
    df = make_df([
        ("AAPL", "2020-01-01", "Morgan Stanley Maintains Overweight on AAPL"),
        ("MSFT", "2020-01-01", "Morgan Stanley Maintains Overweight on MSFT"),
    ])
    out, _ = remove_near_duplicates(df, window_days=2, k=5, threshold=0.8)
    assert len(out) == 2


def test_near_duplicates_are_grouped():
    df = make_df([
        ("AAPL", "2020-01-01 10:00", "Apple reports record quarterly revenue of $91.8 billion"),
        ("AAPL", "2020-01-01 11:00", "Apple reports record quarterly revenue of $91.8 billion."),
        ("AAPL", "2020-01-01 12:00", "Apple reports record quarterly revenue of $91.8bn"),
        ("AAPL", "2020-01-01 13:00", "Tim Cook to step down"),
    ])
    out, stats = remove_near_duplicates(df, window_days=2, k=5, threshold=0.8)
    assert len(out) == 2
    assert out.loc[0, "n_duplicates"] == 2


def test_similar_pairs_table():
    df = make_df([
        ("AAPL", "2020-01-01 10:00", "Apple beats estimates"),
        ("AAPL", "2020-01-01 11:00", "Apple beats estimates!"),
    ])
    pairs = similar_pairs(df, min_sim=0.5)
    assert len(pairs) == 1 and pairs.loc[0, "similarity"] > 0.8
