import warnings; warnings.filterwarnings('ignore')
import os, numpy as np, pandas as pd, sys
import rollcommon as bt
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
E = pd.read_csv(os.path.join(RES,'v2_events.csv'))
W = ['pre20', 'rogers', 'gsci_d2', 'gsci_d3', 'gsci_full']
for w in W: E['z_' + w] = E[w] / E.sd1
E['era'] = np.where(E.year <= 2013, 'A', 'B')

def st(v):
    v = pd.Series(v).dropna(); n = len(v)
    if n < 5: return dict(n=n, m=np.nan, hit=np.nan, t=np.nan)
    return dict(n=n, m=v.mean(), hit=(v > 0).mean(), t=v.mean() / (v.std() / np.sqrt(n)))
def fmt(d, pct=False):
    if d['n'] < 5: return f"n={d['n']}"
    m = f"{d['m']*100:+.2f}%" if pct else f"{d['m']:+.3f}"
    return f"{m} hit {d['hit']:.0%} t {d['t']:+.1f} n{d['n']}"

out = {}
print('=== A. UNCONDITIONAL, by market (spreads native units / price log-return) ===')
rows = []
for spec in ['s1', 's2', 's3', 'px']:
    for root in ['CT', 'KC', 'SB', 'CC', 'ALL']:
        g = E[E.spec == spec] if root == 'ALL' else E[(E.spec == spec) & (E.root == root)]
        for w in W:
            col = ('z_' + w) if root == 'ALL' else w
            a, b, c = st(g[col]), st(g[g.era == 'A'][col]), st(g[g.era == 'B'][col])
            usd = a['m'] * bt.MULT[root] if (spec != 'px' and root != 'ALL') else np.nan
            rows.append(dict(spec=spec, root=root, win=w, n=a['n'], mean=a['m'], usd=usd, hit=a['hit'], t=a['t'], tA=b['t'], tB=c['t'], mA=b['m'], mB=c['m']))
U = pd.DataFrame(rows); U.to_csv(os.path.join(RES,'v2_uncond.csv'), index=False)
pd.set_option('display.width', 250); pd.set_option('display.max_rows', 400)
print(U.round(4).to_string(index=False))

print('\n=== B. CONDITIONAL on spec net percentile (pooled z, all markets) ===')
B = [('>=90', lambda p: p >= 90), ('>=80', lambda p: p >= 80), ('20-80', lambda p: (p > 20) & (p < 80)), ('<=20', lambda p: p <= 20), ('<=10', lambda p: p <= 10)]
rows = []
for tag in ['nc', 'mm']:
    for spec in ['s1', 's2', 'px']:
        g = E[E.spec == spec]
        for w in W:
            pc = g[f'{tag}_pct'] if w == 'pre20' else g[f'{tag}_pct_r']
            for bn, f in B:
                m = f(pc)
                for era, em in [('all', g.year > 0), ('A', g.era == 'A'), ('B', g.era == 'B')]:
                    d = st(g[m & em]['z_' + w])
                    rows.append(dict(src=tag, spec=spec, win=w, bucket=bn, era=era, **d))
C = pd.DataFrame(rows); C.to_csv(os.path.join(RES,'v2_cond.csv'), index=False)
piv = C[(C.era == 'all')].copy()
piv['cell'] = piv.apply(lambda r: f"{r.m:+.2f} ({r.hit:.0%}, t{r.t:+.1f}, n{r.n})" if r.n >= 5 else f"n{r.n}", axis=1)
for tag in ['nc', 'mm']:
    print(f'\n-- source {tag} --')
    print(piv[piv.src == tag].pivot_table(index=['spec', 'win'], columns='bucket', values='cell', aggfunc='first')[['>=90', '>=80', '20-80', '<=20', '<=10']].to_string())

print('\n=== C. per market, nc source, s1 & px, extremes ===')
rows = []
for spec in ['s1', 'px']:
    for root in ['CT', 'KC', 'SB', 'CC']:
        g = E[(E.spec == spec) & (E.root == root)]
        for w in ['pre20', 'rogers', 'gsci_d3']:
            pc = g['nc_pct'] if w == 'pre20' else g['nc_pct_r']
            r = dict(spec=spec, root=root, win=w)
            for bn, f in B:
                d = st(g[f(pc)][w]); scale = 100 if spec == 'px' else 1
                r[bn] = f"{d['m']*scale:+.2f}/{d['hit']:.0%}/t{d['t']:+.1f}/n{d['n']}" if d['n'] >= 5 else f"n{d['n']}"
            rows.append(r)
print(pd.DataFrame(rows).to_string(index=False))
