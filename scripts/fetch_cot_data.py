#!/usr/bin/env python3
"""
fetch_cot_data.py — BCOM COT Data Fetcher & Analyzer
======================================================
Downloads CFTC Disaggregated COT data for all 23 BCOM constituent commodities
from 2006 to present (Futures & Options Combined endpoint).

Outputs:
  data/bcom_cot_master.csv   — Full history, all commodities, all categories,
                                with derived metrics and percentile columns.
  data/latest_summary.json   — Latest-week snapshot with pre-calculated
                                percentiles over 1yr/3yr/5yr/10yr/full
                                history, historical extremes with dates.
Run:  python scripts/fetch_cot_data.py
Deps: pip install requests pandas python-dateutil
"""

import json, os, sys, time, re
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from dateutil import tz

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR  = Path(__file__).parent
ROOT_DIR    = SCRIPT_DIR.parent
DATA_DIR    = ROOT_DIR / "data"
CSV_PATH    = DATA_DIR / "bcom_cot_master.csv"
JSON_PATH   = DATA_DIR / "latest_summary.json"
DATA_DIR.mkdir(exist_ok=True)

# ── CFTC Socrata API ───────────────────────────────────────────────────────
ENDPOINT = "https://publicreporting.cftc.gov/resource/kh3c-gbw2.json"
API_LIMIT = 10000
REQUEST_DELAY = 1.2

# ── Timezone ────────────────────────────────────────────────────────────────
ET = tz.gettz('US/Eastern')

# ── BCOM 2026 Constituents — exact CFTC API market_and_exchange_names ──────
BCOM = {
    "Brent Crude Oil":    {"ticker":"CO", "sector":"Energy",           "cftc":"BRENT CRUDE OIL LAST DAY - NEW YORK MERCANTILE EXCHANGE", "crop":False},
    "Natural Gas":        {"ticker":"NG", "sector":"Energy",           "cftc":"NATURAL GAS - NEW YORK MERCANTILE EXCHANGE",               "crop":False},
    "WTI Crude Oil":      {"ticker":"CL", "sector":"Energy",           "cftc":"CRUDE OIL, LIGHT SWEET - NEW YORK MERCANTILE EXCHANGE",    "crop":False},
    "Low Sulphur Gas Oil":{"ticker":"QS", "sector":"Energy",           "cftc":"GAS OIL LOW SULPHUR - ICE FUTURES EUROPE",                "crop":False},
    "ULS Diesel":         {"ticker":"HO", "sector":"Energy",           "cftc":"NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE",            "crop":False},
    "RBOB Gasoline":      {"ticker":"XB", "sector":"Energy",           "cftc":"GASOLINE, RBOB - NEW YORK MERCANTILE EXCHANGE",            "crop":False},
    "Corn":               {"ticker":"C",  "sector":"Grains",           "cftc":"CORN - CHICAGO BOARD OF TRADE",                           "crop":True},
    "Soybeans":           {"ticker":"S",  "sector":"Grains",           "cftc":"SOYBEANS - CHICAGO BOARD OF TRADE",                       "crop":True},
    "Soybean Meal":       {"ticker":"SM", "sector":"Grains",           "cftc":"SOYBEAN MEAL - CHICAGO BOARD OF TRADE",                   "crop":True},
    "Soybean Oil":        {"ticker":"BO", "sector":"Grains",           "cftc":"SOYBEAN OIL - CHICAGO BOARD OF TRADE",                    "crop":True},
    "Wheat SRW":          {"ticker":"W",  "sector":"Grains",           "cftc":"WHEAT-SRW - CHICAGO BOARD OF TRADE",                      "crop":True},
    "HRW Wheat":          {"ticker":"KW", "sector":"Grains",           "cftc":"WHEAT-HRW - CHICAGO BOARD OF TRADE",                      "crop":True},
    "Copper":             {"ticker":"HG", "sector":"Industrial Metals","cftc":"COPPER- #1 - COMMODITY EXCHANGE INC.",                    "crop":False},
    "Aluminum":           {"ticker":"LA", "sector":"Industrial Metals","cftc":"ALUMINUM - COMMODITY EXCHANGE INC.",                      "crop":False},
    "Zinc":               {"ticker":"LX", "sector":"Industrial Metals","cftc":"ZINC - COMMODITY EXCHANGE INC.",                          "crop":False},
    "Nickel":             {"ticker":"LN", "sector":"Industrial Metals","cftc":"NICKEL - COMMODITY EXCHANGE INC.",                        "crop":False},
    "Lead":               {"ticker":"LL", "sector":"Industrial Metals","cftc":"LEAD - COMMODITY EXCHANGE INC.",                          "crop":False},
    "Gold":               {"ticker":"GC", "sector":"Precious Metals",  "cftc":"GOLD - COMMODITY EXCHANGE INC.",                          "crop":False},
    "Silver":             {"ticker":"SI", "sector":"Precious Metals",  "cftc":"SILVER - COMMODITY EXCHANGE INC.",                        "crop":False},
    "Sugar":              {"ticker":"SB", "sector":"Softs",            "cftc":"SUGAR NO. 11 - ICE FUTURES U.S.",                         "crop":False},
    "Coffee":             {"ticker":"KC", "sector":"Softs",            "cftc":"COFFEE C - ICE FUTURES U.S.",                             "crop":True},
    "Cocoa":              {"ticker":"CC", "sector":"Softs",            "cftc":"COCOA - ICE FUTURES U.S.",                                "crop":True},
    "Cotton":             {"ticker":"CT", "sector":"Softs",            "cftc":"COTTON NO. 2 - ICE FUTURES U.S.",                         "crop":True},
    "Live Cattle":        {"ticker":"LC", "sector":"Livestock",        "cftc":"LIVE CATTLE - CHICAGO MERCANTILE EXCHANGE",               "crop":False},
    "Lean Hogs":          {"ticker":"LH", "sector":"Livestock",        "cftc":"LEAN HOGS - CHICAGO MERCANTILE EXCHANGE",                 "crop":True},
}

