# BMR-Com · COT Positioning Desk

**Weekly CFTC positioning, price technicals and systematic trade ideas for Bloomberg Commodity Index (BCOM) markets, with a softs focus (cocoa, coffee, sugar, cotton).**

🔗 **Live dashboard:** https://bmr-com.github.io/cftc-cot-full/

The question it answers each week: *where are speculators and commercials positioned in each market relative to their own history, what changed this week, and does price agree?* It turns the raw CFTC report into a written desk brief, a positioning monitor and rules-based trade ideas. It updates itself every Friday after the CFTC release, with no manual steps.

![Softs focus](docs/softs.png)

---

## What's on the dashboard

| Section | What it shows |
|---|---|
| **Softs Focus** | Cocoa, coffee, sugar and cotton side by side: managed-money net and weekly change, COT index, **old-crop vs new-crop** positioning, price trend, producer/merchant percentile and the current trade idea. |
| **COT Desk Brief** | A written weekly read: breadth of spec flow, sector rotation, biggest buying and selling (sized as σ moves), crowding, contrarian setups and a risk map. One click copies it as plain text for notes or client emails. |
| **Trade Ideas** | Systematic long/short ideas with reference price on the actual contract (e.g. CTZ26), a 2×ATR stop, a 2R target, size and a full rationale. Includes a watchlist of positioning setups waiting for price confirmation and a scorecard covering all 21 markets. |
| **Positioning Monitor** | Every market ranked by setup score: regime, net position, w/w change, flow σ, driver (new buying / short covering / long liquidation / fresh shorting), 52-week sparkline, COT index, commercial percentile and a one-line desk read. |
| **Scatter** | Commercials vs funds percentile maps (contracts and % of open interest), plus "crowded and still adding vs crowded and exiting". |
| **Seasonality** | Weekly positioning by year against a 5-year range and average, for any market or basket, with crop-year panels for grains and softs. |
| **COT Analyzer / Custom Formula** | Full weekly history for one market across all four trader categories and crop years, plus a formula builder for custom positioning ratios. |

![Desk brief](docs/desk-brief.png)

---

## Methodology

**Positioning (CFTC Disaggregated, futures & options combined)**
- **COT index:** where the managed-money net position sits between its low (0) and high (100) over the look-back (1y / 3y / 5y / since 2006).
- **Flow σ:** this week's change in net position divided by the standard deviation of weekly changes over the last 3 years, so moves are comparable across markets.
- **Driver:** the weekly change split into its gross components, so "net +5k" becomes "short covering 4k + new buying 1k".
- **Commercial divergence:** producer/merchant net percentile against managed money; funds and commercials at opposite extremes is flagged.
- **Setup score (−100 to +100):** contrarian crowding, plus commercial confirmation, plus whether flow has started to turn. It is penalised while flow is still running hard in the crowded direction, so a crowded short that is still being sold is not yet a long setup.

**Trade ideas: research rules first, positioning second**
1. **Trend** (time-series momentum: Moskowitz–Ooi–Pedersen, Baltas). The sign of the 12-month return, confirmed by the 6-month return and price vs the 200-day average. Partial confirmation means half weight.
2. **Carry** (Gorton–Hayashi–Rouwenhorst, Erb–Harvey). Front contract vs the same month next year, annualised. Ignored for Nat Gas, Live Cattle and Lean Hogs because their curves are seasonal (Fama–French). Trend and carry agree: full size. Trend alone: half size. They conflict: flat.
3. **Sizing.** Inverse volatility with a 10% vol target per full position. All sizes are halved in an equity risk-off regime (S&P 500 below its 200-day and VIX above 25), after Daniel–Moskowitz on momentum crashes.
4. **COT overlay.** Trend trades into crowded fund positioning are halved. Contrarian positioning setups become small tactical ideas only once price confirms (close above or below the 20-day average and the 4-week return turning).
5. **Levels.** Stop at 2×ATR(14), target at 2R; RSI flags stretched entries.

Outputs are systematic and rules-based, intended for research and discussion, **not investment advice**.

![Trade ideas](docs/trade-ideas.png)

---

## How it works

```
GitHub Actions (Fri after CFTC release, retries Fri eve / Sat / Mon)
 ├─ scripts/prices.py        Yahoo Finance: daily OHLC (21 markets + S&P 500 / VIX),
 │                           current contract history, term-structure carry
 ├─ scripts/fetch_cot_data.py CFTC Socrata API by contract code → master CSV,
 │                           full-history percentiles, latest_summary.json
 └─ scripts/web_data.py      compact JSON for the browser:
                               data/web/manifest.json   (report date, ~1 KB)
                               data/web/snapshot.json   (all latest metrics, ~60 KB gz)
                               data/web/series/<TICKER>.json (weekly history per market)
GitHub Pages → index.html + js/
  data-store.js  version-keyed cache (localStorage / IndexedDB): a revisit with no new
                 CFTC data downloads only the 1 KB manifest
  insights.js    signal engine: desk brief, setup score, trade ideas (pure functions)
```

**Engineering notes:** problems found and fixed while building this.
- **Speed:** the original page made ~170 live CFTC API calls per visit (24 markets × 4 trader categories, plus the scatters). The tabs now render in under 0.3 s from pre-computed, browser-cached data.
- **Percentile bug:** incremental updates ranked new weeks only against the other new weeks. Cotton's managed-money net was stored at the 12.5th percentile when it was actually at the 82nd. Percentiles are now recomputed over the full history every run (vectorised, seconds), and checked against a brute-force calculation.
- **Silent data freeze:** WTI, Nat Gas and Brent stopped updating in Feb 2022 when the CFTC renamed those markets. Queries now use the stable CFTC contract code, and the update self-heals by backfilling each market from its own last date.
- **Roll gaps:** Yahoo's continuous series jumps on contract rolls (Lean Hogs −12% on Oct 15, Cotton −24% on the 2022 July→Dec roll). Trend measures use a ratio back-adjusted series; levels come from the tradable contract.
- **Seasonality double-counting:** two reports in one ISO week (holidays, shutdown catch-ups) were being summed.

---

## Coverage

21 CFTC-reported BCOM markets: Brent, WTI, Nat Gas, ULS Diesel, RBOB · Corn, Soybeans, Soybean Meal, Soybean Oil, SRW Wheat, HRW Wheat · Copper, Aluminum (COMEX Midwest Premium) · Gold, Silver · Sugar, Coffee, Cocoa, Cotton · Live Cattle, Lean Hogs.

Not available from the CFTC: Zinc, Nickel, Lead (LME) and Low Sulphur Gasoil (ICE Europe). COMEX outright aluminum stopped being reported in June 2026, so aluminum positioning uses the Midwest Premium contract (its price series is COMEX aluminum).

## Running locally

```bash
pip install -r requirements.txt
python scripts/prices.py          # Yahoo prices → data/prices/
python scripts/fetch_cot_data.py  # CFTC → data/ and data/web/
python -m http.server 8000        # open http://localhost:8000
```
`python scripts/check_markets.py` (or the **CFTC Market Check** workflow) lists which CFTC markets exist for each constituent and when each last reported.

---

*BMR-Com · independent commodity research. Data: CFTC Commitments of Traders and Yahoo Finance. Not investment advice.*
