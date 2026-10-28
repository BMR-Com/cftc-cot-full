"""Refresh live ICE softs contracts (CT, KC, SB, CC) from TradingView into data/softs/live_contracts.csv.
History for expired contracts stays in research/index-roll/data/tv_contracts.csv.gz (static).
Runs on GitHub Actions (TradingView is reachable from runners)."""
import os, time, datetime as dt
import pandas as pd
from tvDatafeed import TvDatafeed, Interval
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'data', 'softs', 'live_contracts.csv')
CYC = {'CT': 'HKNZ', 'KC': 'HKNUZ', 'SB': 'HKNV', 'CC': 'HKNUZ'}
MC = dict(F=1, G=2, H=3, J=4, K=5, M=6, N=7, Q=8, U=9, V=10, X=11, Z=12)
today = dt.date.today(); tv = TvDatafeed(); rows = []
for root, cyc in CYC.items():
    for y in range(today.year, today.year + 3):
        for c in cyc:
            exp = dt.date(y, MC[c], 1)
            if exp < today - dt.timedelta(days=45) or exp > today + dt.timedelta(days=900): continue
            sym = f'{root}{c}{y}'; d = None
            for _ in range(3):
                try:
                    d = tv.get_hist(symbol=sym, exchange='ICEUS', interval=Interval.in_daily, n_bars=900)
                    if d is not None and len(d): break
                except Exception as e: print('retry', sym, e)
                time.sleep(2)
            if d is None or not len(d): print('MISSING', sym); continue
            d = d.reset_index(); d['date'] = d['datetime'].dt.date; d['symbol'] = sym
            rows.append(d[['symbol', 'date', 'close', 'volume']]); print(sym, len(d), d.date.max())
if not rows: raise SystemExit('no data fetched')
new = pd.concat(rows)
if os.path.exists(OUT):                       # keep contracts that dropped off the live list
    old = pd.read_csv(OUT); old = old[~old.symbol.isin(new.symbol.unique())]; new = pd.concat([old, new])
os.makedirs(os.path.dirname(OUT), exist_ok=True)
new.sort_values(['symbol', 'date']).to_csv(OUT, index=False); print('saved', OUT, len(new))