TRADER_CATS = ["managed_money", "swap_dealers", "prod_merc", "other_rept"]

# ── EXACT Socrata field names (confirmed from API foundry) ─────────────────
FIELDS = {
    "all": {
        "oi":    "open_interest_all",
        "mm_l":  "m_money_positions_long_all",
        "mm_s":  "m_money_positions_short_all",
        "mm_sp": "m_money_positions_spread",
        "mm_tl": "traders_m_money_long_all",
        "mm_ts": "traders_m_money_short_all",
        "sd_l":  "swap_positions_long_all",
        "sd_s":  "swap__positions_short_all",
        "sd_sp": "swap__positions_spread_all",
        "sd_tl": "traders_swap_long_all",
        "sd_ts": "traders_swap_short_all",
        "pm_l":  "prod_merc_positions_long",
        "pm_s":  "prod_merc_positions_short",
        "pm_tl": "traders_prod_merc_long_all",
        "pm_ts": "traders_prod_merc_short_all",
        "or_l":  "other_rept_positions_long",
        "or_s":  "other_rept_positions_short",
        "or_sp": "other_rept_positions_spread",
        "or_tl": "traders_other_rept_long_all",
        "or_ts": "traders_other_rept_short_all",
    },
    "old": {
        "oi":    "open_interest_old",
        "mm_l":  "m_money_positions_long_old",
        "mm_s":  "m_money_positions_short_old",
        "mm_sp": "m_money_positions_spread_1",
        "mm_tl": "traders_m_money_long_old",
        "mm_ts": "traders_m_money_short_old",
        "sd_l":  "swap_positions_long_old",
        "sd_s":  "swap__positions_short_old",
        "sd_sp": "swap__positions_spread_old",
        "sd_tl": "traders_swap_long_old",
        "sd_ts": "traders_swap_short_old",
        "pm_l":  "prod_merc_positions_long_1",
        "pm_s":  "prod_merc_positions_short_1",
        "pm_tl": "traders_prod_merc_long_old",
        "pm_ts": "traders_prod_merc_short_old",
        "or_l":  "other_rept_positions_long_1",
        "or_s":  "other_rept_positions_short_1",
        "or_sp": "other_rept_positions_spread_1",
        "or_tl": "traders_other_rept_long_old",
        "or_ts": "traders_other_rept_short_old",
    },
    "other": {
        "oi":    "open_interest_other",
        "mm_l":  "m_money_positions_long_other",
        "mm_s":  "m_money_positions_short_other",
        "mm_sp": "m_money_positions_spread_2",
        "mm_tl": "traders_m_money_long_other",
        "mm_ts": "traders_m_money_short_other",
        "sd_l":  "swap_positions_long_other",
        "sd_s":  "swap__positions_short_other",
        "sd_sp": "swap__positions_spread_other",
        "sd_tl": "traders_swap_long_other",
        "sd_ts": "traders_swap_short_other",
        "pm_l":  "prod_merc_positions_long_2",
        "pm_s":  "prod_merc_positions_short_2",
        "pm_tl": "traders_prod_merc_long_other",
        "pm_ts": "traders_prod_merc_short_other",
        "or_l":  "other_rept_positions_long_2",
        "or_s":  "other_rept_positions_short_2",
        "or_sp": "other_rept_positions_spread_2",
        "or_tl": "traders_other_rept_long_other",
        "or_ts": "traders_other_rept_short_other",
    }
}

