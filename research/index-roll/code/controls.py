import warnings; warnings.filterwarnings('ignore')
import os, numpy as np, pandas as pd
import rollcommon as bt
import build_events as v2  # rebuilds events; provides P, SPEC, spec_at
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "results")
P=v2.P; rows=[]
for root in [r for r in bt.MARKETS]:
    keys=[k for k in P if k[0]==root]; cal=pd.DatetimeIndex(sorted(set().union(*[set(P[k].index) for k in keys])))
    for (_,code,y) in keys:
        if y<2000 or code not in bt.CYCLE[root]: continue
        M=bt.MC[code]; m1=pd.Timestamp(y,M,1)-pd.offsets.MonthBegin(1); m2=m1-pd.offsets.MonthBegin(1)
        d2=cal[(cal.year==m2.year)&(cal.month==m2.month)]
        if len(d2)<5 or m1>pd.Timestamp.today(): continue
        legs=bt.chain(root,code,y,2)
        if any(l not in P for l in legs): continue
        x=(P[legs[0]]-P[legs[1]]).reindex(cal).ffill(limit=2); i=cal.get_loc(d2[-3])
        if i<81: continue
        sd=x.loc[cal[i]-pd.Timedelta(days=400):cal[i]].diff().std()
        lvl=x.iloc[i-20]; fr=P[legs[0]].reindex(cal).ffill().iloc[i-20]
        for lag,lab in [(0,'pre20 (roll)'),(20,'ctl -40/-20'),(40,'ctl -60/-40'),(60,'ctl -80/-60')]:
            a,b=cal[i-20-lag],cal[i-lag]
            pct=v2.spec_at(root,'nc',a)[1]
            v=-(x.loc[b]-x.loc[a])/sd
            if pd.notna(v) and pd.notna(pct): rows.append(dict(root=root,year=y,date=b,win=lab,pct=pct,z=v,inv=lvl/fr*100))
D=pd.DataFrame(rows)
def st(v): v=v.dropna(); return f"{v.mean():+.2f} ({(v>0).mean():.0%}, t{v.mean()/(v.std()/np.sqrt(len(v))):+.1f}, n{len(v)})" if len(v)>4 else f"n{len(v)}"
B=[('>=90',D.pct>=90),('>=80',D.pct>=80),('20-80',(D.pct>20)&(D.pct<80)),('<=20',D.pct<=20)]
print('spread1 weakening (z), by window and spec bucket (nc pct at window start)')
print(pd.DataFrame({bn:D[m].groupby('win').z.apply(st) for bn,m in B}).to_string())
R=D[D.win=='pre20 (roll)']; R['era']=np.where(R.year<=2013,'2000-13','2014-26')
print('\nroll window by era:'); print(pd.DataFrame({bn:R[m.loc[R.index]].groupby('era').z.apply(st) for bn,m in B}).to_string())
# date-clustered: average across markets rolling in same month
R['ym']=R.date.dt.to_period('M')
for bn,m in B[:2]:
    c=R[m.loc[R.index]].groupby('ym').z.mean(); print(bn,'clustered by roll month:',st(c))
# is it just inversion? split >=80 by spread level (front premium % of price)
H=R[R.pct>=80]; print('\n>=80 split by curve shape at window start (front-2nd as % of front):')
print(H.groupby(pd.cut(H.inv,[-99,-2,0,2,99])).z.apply(st).to_string())
M_=R[(R.pct>20)&(R.pct<80)]; print('mid-bucket split by curve shape:'); print(M_.groupby(pd.cut(M_.inv,[-99,-2,0,2,99])).z.apply(st).to_string())
D.to_csv(os.path.join(RES,'v2_ctl.csv'),index=False)
