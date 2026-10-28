"""v2: single-source TradingView contracts. Spread + flat-price tests around Rogers and GSCI rolls,
unconditional and conditional on spec positioning percentile."""
import warnings; warnings.filterwarnings('ignore')
import os, numpy as np, pandas as pd, json
import rollcommon as bt
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "..", "data"); RES = os.path.join(HERE, "..", "results")

P = bt.load_tv()
CODE = {33661: 'CT', 83731: 'KC', 80732: 'SB', 73732: 'CC'}

def spec_series():
    out = {}
    L = pd.read_csv(os.path.join(DATA,'cot_legacy.csv.gz'), low_memory=False)
    D = pd.read_csv(os.path.join(DATA,'cot_disagg.csv.gz'), low_memory=False)
    for df, lc, sc, tag in [(L, 'noncomm_positions_long_all', 'noncomm_positions_short_all', 'nc'),
                            (D, 'm_money_positions_long_all', 'm_money_positions_short_all', 'mm')]:
        df['d'] = pd.to_datetime(df.report_date_as_yyyy_mm_dd)
        for code, root in CODE.items():
            g = df[df.cftc_contract_market_code == code].sort_values('d').drop_duplicates('d')
            net = (g[lc] - g[sc]) / g.open_interest_all
            s = pd.Series(net.values, index=g.d)
            # trailing 3y percentile (156 reports incl. current), no look-ahead
            pct = s.rolling(156, min_periods=104).apply(lambda w: (w[:-1] < w[-1]).mean() * 100, raw=True)
            out[(root, tag)] = pd.DataFrame({'net': s, 'pct': pct})
    return out
SPEC = spec_series()

def spec_at(root, tag, t):
    s = SPEC[(root, tag)]
    s = s[s.index + pd.Timedelta(days=3) <= t]   # Tuesday report public by Friday
    return (np.nan, np.nan) if not len(s) else tuple(s.iloc[-1][['net', 'pct']])

rows = []
for root in ['CT', 'SB', 'KC', 'CC']:
    keys = [k for k in P if k[0] == root]
    cal = pd.DatetimeIndex(sorted(set().union(*[set(P[k].index) for k in keys])))
    for (_, code, y) in sorted(keys, key=lambda k: (k[2], bt.MC[k[1]])):
        if y < 2000: continue
        M = bt.MC[code]; m1 = pd.Timestamp(y, M, 1) - pd.offsets.MonthBegin(1); m2 = m1 - pd.offsets.MonthBegin(1)
        d2 = cal[(cal.year == m2.year) & (cal.month == m2.month)]; d1 = cal[(cal.year == m1.year) & (cal.month == m1.month)]
        if len(d2) < 5 or len(d1) < 12 or m1 > pd.Timestamp('2026-10-28'): continue
        legs = bt.chain(root, code, y)
        if any(l not in P for l in legs): continue
        px = pd.concat([P[l] for l in legs], axis=1, sort=True); px.columns = range(4); px = px.reindex(cal).ffill(limit=2)
        i_in = cal.get_loc(d2[-3])
        if i_in < 61: continue
        ev = dict(pre=cal[i_in - 20], r_in=d2[-3], r_out=d1[0], g_in=d1[3], g2=d1[5], g3=d1[6], g_end=d1[8])
        base = dict(root=root, contract=f'{root}{code}{y % 100:02d}', front=code, year=y)
        for tag in ('nc', 'mm'):
            base[f'{tag}_net'], base[f'{tag}_pct'] = spec_at(root, tag, ev['pre'])
            base[f'{tag}_pct_r'] = spec_at(root, tag, ev['r_in'])[1]
        f = px[0]; lr = np.log(f)
        dly = lr.diff().loc[ev['r_in'] - pd.Timedelta(days=400): ev['r_in']].std()
        try:
            flat = dict(spec='px', pre20=lr[ev['r_in']] - lr[ev['pre']], rogers=lr[ev['r_out']] - lr[ev['r_in']],
                        gsci_d2=lr[ev['g2']] - lr[ev['g_in']], gsci_d3=lr[ev['g3']] - lr[ev['g_in']],
                        gsci_full=lr[ev['g_end']] - lr[ev['g_in']], sd1=dly)
        except KeyError: continue
        if not any(pd.isna(list(flat.values()))): rows.append({**base, **flat})
        for s in (1, 2, 3):
            x = px[s - 1] - px[s]
            try:
                v = {k: x.loc[t] for k, t in ev.items()}
            except KeyError: continue
            if any(pd.isna(list(v.values()))): continue
            sd = x.loc[ev['r_in'] - pd.Timedelta(days=400): ev['r_in']].diff().std()
            rows.append({**base, 'spec': f's{s}',
                         # sign: positive = spread WEAKENED for pre20/rogers (short-spread P&L); positive = STRENGTHENED for gsci (long P&L)
                         'pre20': -(v['r_in'] - v['pre']), 'rogers': -(v['r_out'] - v['r_in']),
                         'gsci_d2': v['g2'] - v['g_in'], 'gsci_d3': v['g3'] - v['g_in'], 'gsci_full': v['g_end'] - v['g_in'], 'sd1': sd})
E = pd.DataFrame(rows); E.to_csv(os.path.join(RES,'v2_events.csv'), index=False)
print(E.groupby(['spec', 'root']).year.agg(['min', 'max', 'count']).to_string())
