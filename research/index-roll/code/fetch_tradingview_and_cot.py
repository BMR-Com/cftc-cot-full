"""Refresh data/: run on a GitHub Actions runner (TradingView and CFTC are not reachable from Claude sessions).
Requires: pip install pandas requests websocket-client git+https://github.com/rongardF/tvdatafeed.git
Outputs tv_contracts.csv.gz, cot_legacy.csv.gz, cot_disagg.csv.gz in the working dir; move them into ../data/."""
import time, pandas as pd, requests
from tvDatafeed import TvDatafeed, Interval
tv=TvDatafeed(); out=[]; miss=[]
for root,months in [('CT','HKNZ'),('SB','HKNV'),('KC','HKNUZ'),('CC','HKNUZ')]:
    for y in range(2000,2028):
        for m in months:
            sym=f'{root}{m}{y}'; d=None
            for a in range(3):
                try:
                    d=tv.get_hist(symbol=sym,exchange='ICEUS',interval=Interval.in_daily,n_bars=1200)
                    if d is not None and len(d): break
                except Exception as e: print('err',sym,e)
                time.sleep(2)
            if d is None or not len(d): miss.append(sym); print('MISSING',sym); continue
            d=d.reset_index(); d['date']=d['datetime'].dt.date; d['symbol']=sym
            out.append(d[['symbol','date','close','volume']]); print(sym,len(d),d.date.min(),d.date.max(),flush=True)
pd.concat(out).to_csv('tv_contracts.csv.gz',index=False); print('missing:',miss)
# CFTC COT via Socrata: legacy F&O combined (1986+) and disaggregated F&O combined (2006+)
codes={'033661':'CT','083731':'KC','080732':'SB','073732':'CC'}
for name,ds in [('legacy','jun7-fc8e'),('disagg','kh3c-gbw2')]:
    rows=[]
    for code in codes:
        r=requests.get(f'https://publicreporting.cftc.gov/resource/{ds}.json',params={'cftc_contract_market_code':code,'$limit':50000},timeout=120)
        j=r.json(); print(name,code,len(j)); rows+=j
    pd.DataFrame(rows).to_csv(f'cot_{name}.csv.gz',index=False)
