from pathlib import Path
import pandas as pd
import yaml

OUTPUT_COLUMNS = ["headline", "ticker", "publisher", "url", "ts_utc","has_time","source_file"]

RENAME={"headline":"headline","stock":"ticker","publisher":"publisher","url":"url","date":"date_raw"}

def load_config(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def read_raw(path, source_name):
    df=pd.read_csv(path, usecols=lambda col: col in RENAME, dtype=str)

    df=df.rename(columns=RENAME)
    df["ticker"]=df["ticker"].str.strip().str.upper()
    df["source_file"]=source_name
    return df

def parse_timestamps(df, default_tz="America/New_York"):
    df =df.copy()
    raw=df["date_raw"].str.strip()

    time_part = raw.str.extract(r"(\d{2}:\d{2}(?::\d{2})?)", expand=False)
    df["has_time"] = time_part.notna() & ~time_part.isin(["00:00", "00:00:00"])

    has_offset = raw.str.contains(r"(?:[+-]\d{2}:?\d{2}|Z)$", regex=True, na=False)
 
    ts = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

    ts[has_offset] = pd.to_datetime(raw[has_offset], utc=True, format="ISO8601", errors="coerce")
    naive = pd.to_datetime(raw[~has_offset], format="ISO8601", errors="coerce")
    ts[~has_offset] = (naive.dt.tz_localize(default_tz, ambiguous="NaT",nonexistent="NaT").dt.tz_convert("UTC"))

    df["ts_utc"] = ts
    n_bad = int(ts.isna().sum())
    return df.drop(columns="date_raw"), n_bad

def load_sources(config):
    
    raw_dir = Path(config["paths"]["raw_dir"])
    tables, stats = [], {}
 
    for source_name, file_name in config["sources"].items():
        df = read_raw(raw_dir / file_name, source_name)
        df, n_bad = parse_timestamps(df, config.get("timezone", "America/New_York"))
        stats[source_name] = {
            "rows_read": len(df),
            "bad_dates": n_bad,
            "share_without_time": round(float((~df["has_time"]).mean()), 4),
        }
        tables.append(df)
 
    combined = pd.concat(tables, ignore_index=True)[OUTPUT_COLUMNS]
    return combined, stats

def select_slice(df, tickers, start, end):
    
    start = pd.Timestamp(start, tz="UTC")
    end = pd.Timestamp(end, tz="UTC")
    keep = df["ticker"].isin(tickers) & (df["ts_utc"] >= start) & (df["ts_utc"] < end)
    return df[keep].reset_index(drop=True)


 
