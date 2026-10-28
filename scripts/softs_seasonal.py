"""Softs seasonality builder (CT, KC, SB, CC): contract returns by calendar month, front-month heat map,
calendar-spread seasonality (first three spreads), the first-notice switch trade, seasonal charts and a
list of seasonal trades with their next dates.

Input : research/index-roll/data/tv_contracts.csv.gz  (TradingView daily closes, every contract since 2000)
Output: data/web/softs_seasonal.json (site), research/index-roll/results/seasonal_*.csv (full detail, git-ignored)
"""
import os, json, datetime as dt, warnings
warnings.filterwarnings('ignore')
import numpy as np, pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'research', 'index-roll', 'data', 'tv_contracts.csv.gz')
LIVE = os.path.join(ROOT, 'data', 'softs', 'live_contracts.csv')
OUT = os.path.join(ROOT, 'data', 'web', 'softs_seasonal.json')
RES = os.path.join(ROOT, 'research', 'index-roll', 'results')
MC = dict(F=1, G=2, H=3, J=4, K=5, M=6, N=7, Q=8, U=9, V=10, X=11, Z=12)
MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
CODE_NAME = {c: MON[m - 1] for c, m in MC.items()}
MK = {  # name, cycle, $ per 1.00 price unit, unit, business days from first notice to the first BD of delivery month (SB: last trade)
    'CT': ('Cotton', 'HKNZ', 500, '¢/lb', 5),
    'KC': ('Arabica coffee', 'HKNUZ', 375, '¢/lb', 7),
    'SB': ('Raw sugar', 'HKNV', 1120, '¢/lb', 1),
    'CC': ('Cocoa', 'HKNUZ', 10, '$/t', 10),
}
FIRST_YEAR, MIN_N = 2000, 12

def load():
    d = pd.read_csv(SRC)
    if os.path.exists(LIVE):                     # daily refresh of live contracts overrides the static history
        lv = pd.read_csv(LIVE); d = pd.concat([d[~d.symbol.isin(lv.symbol.unique())], d[d.symbol.isin(lv.symbol.unique())], lv])
        d = d.drop_duplicates(['symbol', 'date'], keep='last')
    P = {}
    for sym, g in d.groupby('symbol'):
        idx = pd.to_datetime(g.date)
        idx = idx + pd.to_timedelta((idx.dt.dayofweek == 6).astype(int), unit='D')   # TradingView dates ICE cotton Mondays as Sunday
        x = pd.Series(g.close.values, index=idx.values).sort_index()
        x = x[~x.index.duplicated(keep='last')]
        med = x.rolling(11, center=True, min_periods=3).median()
        P[(sym[:2], sym[2], int(sym[3:]))] = x[(x / med - 1).abs() <= 0.20]
    return P