CAT_PREFIX = {
    "managed_money": "mm",
    "swap_dealers":  "sd",
    "prod_merc":     "pm",
    "other_rept":    "or",
}

# ── Helpers ────────────────────────────────────────────────────────────────
def pct_of_score(series, score):
    """Percentile rank of score within series (0-100). No scipy needed."""
    s = pd.Series(series).dropna()
    if len(s) == 0:
        return 50.0
    below  = (s < score).sum()
    equal  = (s == score).sum()
    return round(((below + 0.5 * equal) / len(s)) * 100, 1)

def si(val):
    """Safe int parse."""
    try:
        v = int(val)
        return 0 if pd.isna(v) else v
    except (TypeError, ValueError):
        return 0

def trim_name(cftc_name):
    """Short display name from CFTC full name."""
    return cftc_name.split(" - ")[0].title()

def get_expected_report_date():
    """
    Calculate the expected Tuesday report date for current week.
    COT reports are based on Tuesday close, published Friday 3:30 PM ET.
    """
    today = datetime.now(ET)
    # Days since Tuesday (0=Monday, 1=Tuesday, ..., 4=Friday)
    days_since_tuesday = (today.weekday() - 1) % 7
    tuesday = today - timedelta(days=days_since_tuesday)
    return tuesday.strftime("%Y-%m-%d")

def validate_fresh_data(df, expected_date=None):
    """
    Validate that fetched data contains the expected report date.
    Returns (is_valid, actual_latest_date, message)
    """
    if df.empty:
        return False, None, "No data fetched"
    
    latest_date = df["date"].max()
    
    if expected_date:
        # Check if we have data for expected Tuesday
        if expected_date not in df["date"].values:
            # Check if latest date is within last 7 days (acceptable if Friday holiday)
            latest_dt = pd.to_datetime(latest_date)
            expected_dt = pd.to_datetime(expected_date)
            days_diff = (expected_dt - latest_dt).days
            
            if days_diff > 7:
                return False, latest_date, f"Data stale: latest is {latest_date}, expected {expected_date} (diff: {days_diff} days)"
            else:
                return True, latest_date, f"Using data from {latest_date} (expected {expected_date}, diff: {days_diff} days - likely holiday delay)"
    
    return True, latest_date, f"Latest data: {latest_date}"

# ── Fetch from CFTC API ────────────────────────────────────────────────────
def fetch_commodity(cftc_name, since_date="2006-01-01"):
    """Fetch all records for a commodity since a given date."""
    enc = cftc_name.replace("'", "''")
    url = (
        f"{ENDPOINT}"
        f"?$where=market_and_exchange_names='{enc}'"
        f" AND report_date_as_yyyy_mm_dd >= '{since_date}'"
        f"&$order=report_date_as_yyyy_mm_dd ASC"
        f"&$limit={API_LIMIT}"
    )
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data
    except Exception as e:
        print(f"  ERROR fetching {cftc_name}: {e}")
        return []

