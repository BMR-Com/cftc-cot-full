"""After the GSCI/BCOM roll: long front spread from the close of roll day 4/5 (or day 3),
exited before the front contract's first notice / expiry. Exit rules (business days of month M-1, N = count):
CT FND = 5 BD before 1st BD of M -> exit BD N-5; KC 7 BD -> N-7; CC 10 BD -> N-10;
SB expires last BD of M-1 -> exit N-1; CBOT grains FND = last BD of M-1 -> exit N-1;
LE/HE expire in month M -> exit last BD of M-1."""
import warnings; warnings.filterwarnings('ignore')
import os, numpy as np, pandas as pd
import rollcommon as bt, build_events as v2
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'results')
EXIT_BACK = dict(CT=5, KC=7, CC=10, SB=1, ZC=1, ZW=1, KE=1, ZS=1, ZM=1, ZL=1, LE=0, HE=0)
P = v2.P; rows = []; paths = []
for root in bt.MARKETS:
    keys = [k for k in P if k[0] == root]
    cal = pd.DatetimeIndex(sorted(set().union(*[set(P[k].index) for k in keys])))
    for (_, code, y) in keys:
        if y < 2000 or code not in bt.CYCLE[root]: continue
        M = bt.MC[code]; m1 = pd.Timestamp(y, M, 1) - pd.offsets.MonthBegin(1)
        d1 = cal[(cal.year == m1.year) & (cal.month == m1.month)]
        if len(d1) < 15 or d1[-1] > pd.Timestamp.today() - pd.Timedelta(days=1): continue
        o = 0 if bt.ROLL2[root] == 'gsci' else 1
        N = len(d1); ex = N - EXIT_BACK[root] - 1          # 0-based index of exit day in d1
        legs = bt.chain(root, code, y, 2)
        if any(l not in P for l in legs): continue
        x = (P[legs[0]] - P[legs[1]]).reindex(cal).ffill(limit=2)
        sd = x.loc[:d1[0]].iloc[-260:].diff().std()
        pct = v2.spec_at(root, 'nc', d1[3 + o])[1]
        r = dict(root=root, group=bt.GROUP[root], year=y, pct=pct, sd=sd, hold_from_d5=ex - (8 + o))
        for e, lab in [(6 + o, 'd3'), (7 + o, 'd4'), (8 + o, 'd5')]:
            r[f'long_{lab}_to_exit'] = (x.loc[d1[ex]] - x.loc[d1[e]]) if ex > e else np.nan
        r['long_d5_h3'] = (x.loc[d1[min(8 + o + 3, ex)]] - x.loc[d1[8 + o]]) if ex > 8 + o else np.nan
        if not np.isnan(list(r.values())[-1]) or True: rows.append(r)
        seg = x.loc[d1[3 + o]:].iloc[:N - 3 - o]
        if len(seg) >= 15 and not seg.iloc[:15].isna().any(): paths.append((bt.GROUP[root], root, ((seg.iloc[:15] - seg.iloc[0]) / sd).values))
D = pd.DataFrame(rows); D.to_csv(os.path.join(RES, 'post_roll_events.csv'), index=False)
def st(v):
    v = pd.Series(v).dropna(); n = len(v)
    return f"{(v > 0).mean():.0%} t{v.mean() / (v.std() / np.sqrt(n)):+.1f} n{n}" if n > 4 else f"n{n}"
C = ['long_d3_to_exit', 'long_d4_to_exit', 'long_d5_to_exit', 'long_d5_h3']
print('typical days held after GSCI day 5 before exit:', D.groupby('root').hold_from_d5.median().to_dict())
out = {}
for grp in ['ALL', 'softs', 'grains', 'livestock'] + list(bt.MARKETS):
    g = D if grp == 'ALL' else (D[D.group == grp] if grp in ('softs', 'grains', 'livestock') else D[D.root == grp])
    for lab, m in [('all', g.year > 0), ('<=2013', g.year <= 2013), ('2014+', g.year > 2013), ('spec>=80', g.pct >= 80), ('spec<=20', g.pct <= 20)]:
        if grp in bt.MARKETS and lab not in ('all', '2014+'): continue
        out[(grp, lab)] = {c: st((g[m][c] / g[m].sd)) for c in C}
        if grp in bt.MARKETS:
            out[(grp, lab)]['$/lot d5->exit'] = f"{g[m]['long_d5_to_exit'].mean() * bt.MULT[grp]:+.0f}"
pd.set_option('display.width', 250); print(pd.DataFrame(out).T.fillna('').to_string())
A = {}
for grp in ['softs', 'grains', 'livestock']:
    A[grp] = np.round(np.mean([p for g, r, p in paths if g == grp], axis=0), 2)
print('\navg front-spread path from close before roll day 1 (z, +ve = stronger), days 0..14:')
for k, v in A.items(): print(k, v.tolist())
