"""Old-crop / new-crop calendar spread after the first WASDE balance sheets (MY 2007/08 onward).

Trade (per market, entry year Y, entry month m in May..Sep):
  short this year's new-crop contract, long next year's new-crop contract;
  roll the short leg down the old-crop chain at the Rogers roll (close of the last business day of M-2)
  or the GSCI roll (close of GSCI day 3 = 7th business day of M-1);
  close everything the day before first notice of the last old-crop contract.
    CT: short Z(Y) -> H -> K -> N(Y+1), long Z(Y+1), exit 5 BD before Jul delivery month
    ZC: short Z(Y) -> H -> K -> N,          long Z(Y+1), exit day before Jul FND (last BD of Jun)
    ZS: short X(Y) -> F -> H -> K -> N,     long X(Y+1), exit day before Jul FND
    ZW/KE: short Z(Y) -> H -> K,            long N(Y+1), exit day before May FND (last BD of Apr)
Entry: close of the WASDE release day (noon ET release; dates from the wasde-analytics master file, May 2010 onward).
Balance sheet: US new-crop (Y/Y+1) ending stocks / total use from that month's WASDE, versus the
old-crop estimate in the same report and versus final S/U of the previous 10 years (USDA PSD)."""
import os, json, numpy as np, pandas as pd
import rollcommon as bt
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, '..', 'data'); RES = os.path.join(HERE, '..', 'results')
WASDE_DIR = os.environ.get('WASDE_DIR', os.path.join(DATA, 'wasde'))

SPEC = {  # root: (wasde file, psd name, short chain codes with year offsets, long leg, exit month, FND offset rule)
    'CT': ('Cotton.json', 'Cotton', [('Z', 0), ('H', 1), ('K', 1), ('N', 1)], ('Z', 1), (7, 'ct')),
    'ZC': ('Corn.json', 'Corn', [('Z', 0), ('H', 1), ('K', 1), ('N', 1)], ('Z', 1), (7, 'lastbd')),
    'ZS': ('Oilseed,_Soybean.json', 'Oilseed, Soybean', [('X', 0), ('F', 1), ('H', 1), ('K', 1), ('N', 1)], ('X', 1), (7, 'lastbd')),
    'ZW': ('Wheat.json', 'Wheat', [('Z', 0), ('H', 1), ('K', 1)], ('N', 1), (5, 'lastbd')),
    'KE': ('Wheat.json', 'Wheat', [('Z', 0), ('H', 1), ('K', 1)], ('N', 1), (5, 'lastbd')),
}

BU_PER_MT = {'Corn.json': 39.3679, 'Wheat.json': 36.7437, 'Oilseed,_Soybean.json': 36.7437}

def _norm(v, unit, fname):
    """Return the value in one unit per commodity: bales for cotton, million bushels for grains/soybeans."""
    u = (unit or '').lower()
    if 'metric' in u: return v * BU_PER_MT.get(fname, np.nan)
    if 'bushel' in u or 'bale' in u: return v
    return np.nan

def wasde_su(fname):
    """{(Y, month): {'new': su, 'old': su}} from the US table of each month's WASDE (units normalized)."""
    d = json.load(open(os.path.join(WASDE_DIR, fname)))['data']
    def series(attrs, my):
        out = {}
        for a in attrs:
            for r in d.get(f'United States||{a}||{my}', []):
                v = _norm(r['value'], r.get('unit'), fname)
                if not pd.isna(v): out.setdefault((r['forecastYear'], r['forecastMonth']), v)
        return out
    out = {}
    for Y in range(2007, 2027):
        for rel, my in (('new', f'{Y}/{str(Y + 1)[2:]}'), ('old', f'{Y - 1}/{str(Y)[2:]}')):
            es = series(['Ending Stocks', 'Ending stocks'], my); use = series(['Use, Total', 'Use, total'], my)
            dom = series(['Domestic Use', 'Domestic use', 'Domestic, Total', 'Domestic, total', 'Domestic Total'], my)
            exp = series(['Exports', 'Exports, Total', 'Exports, total'], my)
            for k in set(dom) & set(exp):                 # fill missing total use from its components
                use.setdefault(k, dom[k] + exp[k])
            for m in range(5, 10):
                if (Y, m) in es and (Y, m) in use and use[(Y, m)]:
                    out.setdefault((Y, m), {})[rel] = es[(Y, m)] / use[(Y, m)]
    return out

def su_path(fname, Y):
    """{(report_year, report_month): S/U of MY Y/Y+1} for every WASDE that carried it."""
    d = json.load(open(os.path.join(WASDE_DIR, fname)))['data']; my = f'{Y}/{str(Y + 1)[2:]}'
    def series(attrs):
        out = {}
        for a in attrs:
            for r in d.get(f'United States||{a}||{my}', []):
                v = _norm(r['value'], r.get('unit'), fname)
                if not pd.isna(v): out.setdefault((r['forecastYear'], r['forecastMonth']), v)
        return out
    es = series(['Ending Stocks', 'Ending stocks']); use = series(['Use, Total', 'Use, total'])
    dom = series(['Domestic Use', 'Domestic use', 'Domestic, Total', 'Domestic, total', 'Domestic Total']); exp = series(['Exports', 'Exports, Total', 'Exports, total'])
    for k in set(dom) & set(exp): use.setdefault(k, dom[k] + exp[k])
    return {k: es[k] / use[k] for k in es if k in use and use[k]}

def psd_su(name):
    p = pd.read_csv(os.path.join(DATA, 'psd_us.csv.gz'))
    p = p[p.Commodity_Description == name]
    if not len(p): return pd.Series(dtype=float)
    p = p.pivot_table(index='Market_Year', columns='Attribute_Description', values='Value', aggfunc='sum')
    dom = p['Domestic Consumption'] if 'Domestic Consumption' in p else p['Domestic Use']
    return (p['Ending Stocks'] / (dom + p['Exports'])).dropna()

