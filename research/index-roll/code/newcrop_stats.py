import os, numpy as np, pandas as pd
import rollcommon as bt
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
E = pd.read_csv(os.path.join(RES, 'newcrop_spread_events.csv')); C = E[~E.open & (E.roll == 'gsci')].copy()
def s(g):
    if not len(g): return ''
    return f"{(g.pnl > 0).mean():.0%} · {g.usd.mean():+,.0f} · worst {g.usd.min():+,.0f} (n{len(g)})"
pd.set_option('display.width', 280); pd.set_option('display.max_colwidth', 60)
FILT = {'all': lambda g: g.Y > 0, 'loose >=70th': lambda g: g.pct10 >= 70, 'not tight >30th': lambda g: g.pct10 > 30, 'tight <=30th': lambda g: g.pct10 <= 30}
for root in ['CT', 'ZC', 'ZS', 'ZW', 'KE']:
    out = {}
    for v in ['hold', 'stop30']:
        for fl, f in FILT.items():
            for m in [5, 6, 7, 8, 9]:
                g = C[(C.root == root) & (C.variant == v) & (C.entry_month == m)]; out[(v, fl, m)] = s(g[f(g)])
    df = pd.Series(out).unstack(2); df.columns = ['May', 'Jun', 'Jul', 'Aug', 'Sep']
    print(f'\n#### {root}: win% · avg $/spread · worst (GSCI-roll timing, closed trades 2010-2025)'); print(df.to_string())
print('\n#### pooled, % of front price')
for v in ['hold', 'stop30']:
    for fl, f in FILT.items():
        row = []
        for m in [5, 6, 7, 8, 9]:
            g = C[(C.variant == v) & (C.entry_month == m)]; g = g[f(g)]
            row.append(f"{(g.pnl > 0).mean():.0%} {g.pnl_pct.mean():+.1f}% n{len(g)}")
        print(f"{v:7s} {fl:16s}", ' | '.join(row))
R = E[~E.open]; print('\nrogers - gsci avg $:', {r: round(R[(R.root == r) & (R.roll == 'rogers')].usd.mean() - R[(R.root == r) & (R.roll == 'gsci')].usd.mean()) for r in ['CT', 'ZC', 'ZS', 'ZW', 'KE']})