class Market:
    def __init__(self, root, P):
        self.root = root; self.name, self.cyc, self.mult, self.unit, self.fnd_back = MK[root]
        self.P = {k: v for k, v in P.items() if k[0] == root and k[1] in self.cyc}
        self.cal = pd.DatetimeIndex(sorted(set().union(*[set(s.index) for s in self.P.values()])))
        self.fnd = {}
        for k in self.P:
            M = MC[k[1]]; y = k[2]
            first = self.cal[self.cal >= pd.Timestamp(y, M, 1)]
            if len(first) and first[0].month == M:
                i = self.cal.get_loc(first[0]); self.fnd[k] = self.cal[i - self.fnd_back]
            else:   # future: approximate with business days
                fb = pd.bdate_range(pd.Timestamp(y, M, 1), periods=1)[0]
                self.fnd[k] = fb - pd.offsets.BDay(self.fnd_back)
    def nxt(self, k, j=1):
        c = self.cyc; i = c.index(k[1]) + j
        return (self.root, c[i % len(c)], k[2] + i // len(c))
    def s(self, k): return self.P.get(k)
    def px(self, k, t):
        s = self.P.get(k)
        if s is None: return np.nan
        s = s[s.index <= t]
        return s.iloc[-1] if len(s) and (t - s.index[-1]).days <= 5 else np.nan
    def label(self, k): return f"{CODE_NAME[k[1]]} {k[2]}"
    def front_for(self, t):
        """front contract = nearest whose first notice is after t"""
        cands = sorted([k for k in self.P if self.fnd[k] > t], key=lambda k: self.fnd[k])
        return cands[0] if cands else None

def stats(v):
    v = pd.Series(v, dtype=float).dropna(); n = len(v)
    if n < 3: return dict(n=n)
    sd = v.std(ddof=1)
    return dict(n=n, avg=v.mean(), med=v.median(), hit=(v > 0).mean(), t=v.mean() / (sd / np.sqrt(n)) if sd > 0 else np.nan,
                worst=v.min(), best=v.max())

def consistency(years, vals, sgn, split=2013):
    y = np.asarray(years); v = sgn * np.asarray(vals, dtype=float); ok = ~np.isnan(v); y, v = y[ok], v[ok]
    e, l = v[y < split], v[y >= split]; last10 = v[np.argsort(y)][-10:]
    return dict(early_avg=e.mean() if len(e) else np.nan, late_avg=l.mean() if len(l) else np.nan,
                hit_last10=round(100 * (last10 > 0).mean()) if len(last10) else None)

# ---------------------------------------------------------------- 1) first-notice switch trade
def fnd_switch(m, back=5, holds=(10, 21)):
    rows = []
    for P_ in sorted(m.P, key=lambda k: (k[2], MC[k[1]])):
        C = m.nxt(P_)
        if C not in m.P or P_[2] < FIRST_YEAR: continue
        f = m.fnd[P_]
        if f > m.cal[-1]: continue
        i = m.cal.get_loc(f) if f in m.cal else m.cal.searchsorted(f)
        e = m.cal[i - back]
        for h in holds:
            if i - back + h >= len(m.cal): continue
            x = m.cal[i - back + h]; a, b = m.px(C, e), m.px(C, x)
            if pd.isna(a) or pd.isna(b): continue
            rows.append(dict(root=m.root, contract=C[1], prev=P_[1], year=C[2], hold=h, entry=e.date(), exit=x.date(),
                             ret=b / a - 1, chg=b - a, usd=(b - a) * m.mult))
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- 2) contract returns by calendar month
def month_ends(m):
    me = pd.Series(m.cal, index=m.cal).groupby([m.cal.year, m.cal.month]).max()
    return {k: v for k, v in me.items()}

def contract_months(m):
    ME = month_ends(m); rows = []
    for k, s in m.P.items():
        if k[2] < FIRST_YEAR + 1: continue
        stop = m.fnd[k] - pd.Timedelta(days=1)
        for back in range(1, 13):                      # calendar months before the delivery month
            t = pd.Timestamp(k[2], MC[k[1]], 1) - pd.DateOffset(months=back)
            end = ME.get((t.year, t.month)); prev_t = t - pd.DateOffset(months=1); start = ME.get((prev_t.year, prev_t.month))
            if end is None or start is None: continue
            end = min(end, stop)
            if end <= start: continue
            a, b = m.px(k, start), m.px(k, end)
            if pd.isna(a) or pd.isna(b): continue
            rows.append(dict(root=m.root, contract=k[1], year=k[2], cal_month=t.month, cal_year=t.year, back=back, ret=b / a - 1, chg=b - a))
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- 3) front month + first three spreads by calendar month
def front_and_spreads(m):
    ME = month_ends(m); rows = []
    keys = sorted(ME)
    for i in range(1, len(keys)):
        (y, mo), (py, pm) = keys[i], keys[i - 1]
        if y < FIRST_YEAR: continue
        start, end = ME[(py, pm)], ME[(y, mo)]
        f = m.front_for(end)
        if f is None: continue
        chain = [f, m.nxt(f, 1), m.nxt(f, 2), m.nxt(f, 3)]
        p0 = [m.px(k, start) for k in chain]; p1 = [m.px(k, end) for k in chain]
        r = dict(root=m.root, year=y, month=mo, front=f[1] + str(f[2] % 100).zfill(2))
        r['ret'] = p1[0] / p0[0] - 1 if not (pd.isna(p0[0]) or pd.isna(p1[0])) else np.nan
        for j in (1, 2, 3):
            a = p0[j - 1] - p0[j]; b = p1[j - 1] - p1[j]
            r[f's{j}'] = b - a; r[f's{j}_pair'] = f"{CODE_NAME[chain[j-1][1]]}/{CODE_NAME[chain[j][1]]}"
            r[f's{j}_lvl'] = b
        rows.append(r)
    return pd.DataFrame(rows)

