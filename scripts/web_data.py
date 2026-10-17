#!/usr/bin/env python3
"""
web_data.py — build the small, pre-computed JSON files the dashboard reads.

The browser used to pull the full CFTC history for every BCOM market straight
from the Socrata API on every visit (≈170 requests for Summary + Scatter +
Seasonality). Everything those tabs need is derivable from the master CSV the
weekly workflow already maintains, so we compute it once here instead.

Outputs (all under data/web/):
  manifest.json        — report date + commodity list. Tiny; the page checks it
                         with no-cache and uses report_date as the cache key.
  snapshot.json        — latest-week metrics per commodity × crop type × trader
                         category: levels, w/w and 4w changes, flow z-score,
                         COT index, percentiles over several look-backs, ranges.
                         Drives Summary, Scatter and the trader desk notes.
  series/<TICKER>.json — columnar weekly history for one commodity (all crop
                         types, all categories). Loaded lazily by Seasonality
                         and the agri crop-year panels.

Run standalone to rebuild from the existing CSV:
    python scripts/web_data.py
"""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
WEB_DIR = DATA_DIR / "web"
SERIES_DIR = WEB_DIR / "series"
CSV_PATH = DATA_DIR / "bcom_cot_master.csv"

CATS = ["managed_money", "swap_dealers", "prod_merc", "other_rept"]
WIN = {"f": None, "y5": 260, "y3": 156, "y1": 52}
STALE_DAYS = 21  # a market with no report in 3 weeks is excluded from cross-sectional views


# ── helpers ────────────────────────────────────────────────────────────────
def _num(v, nd=None):
    """JSON-safe number: NaN/inf -> None, optional rounding, ints stay ints."""
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    if nd is None:
        return int(round(f))
    return round(f, nd)


def midrank_pct(hist, v):
    """Percentile of v within hist using mid-rank ties (0-100)."""
    h = hist[~np.isnan(hist)]
    if len(h) == 0 or v is None or np.isnan(v):
        return None
    return round(((h < v).sum() + 0.5 * (h == v).sum()) / len(h) * 100, 1)


def win(arr, w):
    return arr if (w is None or len(arr) <= w) else arr[-w:]


def pct_set(arr, wins=("f", "y5", "y3", "y1")):
    v = arr[-1]
    return {k: midrank_pct(win(arr, WIN[k]), v) for k in wins}


def cot_index(arr, w):
    a = win(arr, w)
    a = a[~np.isnan(a)]
    if len(a) == 0:
        return None
    lo, hi = a.min(), a.max()
    if hi == lo:
        return 50.0
    return round((arr[-1] - lo) / (hi - lo) * 100, 1)


def streak(d):
    """Consecutive weeks (ending now) the weekly change kept the same sign."""
    d = d[~np.isnan(d)]
    if len(d) == 0 or d[-1] == 0:
        return 0
    s = np.sign(d[-1])
    n = 0
    for x in d[::-1]:
        if np.sign(x) == s:
            n += 1
        else:
            break
    return int(n * s)


# ── per-category metrics ───────────────────────────────────────────────────
def cat_metrics(g, cat):
    """g: rows for one commodity+crop_type sorted by date."""
    L = g[f"{cat}_long"].to_numpy(float)
    S = g[f"{cat}_short"].to_numpy(float)
    Sp = g[f"{cat}_spread"].to_numpy(float)
    TL = g[f"{cat}_traders_long"].to_numpy(float)
    TS = g[f"{cat}_traders_short"].to_numpy(float)
    oi = g["open_interest"].to_numpy(float)
    N = L - S
    with np.errstate(divide="ignore", invalid="ignore"):
        lp = np.where(oi > 0, L / oi * 100, 0.0)
        sp = np.where(oi > 0, S / oi * 100, 0.0)
    npc = lp - sp

    def d(a, k=1):
        return a[-1] - a[-1 - k] if len(a) > k else 0.0

    dN = np.diff(N) if len(N) > 1 else np.array([0.0])
    hist = win(dN, 156)
    sd = np.nanstd(hist) if len(hist) > 4 else np.nan
    z = (dN[-1] / sd) if sd and not np.isnan(sd) and sd > 0 else 0.0

    return {
        "L": _num(L[-1]), "S": _num(S[-1]), "Sp": _num(Sp[-1]), "N": _num(N[-1]),
        "TL": _num(TL[-1]), "TS": _num(TS[-1]),
        "lp": _num(lp[-1], 2), "sp": _num(sp[-1], 2), "np": _num(npc[-1], 2),
        "dL": _num(d(L)), "dS": _num(d(S)), "dN": _num(d(N)), "dN4": _num(d(N, 4)),
        "dTL": _num(d(TL)), "dTS": _num(d(TS)), "dnp": _num(d(npc), 2),
        "z": _num(z, 2), "streak": streak(dN),
        "cot3": cot_index(N, 156), "cot1": cot_index(N, 52), "cot5": cot_index(N, 260),
        "p": {
            "N": pct_set(N), "L": pct_set(L), "S": pct_set(S),
            "np": pct_set(npc), "lp": pct_set(lp), "sp": pct_set(sp),
            "TL": pct_set(TL, ("f", "y3")), "TS": pct_set(TS, ("f", "y3")),
        },
        "r": {
            "N": [_num(np.nanmin(N)), _num(np.nanmax(N))],
            "np": [_num(np.nanmin(npc), 2), _num(np.nanmax(npc), 2)],
            "L": [_num(np.nanmin(L)), _num(np.nanmax(L))],
            "lp": [_num(np.nanmin(lp), 2), _num(np.nanmax(lp), 2)],
            "S": [_num(np.nanmin(S)), _num(np.nanmax(S))],
            "sp": [_num(np.nanmin(sp), 2), _num(np.nanmax(sp), 2)],
        },
        "spark": [_num(x) for x in win(N, 52)],
    }


