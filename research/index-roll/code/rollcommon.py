"""Index-roll spread backtest: Rogers (RICI) roll, then GSCI (or BCOM) roll. ICE softs, CBOT grains/oilseeds, CME livestock.
Spread = nearby - deferred (price units). 'Sell spread' = short nearby / long deferred.
"""
import sys, os, json, numpy as np, pandas as pd
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MC = dict(F=1, G=2, H=3, J=4, K=5, M=6, N=7, Q=8, U=9, V=10, X=11, Z=12)
# root: (index contract cycle per RICI Appendix A, $ per 1.00 price unit, unit, CFTC code, second roll, group)
# second roll: 'gsci' = business days 5-9 of M-1; 'bcom' = days 6-10 (soy meal/oil are not in the GSCI)
MARKETS = {
    'CT': ('HKNZ',   500,  '¢/lb',  33661, 'gsci', 'softs'),
    'SB': ('HKNV',   1120, '¢/lb',  80732, 'gsci', 'softs'),
    'KC': ('HKNUZ',  375,  '¢/lb',  83731, 'gsci', 'softs'),
    'CC': ('HKNUZ',  10,   '$/t',   73732, 'gsci', 'softs'),
    'ZC': ('HKNUZ',  50,   '¢/bu',  2602,  'gsci', 'grains'),
    'ZW': ('HKNUZ',  50,   '¢/bu',  1602,  'gsci', 'grains'),
    'KE': ('HKNUZ',  50,   '¢/bu',  1612,  'gsci', 'grains'),
    'ZS': ('FHKNX',  50,   '¢/bu',  5602,  'gsci', 'grains'),
    'ZM': ('FHKNZ',  100,  '$/st',  26603, 'bcom', 'grains'),
    'ZL': ('FHKNZ',  600,  '¢/lb',  7601,  'bcom', 'grains'),
    'LE': ('GJMQVZ', 400,  '¢/lb',  57642, 'gsci', 'livestock'),
    'HE': ('GJMQVZ', 400,  '¢/lb',  54642, 'gsci', 'livestock'),
}
CYCLE = {k: v[0] for k, v in MARKETS.items()}
MULT = {k: v[1] for k, v in MARKETS.items()}
UNIT = {k: v[2] for k, v in MARKETS.items()}
CFTC = {v[3]: k for k, v in MARKETS.items()}
ROLL2 = {k: v[4] for k, v in MARKETS.items()}
GROUP = {k: v[5] for k, v in MARKETS.items()}

def load_tv(paths=(DATA+'/tv_contracts.csv.gz', DATA+'/ags_contracts.csv.gz')):
    k = pd.concat([pd.read_csv(p) for p in paths if os.path.exists(p)]); P = {}
    for sym, g in k.groupby('symbol'):
        x = pd.Series(g.close.values, index=pd.to_datetime(g.date)).sort_index()
        x = x[~x.index.duplicated(keep='last')]
        med = x.rolling(11, center=True, min_periods=3).median()
        x = x[(x / med - 1).abs() <= 0.20]          # drop bad ticks (>20% off the local 11-day median)
        P[(sym[:2], sym[2], int(sym[3:]))] = x
    return P


def chain(root, code, y, n=4):
    cyc = CYCLE[root]; i = cyc.index(code); out = []
    for j in range(n):
        out.append((root, cyc[(i + j) % len(cyc)], y + (i + j) // len(cyc)))
    return out



