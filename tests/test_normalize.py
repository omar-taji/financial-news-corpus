import pandas as pd

from corpus.normalize import add_normalized, basic_clean, normalize_headline


def test_curly_quotes_and_case():
    assert normalize_headline("Apple’s Q3 Beat") == "apple's q3 beat"


def test_whitespace_is_collapsed():
    assert normalize_headline("  too   many\n spaces ") == "too many spaces"


def test_nfkc_ligature():
    assert normalize_headline("ﬁnance") == "finance"      # "ﬁnance" with the ﬁ ligature


def test_idempotent():
    once = normalize_headline("Apple’s  “Big” Day – Q3")
    assert normalize_headline(once) == once


def make_df():
    return pd.DataFrame({
        "headline": ["Apple’s day", "   ", "Agilent prices $5…… Million", "Ok"],
        "ticker": ["AAPL", "MSFT", "A", None],
        "ts_utc": pd.to_datetime(["2020-01-01", "2020-01-01", "2020-01-01", "2020-01-01"], utc=True),
    })


def test_basic_clean_drops_and_counts():
    df, stats = basic_clean(make_df())
    assert len(df) == 2
    assert stats["dropped_no_headline"] == 1
    assert stats["dropped_no_ticker"] == 1


def test_original_headline_is_kept_and_suspect_flagged():
    df, _ = basic_clean(make_df())
    df = add_normalized(df)
    assert df.loc[0, "headline"] == "Apple’s day"     # unchanged
    assert df.loc[0, "headline_norm"] == "apple's day"
    assert df["suspect_encoding"].tolist() == [False, True]
