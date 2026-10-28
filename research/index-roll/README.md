# Index-roll research dataset (ICE softs)

Daily contract histories and CFTC positioning for cotton (CT), raw sugar (SB), arabica coffee (KC) and cocoa (CC), plus the code that lines them up around the index roll windows.

## data/
| File | Contents |
|---|---|
| `tv_contracts.csv.gz` | Every listed contract, daily close and volume, from TradingView (ICEUS). Columns: `symbol` (e.g. `CTH2027`), `date`, `close`, `volume`. CT HKNZ, SB HKNV, KC/CC HKNUZ; expiries 2000–2027, bars from 1998. |
| `cot_legacy.csv.gz` | CFTC legacy futures-and-options combined report for the four markets, 1995 onward (all columns as published). |
| `cot_disagg.csv.gz` | CFTC disaggregated futures-and-options combined report for the four markets, June 2006 onward. |

CFTC codes: cotton 033661, coffee 083731, sugar 080732, cocoa 073732.

## Roll windows used
For a contract delivering in month M:
- **Rogers (RICI):** business day before the last business day of M−2, the last business day of M−2, and the first business day of M−1.
- **GSCI:** business days 5–9 of M−1 (BCOM: 6–10).

Business days are taken from exchange trading days in the price file.

## code/
| Script | What it does |
|---|---|
| `rollcommon.py` | Contract cycles, multipliers, the TradingView loader and contract chaining. |
| `build_events.py` | One row per roll event and series (spreads 1–3 and front-month price). Windows are the 20 days before the Rogers entry, the Rogers roll, and GSCI days 1–2, 1–3 and 1–5. Also records the spec net/OI and its trailing 3-year percentile. Writes `results/v2_events.csv`. |
| `stats.py` | Summary tables, unconditional and by positioning bucket. Writes `results/`. |
| `controls.py` | The same windows shifted 1–3 months earlier, an era split and a curve-shape split. |
| `fetch_tradingview_and_cot.py` | Refreshes `data/`. It must run on a GitHub Actions runner, because TradingView and the CFTC API are not reachable from Claude sessions. |

Run from `code/`: `python build_events.py && python stats.py && python controls.py`. `results/` is git-ignored, so outputs stay local.
