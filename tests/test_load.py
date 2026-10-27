from pathlib import Path

import pandas as pd

from corpus.load import OUTPUT_COLUMNS, load_sources, parse_timestamps, read_raw, select_slice

FIXTURE = Path(__file__).parent / "fixtures" / "sample.csv"


def load_fixture():
    df = read_raw(FIXTURE, "test")
    return parse_timestamps(df)


def test_columns_follow_the_contract():
    config = {"paths": {"raw_dir": str(FIXTURE.parent)}, "sources": {"test": FIXTURE.name}}
    df, stats = load_sources(config)
    assert list(df.columns) == OUTPUT_COLUMNS
    assert stats["test"]["rows_read"] == 5


def test_ticker_is_cleaned():
    df, _ = load_fixture()
    assert df.loc[4, "ticker"] == "AAPL"          # " aapl" -> "AAPL"


def test_timestamps_are_utc():
    df, _ = load_fixture()
    assert str(df["ts_utc"].dt.tz) == "UTC"
    # 10:30 in New York summer (UTC-4) = 14:30 UTC
    assert df.loc[0, "ts_utc"] == pd.Timestamp("2020-06-05 14:30:54", tz="UTC")
    # 17:05 in New York winter (UTC-5) = 22:05 UTC
    assert df.loc[1, "ts_utc"] == pd.Timestamp("2020-01-15 22:05:00", tz="UTC")


def test_midnight_means_no_time():
    df, _ = load_fixture()
    assert df["has_time"].tolist() == [True, True, False, False, True]


def test_bad_date_is_counted_not_crashing():
    df, n_bad = load_fixture()
    assert n_bad == 1
    assert pd.isna(df.loc[3, "ts_utc"])


def test_select_slice():
    df, _ = load_fixture()
    out = select_slice(df, ["AAPL"], "2020-01-01", "2021-01-01")
    assert out["headline"].tolist() == ["Apple beats estimates"]
