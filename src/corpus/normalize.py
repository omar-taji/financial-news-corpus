"""
normalize.py: remove unusable rows and add a normalized copy of each headline.

The original 'headline' column is NEVER modified. We add:

    headline_norm     str    lowercase, cleaned version, used ONLY for matching
    suspect_encoding  bool   True if the headline contains broken characters
"""

import re
import unicodedata

# Characters that look alike but have different code points -> one standard form.
# str.maketrans builds a table that str.translate uses to replace characters.
LOOKALIKES = str.maketrans({
    "‘": "'", "’": "'",     # ‘ ’  curly single quotes
    "“": '"', "”": '"',     # “ ”  curly double quotes
    "–": "-", "—": "-",     # – —  en dash, em dash
    " ": " ",                    # non-breaking space
})

# Signs of text that was corrupted before we received it ("mojibake").
# We do not try to repair it (the original is lost); we only flag it.
SUSPECT = re.compile(
    "|".join([
        r"â€",          # UTF-8 read as Windows-1252, e.g. "â€™" instead of "’"
        r"Ã[\x80-\xbf]", # same problem on accented letters, e.g. "Ã©" instead of "é"
        "�",        # � the "replacement character": a byte that could not be decoded
        r"…{2,}",        # repeated ellipsis, e.g. "$5…… Million"
    ])
)


def normalize_headline(text):
    """Return the matching version of ONE headline (a plain string)."""
    text = unicodedata.normalize("NFKC", text)   # unify Unicode forms (ﬁ -> fi, etc.)
    text = text.translate(LOOKALIKES)            # curly quotes -> straight, dashes -> "-"
    text = re.sub(r"\s+", " ", text).strip()     # any run of spaces/tabs/newlines -> one space
    return text.lower()


def basic_clean(df):
    """
    Drop rows we cannot use. Returns (new_table, stats).
    stats counts how many rows were dropped for each reason.
    """
    df = df.copy()
    df["headline"] = df["headline"].str.strip()
    stats = {"rows_in": len(df)}

    no_date = df["ts_utc"].isna()
    no_ticker = df["ticker"].isna() | (df["ticker"] == "")
    no_headline = df["headline"].isna() | (df["headline"] == "")

    stats["dropped_no_date"] = int(no_date.sum())
    stats["dropped_no_ticker"] = int((no_ticker & ~no_date).sum())
    stats["dropped_no_headline"] = int((no_headline & ~no_date & ~no_ticker).sum())

    df = df[~(no_date | no_ticker | no_headline)].reset_index(drop=True)
    stats["rows_out"] = len(df)
    return df, stats


def add_normalized(df):
    """Add the 'headline_norm' and 'suspect_encoding' columns."""
    df = df.copy()
    df["headline_norm"] = df["headline"].map(normalize_headline)
    df["suspect_encoding"] = df["headline"].str.contains(SUSPECT, regex=True)
    return df