_rel = pd.read_csv(os.path.join(DATA, 'wasde_release_dates.csv'), parse_dates=['release_date'])
REL = {(r.year, r.month): r.release_date for r in _rel.itertuples()}

def bdays(cal, y, m): return cal[(cal.year == y) & (cal.month == m)]

def trade_pnl(P, cal, root, legs, L, t0, t_exit, roll):
    pnl = 0.0; t = t0; path = []
    for i, leg in enumerate(legs):
        if i < len(legs) - 1:
            M = bt.MC[leg[1]]; y = leg[2]
            m1 = pd.Timestamp(y, M, 1) - pd.offsets.MonthBegin(1); m2 = m1 - pd.offsets.MonthBegin(1)
            bd = bdays(cal, m2.year, m2.month) if roll == 'rogers' else bdays(cal, m1.year, m1.month)
            full = len(bd) >= 15 or (roll == 'rogers' and m2.year * 12 + m2.month < cal[-1].year * 12 + cal[-1].month)
            t_out = (bd[-1] if roll == 'rogers' else bd[6]) if full else t_exit
            t_out = min(t_out, t_exit)
        else:
            t_out = t_exit
        if t_out <= t: continue
        sr = P[leg].reindex(cal).ffill(limit=3); a, b = sr.get(t), sr.get(t_out)
        if pd.isna(a) or pd.isna(b): return None
        pnl += -(b - a); path.append(f"{leg[1]}{leg[2] % 100:02d}"); t = t_out
        if t_out >= t_exit: break
    sl = P[L].reindex(cal).ffill(limit=3); la, lb = sl.get(t0), sl.get(t_exit)
    if pd.isna(la) or pd.isna(lb): return None
    return pnl + (lb - la), path

def run():
    P = bt.load_tv(); rows = []
    for root, (wf, pn, chain, long_leg, (exm, rule)) in SPEC.items():
        keys = [k for k in P if k[0] == root]
        cal = pd.DatetimeIndex(sorted(set().union(*[set(P[k].index) for k in keys])))
        SU = wasde_su(wf); FIN = psd_su(pn)
        for Y in range(2007, 2027):
            for m in range(5, 10):
                if (Y, m) not in SU or 'new' not in SU[(Y, m)]: continue
                rd = REL.get((Y, m), pd.Timestamp(Y, m, 12))   # WASDE release date (noon ET), entry at that day's close
                ent = cal[cal >= rd]
                if not len(ent): continue
                t0 = ent[0]
                legs = [(root, c, Y + o) for c, o in chain]; L = (root, long_leg[0], Y + long_leg[1])
                if any(l not in P for l in legs + [L]): continue
                xb = bdays(cal, Y + 1, exm - 1)                    # month before the exit contract's delivery month
                if len(xb) >= 10:
                    t_exit = xb[-6] if rule == 'ct' else xb[-2]; open_trade = False
                elif pd.Timestamp(Y + 1, exm - 1, 1) > cal[-1]:
                    t_exit = cal[-1]; open_trade = True            # still running: mark to market
                else: continue
                su = SU[(Y, m)]; su_new = su['new']; su_old = su.get('old', np.nan)
                hist = [FIN.get(y) for y in range(Y - 10, Y - 1)] + [su_old]
                hist = [h for h in hist if h is not None and not pd.isna(h)]
                pct10 = 100 * np.mean([h < su_new for h in hist]) if len(hist) >= 6 else np.nan
                # stop rule: first later WASDE (entry month+1 .. exit) where MY Y/Y+1 S/U drops to <=30th pct of the 10y history
                path_su = su_path(wf, Y); t_stop = None; stop_month = None
                for (ry, rm), v in sorted(path_su.items()):
                    if (ry, rm) <= (Y, m): continue
                    td = cal[cal >= REL.get((ry, rm), pd.Timestamp(ry, rm, 12))]
                    if not len(td) or td[0] >= t_exit: break
                    if len(hist) >= 6 and 100 * np.mean([h < v for h in hist]) <= 30:
                        t_stop = td[0]; stop_month = f'{ry}-{rm:02d}'; break
                for roll in ('rogers', 'gsci'):
                    for variant, t_end in (('hold', t_exit), ('stop30', t_stop or t_exit)):
                        r = trade_pnl(P, cal, root, legs, L, t0, t_end, roll)
                        if r is None: continue
                        pnl, path = r
                        f0 = P[legs[0]].reindex(cal).ffill(limit=3).get(t0); la = P[L].reindex(cal).ffill(limit=3).get(t0)
                        rows.append(dict(root=root, Y=Y, entry_month=m, roll=roll, variant=variant, entry=t0.date(), exit=t_end.date(),
                                         open=open_trade and t_end == t_exit, stopped=(variant == 'stop30' and t_stop is not None), stop_month=stop_month if variant == 'stop30' else None,
                                         short_path='>'.join(path), long_leg=f"{L[1]}{L[2] % 100:02d}",
                                         spread_entry=f0 - la, pnl=pnl, usd=pnl * bt.MULT[root], pnl_pct=pnl / f0 * 100,
                                         su_new=su_new, su_old=su_old, su_chg=su_new - su_old, pct10=pct10))
    E = pd.DataFrame(rows); E.to_csv(os.path.join(RES, 'newcrop_spread_events.csv'), index=False)
    return E

if __name__ == '__main__':
    E = run(); print(E.groupby(['root', 'roll', 'variant']).size().unstack())
