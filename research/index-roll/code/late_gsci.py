"""GSCI/BCOM roll, later days: (a) long spread from the close before roll day 1, exit day 2..5;
(b) short spread from the close of roll day 4 or 5, held 5 or 10 trading days."""
import warnings; warnings.filterwarnings('ignore')
import os, sys, numpy as np, pandas as pd
import rollcommon as bt
import build_events as v2          # loads prices + positioning (also rewrites results/v2_events.csv)
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
P = v2.P; rows = []
for root in bt.MARKETS:
    keys = [k for k in P if k[0] == root]
    if not keys: continue
    cal = pd.DatetimeIndex(sorted(set().union(*[set(P[k].index) for k in keys])))
    for (_, code, y) in keys:
        if y < 2000 or code not in bt.CYCLE[root]: continue
        M = bt.MC[code]; m1 = pd.Timestamp(y, M, 1) - pd.offsets.MonthBegin(1)
        d1 = cal[(cal.year == m1.year) & (cal.month == m1.month)]
        if len(d1) < 12 or m1 > pd.Timestamp.today(): continue
        o = 0 if bt.ROLL2[root] == 'gsci' else 1
        ig = cal.get_loc(d1[3 + o])                    # close before roll day 1
        if ig + 16 >= len(cal): continue
        legs = bt.chain(root, code, y, 3)
        if any(l not in P for l in legs): continue
        px = pd.concat([P[l] for l in legs], axis=1, sort=True).reindex(cal).ffill(limit=2); px.columns = [0, 1, 2]
        pct = v2.spec_at(root, 'nc', cal[ig])[1]
        for spec, x in [('s1', px[0] - px[1]), ('s2', px[1] - px[2]), ('px', np.log(px[0]))]:
            v = x.iloc[ig:ig + 16].values
            if np.isnan(v).any(): continue
            sd = x.iloc[max(0, ig - 260):ig].diff().std()
            r = dict(root=root, group=bt.GROUP[root], year=y, spec=spec, pct=pct, sd=sd)
            for k in (2, 3, 4, 5): r[f'long_d{k}'] = v[k] - v[0]
            for e in (4, 5):
                for h in (5, 10): r[f'short_d{e}_h{h}'] = -(v[e + h] - v[e])
            rows.append(r)
D = pd.DataFrame(rows); D.to_csv(os.path.join(RES, 'late_gsci_events.csv'), index=False)
COLS = ['long_d2', 'long_d3', 'long_d4', 'long_d5', 'short_d4_h5', 'short_d4_h10', 'short_d5_h5', 'short_d5_h10']
def st(v):
    v = pd.Series(v).dropna(); n = len(v)
    return f"{(v > 0).mean():.0%} t{v.mean() / (v.std() / np.sqrt(n)):+.1f}" if n > 4 else f"n{n}"
pd.set_option('display.width', 260)
for spec in ['s1', 's2', 'px']:
    d = D[D.spec == spec].copy()
    for c in COLS: d['z_' + c] = d[c] / d.sd
    print(f'\n######## {spec}: hit rate and t (pooled z), positive = trade made money')
    out = {}
    for grp in ['ALL', 'softs', 'grains', 'livestock']:
        g = d if grp == 'ALL' else d[d.group == grp]
        for lab, m in [('all', g.year > 0), ('<=2013', g.year <= 2013), ('2014+', g.year > 2013),
                       ('spec>=80', g.pct >= 80), ('spec20-80', (g.pct > 20) & (g.pct < 80)), ('spec<=20', g.pct <= 20)]:
            out[(grp, lab)] = {c: st(g[m]['z_' + c]) for c in COLS}
    print(pd.DataFrame(out).T.to_string())
    if spec == 's1':
        print('\nper market, all years / 2014+  ($/lot mean, hit)')
        for c in ['long_d4', 'long_d5', 'short_d4_h5', 'short_d5_h10']:
            row = []
            for r in bt.MARKETS:
                g = d[d.root == r][c]; b = d[(d.root == r) & (d.year > 2013)][c]
                row.append(f"{r} {g.mean() * bt.MULT[r]:+.0f}/{(g > 0).mean():.0%} | {b.mean() * bt.MULT[r]:+.0f}/{(b > 0).mean():.0%}")
            print(c, ' ; '.join(row))
