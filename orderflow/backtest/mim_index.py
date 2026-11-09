"""Baltussen, Da, Lammers & Martens (2021, JFE 142:377-403) replication on MT5 index CFDs.
   r_LH  = return over the last 30 min before the CASH close
   r_ROD = return from previous cash close to the start of that last 30 min
   Server time = ET + 7 (verified from the volume profile: US cash open 09:30 ET = 16:30 server)."""
import numpy as np, datetime as dt, os
from scipy import stats

CLOSE={"US500":(23,0),"US30":(23,0),"DAX":(18,30),"FRA40":(18,30),"ESP35":(18,30),
       "UK100":(18,30),"AUS200":(9,0)}
def load(s):
    r=np.load(os.path.join("..","data",f"mt5_{s}_M30.npy"))
    t=np.array([dt.datetime.fromtimestamp(x,dt.timezone.utc) for x in r['time']])
    return t, r['open'].astype(float), r['close'].astype(float), r['high'].astype(float), r['low'].astype(float)

def mim(sym):
    ch,cm=CLOSE[sym]
    t,o,c,h,l=load(sym)
    hm=np.array([x.hour*60+x.minute for x in t])
    close_min=ch*60+cm
    last_start=close_min-30                       # bar that COVERS the final 30 min
    days=np.array([x.date() for x in t])
    X=[];Y=[];D=[]
    prev_close=None
    for d in sorted(set(days)):
        m=np.where(days==d)[0]
        i_last=[i for i in m if hm[i]==last_start]
        if not i_last: continue
        i=i_last[0]
        if prev_close is not None:
            X.append(o[i]/prev_close-1.0)         # prev cash close -> start of last 30min
            Y.append(c[i]/o[i]-1.0)               # the last 30 min itself
            D.append(d)
        prev_close=c[i]
    return np.array(X),np.array(Y),D

print("MARKET INTRADAY MOMENTUM - replication on MT5 index CFDs, 2015-2026")
print("H0: last-30min return is unpredictable.  Paper: beta>0, t>3 on equity futures.\n")
print(f"{'symbol':8} {'days':>5} {'beta':>8} {'t':>7} {'R2%':>6} {'hit%':>6} {'mean bp':>8} {'SR/yr':>7}")
print("-"*60)
res={}
for s in ("US500","US30","DAX","FRA40","ESP35","AUS200"):
    try: X,Y,D=mim(s)
    except Exception as e: print(f"{s:8} err {e}"); continue
    if len(X)<200: print(f"{s:8} only {len(X)} days"); continue
    sl,ic,r,p,se=stats.linregress(X,Y)
    ret=np.sign(X)*Y
    sr=ret.mean()/ret.std()*np.sqrt(252)
    print(f"{s:8} {len(X):5d} {sl:8.4f} {sl/se:7.2f} {100*r*r:6.2f} {100*np.mean(np.sign(X)==np.sign(Y)):5.1f}% {1e4*ret.mean():8.2f} {sr:7.2f}")
    res[s]=(X,Y,ret)
# pooled US
if "US500" in res and "US30" in res:
    X=np.concatenate([res[s][0] for s in ("US500","US30")]); Y=np.concatenate([res[s][1] for s in ("US500","US30")])
    sl,ic,r,p,se=stats.linregress(X,Y); ret=np.sign(X)*Y
    print("-"*60)
    print(f"{'US pool':8} {len(X):5d} {sl:8.4f} {sl/se:7.2f} {100*r*r:6.2f} {100*np.mean(np.sign(X)==np.sign(Y)):5.1f}% {1e4*ret.mean():8.2f} {ret.mean()/ret.std()*np.sqrt(252):7.2f}")