# ── prices & technicals ─────────────────────────────────────────────────────
PRICE_CSV = DATA_DIR / "prices" / "daily.csv"
PRICE_REPORT = DATA_DIR / "prices" / "report.json"
SEASONAL_CURVE = {"NG", "LC", "LH"}   # Fama-French: carry unreliable on seasonal curves


CIT_CSV = DATA_DIR / "cit_master.csv"


def load_cit():
    """Index-trader (CIT) supplemental report, 13 ag markets. Empty dict if missing."""
    if not CIT_CSV.exists():
        return {}
    c = pd.read_csv(CIT_CSV, dtype={"date": str})
    c["date"] = pd.to_datetime(c["date"]).dt.strftime("%Y-%m-%d")
    return {t: g.drop_duplicates("date", keep="last").set_index("date").sort_index()
            for t, g in c.groupby("ticker")}


def cit_metrics(g):
    """Latest-week index-trader metrics for one market (g indexed by date)."""
    L = g["cit_long"].to_numpy(float); S = g["cit_short"].to_numpy(float)
    oi = g["open_interest"].to_numpy(float); N = L - S
    with np.errstate(divide="ignore", invalid="ignore"):
        npc = np.where(oi > 0, N / oi * 100, 0.0)
        lp = np.where(oi > 0, L / oi * 100, 0.0)

    def d(a, k=1):
        return a[-1] - a[-1 - k] if len(a) > k else None

    dN = np.diff(N) if len(N) > 1 else np.array([0.0])
    sd = np.nanstd(win(dN, 156)) if len(dN) > 4 else np.nan
    z = (dN[-1] / sd) if sd and not np.isnan(sd) and sd > 0 else 0.0
    rb = g["rebalance_window"].astype(str).str.lower().eq("true").to_numpy()
    return {
        "date": g.index[-1], "L": _num(L[-1]), "S": _num(S[-1]), "N": _num(N[-1]),
        "TL": _num(g["cit_traders_long"].iloc[-1]), "np": _num(npc[-1], 2), "lp": _num(lp[-1], 2),
        "dN": _num(d(N)), "dN4": _num(d(N, 4)), "dN13": _num(d(N, 13)), "dN52": _num(d(N, 52)),
        "dnp4": _num(d(npc, 4), 2), "dnp13": _num(d(npc, 13), 2),
        "z": _num(z, 2), "streak": streak(dN), "rebal": bool(rb[-1]),
        "p": {"N": pct_set(N), "np": pct_set(npc), "L": pct_set(L)},
        "cot3": cot_index(N, 156),
        "r": {"N": [_num(np.nanmin(N)), _num(np.nanmax(N))], "np": [_num(np.nanmin(npc), 2), _num(np.nanmax(npc), 2)]},
        "spark": [_num(x) for x in win(N, 52)],
    }