# ── Process raw API records into flat rows ─────────────────────────────────
def process_records(raw, commodity_name, meta, crop_type="all"):
    """Convert list of raw API dicts into a list of flat row dicts."""
    fmap = FIELDS[crop_type]
    rows = []
    for rec in raw:
        date_str = rec.get("report_date_as_yyyy_mm_dd", "")[:10]
        if not date_str:
            continue

        oi = si(rec.get(fmap["oi"]))

        row = {
            "date":           date_str,
            "commodity":      commodity_name,
            "ticker":         meta["ticker"],
            "sector":         meta["sector"],
            "crop_type":      crop_type,
            "is_crop":        meta["crop"],
            "open_interest":  oi,
        }

        # All 4 trader categories
        for cat, pfx in CAT_PREFIX.items():
            L  = si(rec.get(fmap[f"{pfx}_l"]))
            S  = si(rec.get(fmap[f"{pfx}_s"]))
            Sp = si(rec.get(fmap.get(f"{pfx}_sp",""))) if fmap.get(f"{pfx}_sp") else 0
            TL = si(rec.get(fmap[f"{pfx}_tl"]))
            TS = si(rec.get(fmap[f"{pfx}_ts"]))

            net    = L - S
            lp     = (L / oi * 100) if oi > 0 else 0.0
            sp_pct = (S / oi * 100) if oi > 0 else 0.0
            np_pct = lp - sp_pct
            ppt_l  = (L / TL) if TL > 0 else 0.0
            ppt_s  = (S / TS) if TS > 0 else 0.0

            prefix = f"{cat}"
            row[f"{prefix}_long"]          = L
            row[f"{prefix}_short"]         = S
            row[f"{prefix}_spread"]        = Sp
            row[f"{prefix}_net"]           = net
            row[f"{prefix}_traders_long"]  = TL
            row[f"{prefix}_traders_short"] = TS
            row[f"{prefix}_long_pct_oi"]   = round(lp, 3)
            row[f"{prefix}_short_pct_oi"]  = round(sp_pct, 3)
            row[f"{prefix}_net_pct_oi"]    = round(np_pct, 3)
            row[f"{prefix}_per_trader_l"]  = round(ppt_l, 1)
            row[f"{prefix}_per_trader_s"]  = round(ppt_s, 1)

        rows.append(row)
    return rows

# ── Percentile calculation across multiple windows ─────────────────────────
WINDOWS = {
    "1yr":  52,
    "3yr":  156,
    "5yr":  260,
    "10yr": 520,
    "full": None,
}

PCTILE_COLS = [
    "managed_money_net",      "managed_money_long",     "managed_money_short",
    "managed_money_net_pct_oi","managed_money_long_pct_oi","managed_money_short_pct_oi",
    "managed_money_per_trader_l","managed_money_per_trader_s",
    "swap_dealers_net",       "swap_dealers_long",      "swap_dealers_short",
    "swap_dealers_net_pct_oi",
    "prod_merc_net",          "prod_merc_long",         "prod_merc_short",
    "prod_merc_net_pct_oi",
    "other_rept_net",         "other_rept_long",        "other_rept_short",
    "other_rept_net_pct_oi",
    "open_interest",
]

def add_percentiles(df):
    """Add percentile rank columns for each metric, per commodity+crop_type group."""
    print("  Calculating percentiles...")
    groups = df.groupby(["commodity", "crop_type"])
    pctile_dfs = []

    for (comm, ct), grp in groups:
        grp = grp.sort_values("date").reset_index(drop=True)
        pctile_rows = []

        for i, row in grp.iterrows():
            pr = {"date": row["date"], "commodity": comm, "crop_type": ct}
            for col in PCTILE_COLS:
                if col not in grp.columns:
                    continue
                val = row[col]
                for win_name, win_size in WINDOWS.items():
                    hist = grp.loc[:i, col]
                    if win_size and len(hist) > win_size:
                        hist = hist.iloc[-win_size:]
                    pr[f"pctile_{col}_{win_name}"] = pct_of_score(hist, val)
            pctile_rows.append(pr)

        pctile_dfs.append(pd.DataFrame(pctile_rows))

    if not pctile_dfs:
        return df
    pctile_df = pd.concat(pctile_dfs, ignore_index=True)
    df = df.merge(pctile_df, on=["date","commodity","crop_type"], how="left")
    return df

# ── Historical extremes for summary JSON ──────────────────────────────────
def extremes(series, dates, windows=(260, 520)):
    """Return min/max values and their dates for different windows."""
    result = {}
    for w in windows:
        tag = f"{w//52}yr"
        s = series.iloc[-w:] if len(series) > w else series
        d = dates.iloc[-w:] if len(dates) > w else dates
        if len(s) == 0:
            continue
        mn_idx = s.idxmin(); mx_idx = s.idxmax()
        result[f"{tag}_min"] = int(s[mn_idx])
        result[f"{tag}_min_date"] = str(d[mn_idx])[:10]
        result[f"{tag}_max"] = int(s[mx_idx])
        result[f"{tag}_max_date"] = str(d[mx_idx])[:10]
    mn_idx = series.idxmin(); mx_idx = series.idxmax()
    result["full_min"] = int(series[mn_idx])
    result["full_min_date"] = str(dates[mn_idx])[:10]
    result["full_max"] = int(series[mx_idx])
    result["full_max_date"] = str(dates[mx_idx])[:10]
    return result

