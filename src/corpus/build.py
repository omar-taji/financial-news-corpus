"""
build.py: run the whole pipeline with one command, from the project root:

    python -m corpus.build

raw CSVs -> load -> slice -> clean -> normalize -> exact dedup -> near dedup -> save
"""

import hashlib
import json
from pathlib import Path

from corpus.dedup import remove_exact_duplicates, remove_near_duplicates
from corpus.load import load_config, load_sources, select_slice
from corpus.normalize import add_normalized, basic_clean

FINAL_COLUMNS = ["id", "ticker", "ts_utc", "has_time", "headline", "headline_norm",
                 "publisher", "source_file", "url", "suspect_encoding", "n_duplicates"]


def make_id(row):
    """Stable id: the same row always gets the same id, on every run."""
    key = f"{row['ticker']}|{row['headline_norm']}|{row['ts_utc'].isoformat()}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def main(config_path="config.yaml"):
    config = load_config(config_path)
    paths, d = config["paths"], config["dedup"]
    stats = {}

    print("1/6 loading raw files...")
    df, stats["load"] = load_sources(config)

    print("2/6 selecting the slice...")
    s = config["slice"]
    df = select_slice(df, s["tickers"], s["start"], s["end"])
    stats["slice"] = {"rows": len(df), "tickers": len(s["tickers"]),
                      "start": s["start"], "end": s["end"]}

    print("3/6 cleaning...")
    df, stats["clean"] = basic_clean(df)

    print("4/6 normalizing...")
    df = add_normalized(df)
    stats["normalize"] = {"suspect_encoding": int(df["suspect_encoding"].sum())}

    print("5/6 removing duplicates...")
    df, stats["exact_dedup"] = remove_exact_duplicates(df, d["window_days"])
    df, stats["near_dedup"] = remove_near_duplicates(df, d["window_days"],
                                                     d["shingle_size"], d["threshold"])
    stats["dedup_settings"] = d

    print("6/6 saving...")
    df["id"] = df.apply(make_id, axis=1)
    df = df[FINAL_COLUMNS].sort_values(["ts_utc", "ticker"]).reset_index(drop=True)

    out_dir = Path(paths["processed_dir"])
    out_dir.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_dir / "headlines.parquet", index=False)

    stats["final"] = {
        "rows": len(df),
        "per_ticker": df["ticker"].value_counts().to_dict(),
        "per_source": df["source_file"].value_counts().to_dict(),
        "share_with_time": round(float(df["has_time"].mean()), 4),
    }
    Path("reports").mkdir(exist_ok=True)
    with open("reports/stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, default=str)

    print(f"Done: {len(df)} headlines saved to {out_dir / 'headlines.parquet'}")
    return df, stats


if __name__ == "__main__":
    main()
