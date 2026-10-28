import sys, time, pandas as pd, requests
root=sys.argv[1]
CFG={'ZC':('CBOT','HKNUZ'),'ZS':('CBOT','FHKNX'),'ZM':('CBOT','FHKNZ'),'ZL':('CBOT','FHKNZ'),'ZW':('CBOT','HKNUZ'),'KE':('CBOT','HKNUZ'),'LE':('CME','GJMQVZ'),'HE':('CME','GJMNQVZ')}
if root=='COT':
    codes=['002602','005602','026603','007601','001602','001612','057642','054642']
    for name,ds in [('legacy','jun7-fc8e'),('disagg','kh3c-gbw2')]:
        rows=[]
        for c in codes:
            j=requests.get(f'https://publicreporting.cftc.gov/resource/{ds}.json',params={'cftc_contract_market_code':c,'$limit':50000},timeout=180).json(); print(name,c,len(j)); rows+=j
        pd.DataFrame(rows).to_csv(f'ags_cot_{name}.csv.gz',index=False)
    sys.exit()
from tvDatafeed import TvDatafeed, Interval
tv=TvDatafeed(); ex,months=CFG[root]; out=[]; miss=[]
for y in range(2000,2028):
    for m in months:
        sym=f'{root}{m}{y}'; d=None
        for a in range(3):
            try:
                d=tv.get_hist(symbol=sym,exchange=ex,interval=Interval.in_daily,n_bars=1200)
                if d is not None and len(d): break
            except Exception as e: print('err',sym,e)
            time.sleep(2)
        if d is None or not len(d): miss.append(sym); continue
        d=d.reset_index(); d['date']=d['datetime'].dt.date; d['symbol']=sym
        out.append(d[['symbol','date','close','volume']]); print(sym,len(d),flush=True)
pd.concat(out).to_csv(f'ags_{root}.csv.gz',index=False); print('missing',miss)