# ── Build summary JSON ─────────────────────────────────────────────────────
def build_summary(df):
    """Build compact summary dict for Groq context."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    latest_date = df["date"].max()

    summary = {
        "report_date":   latest_date,
        "generated":     now,
        "data_from":     df["date"].min(),
        "total_records": len(df),
        "description":   (
            "BCOM COT Data — CFTC Disaggregated Futures & Options Combined. "
            "Percentiles calculated vs full history since 2006 and rolling windows. "
            "Crop commodities have old/other/all crop-type variants."
        ),
        "commodities": []
    }

    for comm_name, meta in BCOM.items():
        cd = df[df["commodity"] == comm_name].sort_values("date")
        if cd.empty:
            continue

        crop_types = ["all", "old", "other"] if meta["crop"] else ["all"]
        comm_entry = {
            "name":    comm_name,
            "ticker":  meta["ticker"],
            "sector":  meta["sector"],
            "is_crop": meta["crop"],
            "variants": []
        }

        for ct in crop_types:
            ctd = cd[cd["crop_type"] == ct].sort_values("date")
            if ctd.empty:
                continue

            latest = ctd.iloc[-1]
            prev   = ctd.iloc[-2] if len(ctd) > 1 else latest

            variant = {
                "crop_type":    ct,
                "date":         str(latest["date"])[:10],
                "open_interest": int(latest.get("open_interest", 0)),
                "categories":   {}
            }

            for cat in TRADER_CATS:
                net   = int(latest.get(f"{cat}_net", 0))
                lng   = int(latest.get(f"{cat}_long", 0))
                shrt  = int(latest.get(f"{cat}_short", 0))
                sprd  = int(latest.get(f"{cat}_spread", 0))
                pnet  = float(latest.get(f"{cat}_net_pct_oi", 0))
                plng  = float(latest.get(f"{cat}_long_pct_oi", 0))
                pshrt = float(latest.get(f"{cat}_short_pct_oi", 0))
                tl    = int(latest.get(f"{cat}_traders_long", 0))
                ts    = int(latest.get(f"{cat}_traders_short", 0))
                ptl   = float(latest.get(f"{cat}_per_trader_l", 0))
                pts   = float(latest.get(f"{cat}_per_trader_s", 0))

                chg_net  = net  - int(prev.get(f"{cat}_net", net))
                chg_long = lng  - int(prev.get(f"{cat}_long", lng))
                chg_shrt = shrt - int(prev.get(f"{cat}_short", shrt))

                def gp(col, win="full"):
                    return float(latest.get(f"pctile_{col}_{win}", -1))

                pctiles = {
                    "net_full":      gp(f"{cat}_net"),
                    "net_1yr":       gp(f"{cat}_net","1yr"),
                    "net_3yr":       gp(f"{cat}_net","3yr"),
                    "net_5yr":       gp(f"{cat}_net","5yr"),
                    "net_10yr":      gp(f"{cat}_net","10yr"),
                    "long_full":     gp(f"{cat}_long"),
                    "long_10yr":     gp(f"{cat}_long","10yr"),
                    "short_full":    gp(f"{cat}_short"),
                    "short_10yr":    gp(f"{cat}_short","10yr"),
                    "net_pctoi_full":gp(f"{cat}_net_pct_oi"),
                    "net_pctoi_10yr":gp(f"{cat}_net_pct_oi","10yr"),
                }

                net_series  = ctd[f"{cat}_net"].reset_index(drop=True)
                lng_series  = ctd[f"{cat}_long"].reset_index(drop=True)
                shrt_series = ctd[f"{cat}_short"].reset_index(drop=True)
                date_series = ctd["date"].reset_index(drop=True)

                hist = {
                    "net":   extremes(net_series,  date_series),
                    "long":  extremes(lng_series,  date_series),
                    "short": extremes(shrt_series, date_series),
                }

                variant["categories"][cat] = {
                    "net":              net,
                    "long":             lng,
                    "short":            shrt,
                    "spread":           sprd,
                    "net_pct_oi":       round(pnet, 2),
                    "long_pct_oi":      round(plng, 2),
                    "short_pct_oi":     round(pshrt, 2),
                    "traders_long":     tl,
                    "traders_short":    ts,
                    "per_trader_long":  round(ptl, 1),
                    "per_trader_short": round(pts, 1),
                    "wk_chg_net":       chg_net,
                    "wk_chg_long":      chg_long,
                    "wk_chg_short":     chg_shrt,
                    "pctiles":          pctiles,
                    "historical":       hist,
                }

            comm_entry["variants"].append(variant)
        summary["commodities"].append(comm_entry)

    return summary


# ── Main ───────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("BCOM COT Data Fetcher")
    print(f"Started: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 65)

    # Determine start date (incremental update)
    if CSV_PATH.exists():
        existing = pd.read_csv(CSV_PATH, usecols=["date"])
        latest_in_csv = existing["date"].max()
        since = (
            pd.to_datetime(latest_in_csv) - timedelta(days=14)
        ).strftime("%Y-%m-%d")
        print(f"Existing CSV found. Fetching from {since} (2-week overlap).")
        full_rebuild = False
    else:
        since = "2006-01-01"
        print(f"No CSV found. Full download from {since}.")
        full_rebuild = True

    all_rows = []
    total = len(BCOM)

    for i, (comm_name, meta) in enumerate(BCOM.items(), 1):
        print(f"  [{i:2d}/{total}] {comm_name} ({meta['ticker']}) ...", end=" ", flush=True)
        raw = fetch_commodity(meta["cftc"], since_date=since)
        if not raw:
            print("no data")
            time.sleep(REQUEST_DELAY)
            continue

        rows = process_records(raw, comm_name, meta, crop_type="all")
        all_rows.extend(rows)

        if meta["crop"]:
            for ct in ["old", "other"]:
                fmap = FIELDS[ct]
                if raw and fmap["mm_l"] in raw[-1]:
                    ct_rows = process_records(raw, comm_name, meta, crop_type=ct)
                    all_rows.extend(ct_rows)

        print(f"{len(raw)} records")
        time.sleep(REQUEST_DELAY)

    if not all_rows:
        print("ERROR: No data fetched. Exiting.")
        sys.exit(1)

    new_df = pd.DataFrame(all_rows)
    new_df["date"] = pd.to_datetime(new_df["date"]).dt.strftime("%Y-%m-%d")

    # ── VALIDATE FRESH DATA ────────────────────────────────────────────────
    expected_tuesday = get_expected_report_date()
    is_valid, latest_date, msg = validate_fresh_data(new_df, expected_tuesday)
    print(f"\n[Validator] {msg}")
    
    if not is_valid:
        print("ERROR: Data validation failed. CFTC may not have released new report yet.")
        sys.exit(1)  # Triggers retry in GitHub Actions

    # Merge with existing CSV
    if CSV_PATH.exists() and not full_rebuild:
        old_df = pd.read_csv(CSV_PATH, dtype=str)
        cutoff = new_df["date"].min()
        old_df = old_df[old_df["date"] < cutoff]
        df = pd.concat([old_df, new_df], ignore_index=True)
        for col in new_df.columns:
            if col not in ["date","commodity","ticker","sector","crop_type","is_crop"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
    else:
        df = new_df

    df = df.sort_values(["commodity","crop_type","date"]).reset_index(drop=True)

    print(f"\nTotal rows before percentile calc: {len(df):,}")
    print("Calculating percentile columns (this takes a few minutes for full rebuild)...")

    df = add_percentiles(df)

    # Save master CSV
    df.to_csv(CSV_PATH, index=False)
    sz = CSV_PATH.stat().st_size / 1024
    print(f"\nSaved: {CSV_PATH.name} ({sz:.1f} KB, {len(df):,} rows)")

    # Build and save summary JSON
    print("Building latest_summary.json...")
    summary = build_summary(df)
    with open(JSON_PATH, "w") as f:
        json.dump(summary, f, separators=(",",":"))
    sz2 = JSON_PATH.stat().st_size / 1024
    print(f"Saved: {JSON_PATH.name} ({sz2:.1f} KB)")

    print("\n" + "=" * 65)
    print(f"Done: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Latest report date: {summary['report_date']}")
    print(f"Commodities: {len(summary['commodities'])}")
    print("=" * 65)

if __name__ == "__main__":
    main()