# ---------------------------------------------------------------- 4) seasonal chart series (weeks to first notice)
def seas_series(m, kind, code, today):
    """kind 'px' (contract) or 'sp' (contract minus the next one), aligned on weeks before the contract's first notice."""
    by_year = {}
    for k in m.P:
        if k[1] != code: continue
        f = m.fnd[k]; other = m.nxt(k) if kind == 'sp' else None
        if kind == 'sp' and other not in m.P: continue
        vals = []
        for w in range(0, 53):
            t = f - pd.Timedelta(days=7 * w + 1)
            if t > today: vals.append(None); continue
            a = m.px(k, t)
            v = a - m.px(other, t) if kind == 'sp' else a
            vals.append(None if pd.isna(v) else round(float(v), 3))
        by_year[k[2]] = vals
    yrs = sorted(by_year); cur = min([y for y in yrs if m.fnd[(m.root, code, y)] > today], default=None)
    if cur is None: return None
    hist = [y for y in yrs if y < cur and y >= FIRST_YEAR + 1]
    A = np.array([[np.nan if v is None else v for v in by_year[y]] for y in hist], dtype=float)
    bands = {}
    for q in (10, 25, 50, 75, 90):
        col = np.nanpercentile(A, q, axis=0) if len(A) else []
        bands[q] = [[w, round(float(v), 3)] for w, v in enumerate(col) if not np.isnan(v)]
    avg5 = np.nanmean(A[-5:], axis=0) if len(A) >= 5 else []
    pts = lambda arr: [[w, v] for w, v in enumerate(arr) if v is not None and not (isinstance(v, float) and np.isnan(v))]
    k = (m.root, code, cur)
    nm = m.label(k) if kind == 'px' else f"{CODE_NAME[code]}/{CODE_NAME[m.nxt(k)[1]]} {cur}"
    now_w = next((w for w, v in enumerate(by_year[cur]) if v is not None), None)
    now_v = by_year[cur][now_w] if now_w is not None else None
    same = [r[now_w] for r in A if now_w is not None and not np.isnan(r[now_w])]
    return dict(key=f"{m.root}-{kind}-{code}", root=m.root, kind=kind, code=code, label=nm, fnd=str(m.fnd[k].date()),
                current=pts(by_year[cur]), last_year=pts(by_year.get(cur - 1, [])), avg5=[[w, round(float(v), 3)] for w, v in enumerate(avg5) if not np.isnan(v)],
                bands=bands, now=now_v, wk_now=now_w, pct_same_time=(100 * np.mean([s < now_v for s in same]) if same and now_v is not None else None),
                n_years=len(hist), first_year=hist[0] if hist else None)

# ---------------------------------------------------------------- 5) trade list
def next_window(m, kind, row, today):
    """next calendar date range for a seasonal rule"""
    if kind == 'fnd':
        P_ = [k for k in m.P if k[1] == row['prev'] and m.fnd[k] > today + pd.Timedelta(days=7)]
        if not P_: return None
        P_ = min(P_, key=lambda k: m.fnd[k]); f = m.fnd[P_]
        e = f - pd.offsets.BDay(5); x = e + pd.offsets.BDay(int(row['hold']))
        return e.date(), x.date(), m.label(m.nxt(P_))
    y = today.year + (1 if row['month'] < today.month or (row['month'] == today.month and today.day > 3) else 0)
    s = pd.Timestamp(y, row['month'], 1) - pd.offsets.BDay(1); e = pd.Timestamp(y, row['month'], 1) + pd.offsets.MonthEnd(0)
    return s.date(), e.date(), None

