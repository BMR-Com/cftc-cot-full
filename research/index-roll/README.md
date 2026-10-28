# Index-roll research dataset (ICE softs, CBOT grains/oilseeds, CME livestock)

Daily contract histories and CFTC positioning for cotton (CT), raw sugar (SB), arabica coffee (KC), cocoa (CC), corn (ZC), Chicago wheat (ZW), KC wheat (KE), soybeans (ZS), soybean meal (ZM), soybean oil (ZL), live cattle (LE) and lean hogs (HE), plus the code that lines them up around the index roll windows.

## data/
| File | Contents |
|---|---|
| `tv_contracts.csv.gz` | Every listed contract, daily close and volume, from TradingView (ICEUS). Columns: `symbol` (e.g. `CTH2027`), `date`, `close`, `volume`. CT HKNZ, SB HKNV, KC/CC HKNUZ; expiries 2000–2027, bars from 1998. |
| `cot_legacy.csv.gz` | CFTC legacy futures-and-options combined report for the four markets, 1995 onward (all columns as published). |
| `cot_disagg.csv.gz` | CFTC disaggregated futures-and-options combined report for the four markets, June 2006 onward. |
| `ags_contracts.csv.gz` | Same format as `tv_contracts`, for ZC, ZW, KE, ZS, ZM, ZL (CBOT) and LE, HE (CME), expiries 2000–2027. |
| `wasde/` | US balance sheets by report month (Cotton, Corn, Oilseed Soybean, Wheat), copied from wasde-analytics; May 2010 report onward. |
| `wasde_release_dates.csv` | WASDE release date for every report from Apr 2010 (from the wasde-analytics master file). |
| `psd_us.csv.gz` | USDA PSD US final balance sheets (cotton, corn, soybeans and products, wheat), 1960 onward. |
| `ags_cot_legacy.csv.gz`, `ags_cot_disagg.csv.gz` | CFTC legacy and disaggregated F&O combined reports for those eight markets. |

CFTC codes: cotton 033661, coffee 083731, sugar 080732, cocoa 073732, corn 002602, Chicago wheat 001602, KC wheat 001612, soybeans 005602, soybean meal 026603, soybean oil 007601, live cattle 057642, lean hogs 054642.

Market settings (index cycle, multiplier, unit, CFTC code, second roll, group) are in `MARKETS` in `code/rollcommon.py`. Index cycles follow the RICI Appendix A contract schedule.

## Roll windows used
For a contract delivering in month M:
- **Rogers (RICI):** business day before the last business day of M−2, the last business day of M−2, and the first business day of M−1.
- **GSCI:** business days 5–9 of M−1. Soybean meal and oil are not in the GSCI, so their second roll is BCOM's, business days 6–10.

Business days are taken from exchange trading days in the price file. The loader moves Sunday-dated bars to Monday (TradingView stamps ICE cotton Monday sessions as Sunday) and drops bad ticks, meaning prints more than 20% away from the contract's 11-day median.

## code/
| Script | What it does |
|---|---|
| `rollcommon.py` | Contract cycles, multipliers, the TradingView loader and contract chaining. |
| `build_events.py` | One row per roll event and series (spreads 1–3 and front-month price). Windows are the 20 days before the Rogers entry, the Rogers roll, and GSCI days 1–2, 1–3 and 1–5. Also records the spec net/OI and its trailing 3-year percentile. Writes `results/v2_events.csv`. |
| `stats.py` | Summary tables, unconditional and by positioning bucket. Writes `results/`. |
| `late_gsci.py` | Later in the GSCI/BCOM roll: long spread exited on days 2–5, and short spread entered at the close of day 4 or 5 and held 5 or 10 days. |
| `post_roll.py` | Long or short spread from GSCI day 3, 4 or 5 to the day before the front contract's first notice or expiry (market-specific exit rules are in the file header). |
| `newcrop_spread.py` | Old-crop/new-crop calendar spread entered at each May–Sep WASDE: short this year's new-crop contract, long next year's, with the short leg rolled at the Rogers or GSCI roll until the last old-crop first notice. Also an optional stop at the first later WASDE where new-crop S/U drops to the 30th percentile of 10 years or below. |
| `newcrop_stats.py` | Summary of `newcrop_spread.py` output by market, entry month and balance-sheet condition. |
| `controls.py` | The same windows shifted 1–3 months earlier, an era split and a curve-shape split. |
| `fetch_ags_tradingview_and_cot.py` | Refreshes the ags files, one market per run: `python fetch_ags_tradingview_and_cot.py ZC`, or `COT` for positioning. |
| `fetch_tradingview_and_cot.py` | Refreshes the softs files in `data/`. It must run on a GitHub Actions runner, because TradingView and the CFTC API are not reachable from Claude sessions. |

Run from `code/`: `python build_events.py && python stats.py && python controls.py`. `results/` is git-ignored, so outputs stay local.