def cit_aggregate(cit, rd):
    """Complex-wide index flow: is money being allocated to or pulled from ag commodities?"""
    rows = []
    for t, g in cit.items():
        if (rd - pd.to_datetime(g.index[-1])).days > STALE_DAYS or len(g) < 14:
            continue
        N = g["cit_net"].to_numpy(float); oi = g["open_interest"].to_numpy(float)
        npc = np.where(oi > 0, N / oi * 100, 0.0)
        rows.append({"t": t, "sector": g["sector"].iloc[-1], "name": g["commodity"].iloc[-1],
                     "dN": N[-1] - N[-2], "dN4": N[-1] - N[-5], "dN13": N[-1] - N[-14],
                     "dnp4": npc[-1] - npc[-5], "dnp13": npc[-1] - npc[-14]})
    if not rows:
        return None
    r = pd.DataFrame(rows)
    # history of breadth: share of markets whose index net rose over 4 weeks, per report date
    allg = pd.concat([g.assign(t=t)[["cit_net", "open_interest", "t"]] for t, g in cit.items()])
    allg.index = pd.to_datetime(allg.index)
    w = allg.pivot_table(index=allg.index, columns="t", values="cit_net").sort_index()
    br = (w.diff(4) > 0).sum(axis=1) / w.notna().sum(axis=1) * 100
    br = br.dropna()
    sec = r.groupby("sector")[["dnp4", "dnp13"]].mean().round(2)
    return {
        "date": max(g.index[-1] for g in cit.values()), "n": len(r),
        "adding4": int((r.dN4 > 0).sum()), "adding13": int((r.dN13 > 0).sum()),
        "avg_dnp4": _num(r.dnp4.mean(), 2), "avg_dnp13": _num(r.dnp13.mean(), 2),
        "rebal": bool(pd.to_datetime(max(g.index[-1] for g in cit.values())).month == 1
                      and pd.to_datetime(max(g.index[-1] for g in cit.values())).day <= 20),
        "breadth4": _num(br.iloc[-1], 1) if len(br) else None,
        "breadth4_pct": midrank_pct(br.to_numpy(float), br.iloc[-1]) if len(br) else None,
        "breadth_hist": {"dates": [d.strftime("%Y-%m-%d") for d in br.index[-260:]],
                         "v": [_num(x, 1) for x in br.iloc[-260:]]},
        "sectors": {k: {"dnp4": _num(v.dnp4, 2), "dnp13": _num(v.dnp13, 2)} for k, v in sec.iterrows()},
        "top_in": r.sort_values("dnp4", ascending=False).head(3)[["name", "dnp4", "dN4"]].to_dict("records"),
        "top_out": r.sort_values("dnp4").head(3)[["name", "dnp4", "dN4"]].to_dict("records"),
    }


FRONT_CSV = DATA_DIR / "prices" / "front_contract.csv"
# Markets whose continuous "=F" series has large roll gaps (seasonal / quarterly curves).
ROLL_ADJUST = {"C", "S", "SM", "BO", "W", "KW", "SB", "KC", "CC", "CT", "LC", "LH", "NG"}


def load_prices():
    if not PRICE_CSV.exists():
        return {}, {}, {}
    p = pd.read_csv(PRICE_CSV, parse_dates=["date"])
    rep = json.loads(PRICE_REPORT.read_text()) if PRICE_REPORT.exists() else {}
    fr = {}
    if FRONT_CSV.exists():
        f = pd.read_csv(FRONT_CSV, parse_dates=["date"])
        fr = {tk: g.set_index("date").sort_index() for tk, g in f.groupby("ticker")}
    return {tk: g.set_index("date").sort_index() for tk, g in p.groupby("ticker")}, rep, fr


def back_adjust(close, ticker):
    """Remove roll gaps from an unadjusted front-month series (ratio back-adjust).
    A day counts as a roll gap when its log move exceeds 3.5x the trailing 60-day
    stdev; that day's return is set to zero. Applied only to markets with
    seasonal/quarterly curves, where Yahoo's roll creates 5-25% jumps."""
    c = close.where(close > 0)
    lr = np.log(c / c.shift())
    if ticker in ROLL_ADJUST:
        sd = lr.rolling(60, min_periods=20).std().shift()
        gap = lr.abs() > 3.5 * sd
        lr = lr.mask(gap, 0.0)
    lr = lr.fillna(0.0)
    adj = np.exp(lr.cumsum())
    return adj / adj.iloc[-1] * close.iloc[-1], int(gap.sum()) if ticker in ROLL_ADJUST else 0


def rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def px_metrics(g, carry=None, ticker=None, front=None):
    """Trend from the roll-adjusted continuous series; levels and short-term
    technicals from the tradable front contract when its history is long enough."""
    g = g.dropna(subset=["close"])
    if len(g) < 60:
        return None
    adj, ngaps = back_adjust(g["close"], ticker)
    def ret(s, n):
        return float(s.iloc[-1] / s.iloc[-1 - n] - 1) if len(s) > n and s.iloc[-1 - n] > 0 else None
    r12, r6 = ret(adj, 252), ret(adj, 126)
    s200 = float(adj.rolling(200).mean().iloc[-1]) if len(adj) >= 200 else None
    vs200 = (float(adj.iloc[-1]) / s200 - 1) if s200 else None
    trend = 0.0
    if r12:
        sg = 1 if r12 > 0 else -1
        conf = int(r6 is not None and np.sign(r6) == sg) + int(vs200 is not None and np.sign(vs200) == sg)
        trend = sg * {2: 1.0, 1: 0.5, 0: 0.0}[conf]
    lra = np.log(adj / adj.shift())
    hi52, lo52 = float(adj.iloc[-252:].max()), float(adj.iloc[-252:].min())
    rng52 = (float(adj.iloc[-1]) - lo52) / (hi52 - lo52) * 100 if hi52 > lo52 else None

    # short-term: the actual contract if we have >= 30 sessions of it, else adjusted series
    src, contract = None, None
    if front is not None and len(front.dropna(subset=["close"])) >= 30:
        src = front.dropna(subset=["close"]); contract = str(src["contract"].iloc[-1])
    else:
        src = pd.DataFrame({"close": adj, "high": adj, "low": adj})
    c, h, l = src["close"], src["high"].fillna(src["close"]), src["low"].fillna(src["close"])
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1 / 14, adjust=False).mean()
    lr = np.log(c / c.shift()).replace([np.inf, -np.inf], np.nan)
    sma = lambda n: (float(c.rolling(n).mean().iloc[-1]) if len(c) >= n else None)
    cy = None
    if carry and carry.get("carry_ann") is not None:
        cy = {"ann": carry["carry_ann"], "front": carry.get("front"), "deferred": carry.get("deferred"),
              "seasonal": ticker in SEASONAL_CURVE}
    return {
        "date": c.index[-1].strftime("%Y-%m-%d"), "close": _num(c.iloc[-1], 4), "contract": contract,
        "r1w": _num(ret(c, 5), 4), "r4w": _num(ret(c, 20), 4), "r13w": _num(ret(adj, 63), 4),
        "r26w": _num(r6, 4), "r52w": _num(r12, 4), "vs200": _num(vs200, 4),
        "sma20": _num(sma(20), 4), "sma50": _num(sma(50), 4),
        "rsi": _num(rsi(c).iloc[-1], 1), "atr": _num(atr.iloc[-1], 4),
        "rv20": _num(lr.iloc[-20:].std() * np.sqrt(252), 4),
        "rv60": _num(lra.iloc[-60:].std() * np.sqrt(252), 4),
        "rng52": _num(rng52, 1), "hi20": _num(float(h.iloc[-20:].max()), 4), "lo20": _num(float(l.iloc[-20:].min()), 4),
        "trend": trend, "carry": cy, "roll_gaps_removed": ngaps,
        "spark": [_num(x, 4) for x in adj.iloc[-260::5]],
    }