def build():
    P = load(); today = max(s.index.max() for s in P.values())
    out = dict(generated=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC'), as_of=str(today.date()), markets={}, trades=[], seasonal=[])
    allF, allC, allS = [], [], []
    for root in MK:
        m = Market(root, P); name, cyc, mult, unit, _ = MK[root]
        F = fnd_switch(m); C = contract_months(m); S = front_and_spreads(m)
        allF.append(F); allC.append(C); allS.append(S)
        done = lambda df: df[df.year <= today.year - (0 if today.month == 12 else 1)] if 'cal_year' not in df else df[(df.cal_year < today.year) | ((df.cal_year == today.year) & (df.cal_month < today.month))]
        # heat map 1: contract x calendar month (avg % and hit)
        Cd = C[(C.cal_year < today.year) | ((C.cal_year == today.year) & (C.cal_month < today.month))]
        hm = {}
        for code in cyc:
            row = {}
            for back in range(12, 0, -1):
                g = Cd[(Cd.contract == code) & (Cd.back == back)]
                if len(g) < MIN_N: continue
                mo = int(g.cal_month.iloc[0]); st = stats(g.ret)
                row[MON[mo - 1]] = dict(back=back, avg=round(st['avg'] * 100, 2), hit=round(st['hit'] * 100), n=st['n'], med=round(st['med'] * 100, 2))
            hm[code] = row
        # heat map 2: front-month returns, year x month + averages
        Sd = S[(S.year < today.year) | ((S.year == today.year) & (S.month <= today.month))]
        grid = {int(y): {int(r.month): (None if pd.isna(r.ret) else round(r.ret * 100, 1)) for r in g.itertuples()} for y, g in Sd.groupby('year')}
        Sc = Sd[(Sd.year < today.year) | (Sd.month < today.month)]
        favg = {MON[mo - 1]: dict(avg=round(g.ret.mean() * 100, 2), hit=round((g.ret > 0).mean() * 100), n=int(g.ret.notna().sum())) for mo, g in Sc.groupby('month')}
        # heat map 3: spreads by month (front-2nd, 2nd-3rd, 3rd-4th) and by named pair
        sp = {}
        for j in (1, 2, 3):
            sp[f's{j}'] = {MON[mo - 1]: dict(avg=round(g[f's{j}'].mean(), 3), hit=round((g[f's{j}'] > 0).mean() * 100), n=int(g[f's{j}'].notna().sum()),
                                              pair=g[f's{j}_pair'].mode().iloc[0]) for mo, g in Sc.groupby('month')}
        fs = []
        for (code, h), g in F.groupby(['contract', 'hold']):
            st = stats(g.ret)
            if st['n'] < MIN_N: continue
            fs.append(dict(contract=CODE_NAME[code], prev=CODE_NAME[g.prev.iloc[0]], hold=int(h), n=st['n'], hit=round(st['hit'] * 100),
                           avg=round(st['avg'] * 100, 2), med=round(st['med'] * 100, 2), usd=round(g.usd.mean()), worst=round(st['worst'] * 100, 1),
                           last5=[round(x * 100, 1) for x in g.sort_values('year').ret.tail(5)]))
        out['markets'][root] = dict(name=name, unit=unit, mult=mult, cycle=[CODE_NAME[c] for c in cyc],
                                    contract_heat=hm, front_grid=grid, front_avg=favg, spread_heat=sp, fnd_switch=fs)
        # seasonal chart series
        for code in cyc:
            for kind in ('px', 'sp'):
                z = seas_series(m, kind, code, today)
                if z: out['seasonal'].append(z)
        # candidate trades: first-notice switch
        for (code, h), g in F.groupby(['contract', 'hold']):
            g = g[g.year <= today.year]; st = stats(g.ret)
            if st['n'] < MIN_N: continue
            side = 'Long' if st['avg'] > 0 else 'Short'; hit = st['hit'] if side == 'Long' else 1 - st['hit']
            sgn = 1 if side == 'Long' else -1
            last5 = [round(sgn * r * 100, 1) for r in g.sort_values('year').ret.tail(5)]
            nw = next_window(m, 'fnd', dict(prev=g.prev.iloc[0], hold=h), today)
            out['trades'].append(dict(root=root, market=name, family='First-notice switch', side=side,
                                      what=f"{side} {CODE_NAME[code]} from 5 days before {CODE_NAME[g.prev.iloc[0]]} first notice, hold {h} days",
                                      hit=round(hit * 100), avg_pct=round(sgn * st['avg'] * 100, 2), usd=round(sgn * g.usd.mean()), n=st['n'],
                                      worst_pct=round(min(sgn * g.ret) * 100, 1), last5=last5, t=st['t'] * sgn,
                                      next_entry=str(nw[0]) if nw else None, next_exit=str(nw[1]) if nw else None, contract=nw[2] if nw else None,
                                      **consistency(g.year.values, g.ret.values, sgn)))
        # candidate trades: front month and spreads by calendar month
        for mo, g in Sc.groupby('month'):
            for col, fam, unit_ in [('ret', 'Front month', '%')] + [(f's{j}', f'Spread {j}', unit) for j in (1, 2, 3)]:
                v = g[col].dropna(); st = stats(v)
                if st['n'] < MIN_N: continue
                side = ('Long' if st['avg'] > 0 else 'Short') if col == 'ret' else ('Bull spread (buy front)' if st['avg'] > 0 else 'Bear spread (sell front)')
                sgn = 1 if st['avg'] > 0 else -1; hit = st['hit'] if sgn > 0 else 1 - st['hit']
                pair = '' if col == 'ret' else g[f'{col}_pair'].mode().iloc[0]
                usd = None if col == 'ret' else round(sgn * v.mean() * mult)
                nw = next_window(m, 'month', dict(month=mo), today)
                out['trades'].append(dict(root=root, market=name, family=fam, side=side,
                                          what=(f"{side} front month in {MON[mo-1]}" if col == 'ret' else f"{side} {pair} in {MON[mo-1]}"),
                                          hit=round(hit * 100), avg_pct=round(sgn * st['avg'] * 100, 2) if col == 'ret' else None,
                                          avg_chg=None if col == 'ret' else round(sgn * st['avg'], 3), usd=usd, n=st['n'],
                                          worst_pct=round(min(sgn * v) * 100, 1) if col == 'ret' else None,
                                          worst_chg=None if col == 'ret' else round(min(sgn * v), 3),
                                          last5=[round(sgn * x * (100 if col == 'ret' else 1), 2) for x in g.sort_values('year')[col].dropna().tail(5)],
                                          t=st['t'] * sgn, next_entry=str(nw[0]), next_exit=str(nw[1]), contract=None, month=MON[mo - 1],
                                          **consistency(g.year.values, g[col].values, sgn)))
    os.makedirs(RES, exist_ok=True)
    pd.concat(allF).to_csv(os.path.join(RES, 'seasonal_fnd_switch.csv'), index=False)
    pd.concat(allC).to_csv(os.path.join(RES, 'seasonal_contract_months.csv'), index=False)
    pd.concat(allS).to_csv(os.path.join(RES, 'seasonal_front_spreads.csv'), index=False)
    T = pd.DataFrame(out['trades']); T.to_csv(os.path.join(RES, 'seasonal_trades_all.csv'), index=False)
    return out, T

def publish(out, T, min_hit=70, min_t=2.0):
    """keep only the rules that pass the screen (hit rate, significance, same sign in both halves of the
    history); screening statistics are not published"""
    keep = T[(T.hit >= min_hit) & (T.t >= min_t) & (T.early_avg > 0) & (T.late_avg > 0)].copy()
    keep = keep.sort_values(['hit', 't'], ascending=False)
    out['trades'] = [{k: (None if (isinstance(v, float) and np.isnan(v)) else v) for k, v in r.items() if k not in ('t', 'early_avg', 'late_avg')} for r in keep.to_dict('records')]
    out['screen'] = dict(min_hit=min_hit, min_years=MIN_N)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'), default=str)
    return keep

if __name__ == '__main__':
    out, T = build(); keep = publish(out, T)
    print(f"{len(T)} rules tested, {len(keep)} published; json {os.path.getsize(OUT)/1024:.0f} KB")
