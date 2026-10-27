# Data card: financial headlines corpus (P1)

**Output:** `data/processed/headlines.parquet`, 3,962 headlines, rebuilt with `python -m corpus.build`.
**Purpose:** unlabeled corpus of company news headlines with timestamps and tickers, for the market study of the financial sentiment project.

## Source
Kaggle, *Daily Financial News for 6000+ Stocks* (miguelaenlle), two files:

| File | Rows read | Unreadable dates | Rows with a real time |
|---|---|---|---|
| `raw_analyst_ratings.csv` (Benzinga) | 1,407,328 | 0 | 4.0% |
| `raw_partner_headlines.csv` (partner sites) | 1,845,559 | 0 | 0% |

License: see the Kaggle dataset page before redistributing. The raw data is not included in this repository.

## Selection
- Tickers: AAPL, MSFT, JPM, XOM, JNJ
- Window: 2019-01-01 to 2020-07-01 (the data actually ends on 2020-06-11)

## Processing funnel
| Step | Rows | Removed |
|---|---|---|
| Slice (tickers + window) | 4,008 | |
| Basic cleaning (missing date, ticker or headline) | 4,008 | 0 |
| Exact duplicates (same ticker, same normalized text, ≤ 2 days apart) | 3,967 | 41 (1.0%) |
| Near duplicates (same ticker, Jaccard ≥ 0.8 on character 5-grams, ≤ 2 days apart) | 3,962 | 5 (0.1%) |
| **Final** | **3,962** | **46 (1.1%)** |

Normalization (for matching only; the original headline is kept): Unicode NFKC, curly quotes and dashes unified, whitespace collapsed, lowercase. In each duplicate group the earliest headline is kept, and `n_duplicates` records how many copies it had.

## Choice of the near-duplicate threshold
Candidate pairs (same ticker, ≤ 2 days apart) were read by hand at each similarity level:

| Similarity | Typical pairs | Same story? |
|---|---|---|
| ≥ 0.8 | truncated copy; same title with "(Revised)"; same news reworded | yes, with one exception: daily roundups with different dates ("Top Upgrades, Downgrades For December 17" vs "19") |
| 0.7 – 0.8 | ratings from **different brokers** ("Credit Suisse Maintains Neutral on Exxon" vs "UBS Maintains Neutral on Exxon"); different market-mover lists; also some true rewordings | mixed |
| 0.6 – 0.7 | recurring templates ("52-Week Highs On Tuesday" vs "Thursday"); same podcast title with words reordered | mostly no |

**Decision: 0.8.** Below it, different analyst actions start being merged, which would delete real events. Known misses at 0.8: titles whose words are reordered ("Wall Street Breakfast: X" vs "X (Wall Street Breakfast Podcast)", about 0.7) stay as two rows; date-varying roundups can be merged by mistake.

Only 171 candidate pairs have a similarity between 0.4 and 1.0, so near-duplicates are rare in this slice: most republication is exact copying.

## Timestamp quality
- Only **37 of 3,962 headlines (0.9%)** have a real time of publication, all from the Benzinga file. All others are stored at midnight, meaning only the day is known.
- Consequence for the market study: it is impossible to tell whether a headline came before or after the 16:00 close. The conservative rule must be used: measure returns from day +1 to day +2.

## Text quality
- **35 headlines (0.9%) contain corrupted characters**, flagged in `suspect_encoding`. They come from GuruFocus, where zeros were replaced by ellipses upstream ("Invesco S&P 5…… Low" for "S&P 500"). They are kept and flagged, not repaired: the original text cannot be recovered reliably.

## Known biases and limitations
1. **Very uneven ticker coverage.** MSFT has **zero rows** in either file, so the final corpus has 4 tickers, not 5. AAPL appears only in 2020. JPM comes almost entirely from partner sites, and JNJ and XOM mostly from Benzinga. Final shares: JPM 59.2%, JNJ 16.6%, XOM 12.2%, AAPL 11.9%.
2. **The ticker is not always the subject.** Partner headlines filed under JPM include other banks (Comerica) and general market podcasts. The ticker column means "listed under", not "about".
3. **Templates and roundups.** Many Benzinga headlines are analyst-rating templates or daily lists ("Stocks That Hit 52-Week Highs"), which carry little company-specific information.
4. **Publisher mix.** Seeking Alpha 765, Zacks 589, Benzinga Newsdesk 557, GuruFocus 546 headlines: a few outlets dominate.
5. **Survivorship.** Tickers were chosen by name recognition today, which favors companies that did well.

## Recommendation
Re-select the tickers **from the data**: count headlines per ticker in the chosen window (`value_counts()`), keep tickers with enough coverage in both files, and check that each one exists in every year of the window.