# ── builders ───────────────────────────────────────────────────────────────
def build(df, bcom_meta=None):
    """df: master dataframe (raw columns are enough; percentile cols ignored)."""
    WEB_DIR.mkdir(exist_ok=True)
    SERIES_DIR.mkdir(exist_ok=True)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    report_date = df["date"].max()
    rd = pd.to_datetime(report_date)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    meta_by_name = bcom_meta or {}
    order = list(meta_by_name.keys()) or sorted(df["commodity"].unique())

    manifest = {"report_date": report_date, "generated": now,
                "data_from": df["date"].min(), "commodities": []}
    snapshot = {"report_date": report_date, "generated": now, "commodities": []}
    prices, prep, fronts = load_prices()
    cit = load_cit()
    if cit:
        agg = cit_aggregate(cit, rd)
        if agg:
            for k2 in ("top_in", "top_out"):
                agg[k2] = [{"name": x["name"], "dnp4": _num(x["dnp4"], 2), "dN4": _num(x["dN4"])} for x in agg[k2]]
            snapshot["cit_agg"] = agg
        manifest["cit_tickers"] = sorted(cit.keys())
    if prep:
        snapshot["regime"] = prep.get("regime")
        snapshot["prices_fetched"] = prep.get("fetched_at")
        manifest["prices_fetched"] = prep.get("fetched_at")

    for name in order:
        cd = df[df["commodity"] == name]
        if cd.empty:
            continue
        first = cd.iloc[0]
        m = meta_by_name.get(name, {})
        ticker = m.get("ticker", first["ticker"])
        sector = m.get("sector", first["sector"])
        is_crop = bool(m.get("crop", str(first["is_crop"]).lower() == "true"))
        crop_types = [c for c in ["all", "old", "other"] if (cd["crop_type"] == c).any()]
        last = cd[cd["crop_type"] == "all"]["date"].max()
        stale = (rd - pd.to_datetime(last)).days > STALE_DAYS

        manifest["commodities"].append({
            "name": name, "ticker": ticker, "sector": sector, "is_crop": is_crop,
            "code": m.get("code"), "cftc": m.get("cftc"),
            "crop_types": crop_types, "last_date": last, "stale": stale,
        })

        # ── series file ──
        all_dates = sorted(cd[cd["crop_type"] == "all"]["date"].unique())
        ser = {"name": name, "ticker": ticker, "sector": sector, "is_crop": is_crop,
               "dates": all_dates, "ct": {}}
        snap = {"name": name, "ticker": ticker, "sector": sector, "is_crop": is_crop,
                "date": last, "stale": stale, "v": {}}
        pg = prices.get(ticker)
        if pg is not None and len(pg):
            snap["px"] = px_metrics(pg, (prep.get("carry") or {}).get(ticker), ticker, fronts.get(ticker))
            note = ((prep.get("markets") or {}).get(ticker) or {}).get("note")
            if snap["px"] and note:
                snap["px"]["note"] = note
            # weekly close aligned to each COT report date (last close on/before Tuesday)
            cs = back_adjust(pg["close"].dropna(), ticker)[0]
            idx = cs.index.searchsorted(pd.to_datetime(all_dates), side="right") - 1
            ser["px"] = [(_num(cs.iloc[i], 4) if i >= 0 and (pd.to_datetime(d) - cs.index[i]).days <= 7 else None)
                         for i, d in zip(idx, all_dates)]
        cg = cit.get(ticker)
        if cg is not None and len(cg) > 1:
            cr = cg.reindex(all_dates)
            ser["cit"] = {"l": [_num(x) for x in cr["cit_long"]], "s": [_num(x) for x in cr["cit_short"]],
                          "tl": [_num(x) for x in cr["cit_traders_long"]], "oi": [_num(x) for x in cr["open_interest"]]}
            snap["cit"] = cit_metrics(cg)
        for ct in crop_types:
            g = (cd[cd["crop_type"] == ct].drop_duplicates("date", keep="last")
                 .set_index("date").reindex(all_dates))
            blk = {"oi": [_num(x) for x in g["open_interest"]]}
            for cat in CATS:
                blk[cat] = {
                    "l": [_num(x) for x in g[f"{cat}_long"]],
                    "s": [_num(x) for x in g[f"{cat}_short"]],
                    "sp": [_num(x) for x in g[f"{cat}_spread"]],
                    "tl": [_num(x) for x in g[f"{cat}_traders_long"]],
                    "ts": [_num(x) for x in g[f"{cat}_traders_short"]],
                }
            ser["ct"][ct] = blk

            gv = g.dropna(subset=["open_interest"]).reset_index()
            if len(gv) < 2:
                continue
            oi = gv["open_interest"].to_numpy(float)
            snap["v"][ct] = {
                "date": gv["date"].iloc[-1],
                "oi": _num(oi[-1]), "doi": _num(oi[-1] - oi[-2]),
                "doi4": _num(oi[-1] - oi[-5]) if len(oi) > 4 else None,
                "poi": pct_set(oi, ("f", "y3")),
                "cats": {cat: cat_metrics(gv, cat) for cat in CATS},
            }
        with open(SERIES_DIR / f"{ticker}.json", "w") as f:
            json.dump(ser, f, separators=(",", ":"))
        snapshot["commodities"].append(snap)

    with open(WEB_DIR / "snapshot.json", "w") as f:
        json.dump(snapshot, f, separators=(",", ":"))
    with open(WEB_DIR / "manifest.json", "w") as f:
        json.dump(manifest, f, separators=(",", ":"), indent=None)
    return manifest


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        from fetch_cot_data import BCOM  # noqa: E402
    except Exception:
        BCOM = None
    cols = None
    df = pd.read_csv(CSV_PATH, low_memory=False)
    df = df[[c for c in df.columns if not c.startswith("pctile_")]]
    man = build(df, BCOM)
    sizes = {p.name: p.stat().st_size for p in WEB_DIR.glob("*.json")}
    print("report_date", man["report_date"], "| commodities", len(man["commodities"]))
    print("stale:", [c["name"] for c in man["commodities"] if c["stale"]])
    print(sizes)
