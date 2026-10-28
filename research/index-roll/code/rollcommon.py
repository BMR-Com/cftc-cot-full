"""Index-roll spread backtest: Rogers (RICI) roll then GSCI roll, ICE softs.
Spread = nearby - deferred (price units). 'Sell spread' = short nearby / long deferred.
"""
import sys, os, json, numpy as np, pandas as pd
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MC = dict(F=1, G=2, H=3, J=4, K=5, M=6, N=7, Q=8, U=9, V=10, X=11, Z=12)
CYCLE = {'CT': 'HKNZ', 'SB': 'HKNV', 'KC': 'HKNUZ', 'CC': 'HKNUZ'}
MULT = {'CT': 500, 'SB': 1120, 'KC': 375, 'CC': 10}   # $ per 1.00 price unit per lot
UNIT = {'CT': '¢/lb', 'SB': '¢/lb', 'KC': '¢/lb', 'CC': '$/t'}

def load_tv(path=DATA+'/tv_contracts.csv.gz'):
    k = pd.read_csv(path); P = {}
    for sym, g in k.groupby('symbol'):
        P[(sym[:2], sym[2], int(sym[3:]))] = pd.Series(g.close.values, index=pd.to_datetime(g.date)).sort_index()
    return P


def chain(root, code, y, n=4):
    cyc = CYCLE[root]; i = cyc.index(code); out = []
    for j in range(n):
        out.append((root, cyc[(i + j) % len(cyc)], y + (i + j) // len(cyc)))
    return out



