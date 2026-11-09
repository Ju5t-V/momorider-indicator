"""Market Intraday Momentum (Baltussen, Da, Lammers & Martens 2021, JFE 142:377-403)
   r_LH (last 30min of the UTC day) regressed on r_ROD (prev close -> last 30min).
   Tested here on crypto perps, which the paper does NOT cover - 24h market, no close."""
import numpy as np, json, os, sys, datetime as dt
from scipy import stats
D=os.path.join("..","..","strategy","data")
SYMS=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT",
      "LINKUSDT","AVAXUSDT","ADAUSDT","LTCUSDT","SUIUSDT","APTUSDT"]
def load(s,tf="30"):
    k=json.load(open(os.path.join(D,f"{s}_{tf}.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    return a[:,0].astype(np.int64),a[:,1],a[:,2],a[:,3],a[:,4],a[:,5]

print("Market Intraday Momentum on crypto perps, UTC day boundary, 30m bars")
print("r_ROD = prev-day close -> 23:30 ;  r_LH = 23:30 -> 00:00\n")
print(f"{'symbol':10} {'days':>5} {'beta':>8} {'t':>7} {'R2%':>6} {'sign-match%':>11} {'meanR_LH|sig':>13}")
print("-"*68)
pool_x=[];pool_y=[]
for s in SYMS:
    t,o,h,l,c,v=load(s)
    day=np.array([dt.datetime.fromtimestamp(x/1000,dt.timezone.utc) for x in t])
    # last bar of each UTC day = the 23:30 bar
    key=np.array([d.strftime("%Y-%m-%d") for d in day])
    X=[];Y=[]
    uk=sorted(set(key))
    for i in range(1,len(uk)):
        m=np.where(key==uk[i])[0]
        mp=np.where(key==uk[i-1])[0]
        if len(m)<40 or len(mp)<40: continue
        prev_close=c[mp[-1]]
        pre_last=c[m[-2]]         # close of the 23:00 bar = price at 23:30
        last_close=c[m[-1]]       # close of the 23:30 bar = 00:00
        X.append(pre_last/prev_close-1.0)
        Y.append(last_close/pre_last-1.0)
    X=np.array(X);Y=np.array(Y)
    pool_x+=list(X);pool_y+=list(Y)
    sl,ic,r,p,se=stats.linregress(X,Y)
    tval=sl/se
    match=np.mean(np.sign(X)==np.sign(Y))*100
    sgn=np.sign(X); ret=sgn*Y
    print(f"{s:10} {len(X):5d} {sl:8.4f} {tval:7.2f} {100*r*r:6.2f} {match:10.1f}% {1e4*ret.mean():11.2f}bp")
X=np.array(pool_x);Y=np.array(pool_y)
sl,ic,r,p,se=stats.linregress(X,Y)
sgn=np.sign(X);ret=sgn*Y
print("-"*68)
print(f"{'POOLED':10} {len(X):5d} {sl:8.4f} {sl/se:7.2f} {100*r*r:6.2f} {100*np.mean(np.sign(X)==np.sign(Y)):10.1f}% {1e4*ret.mean():11.2f}bp")
print(f"\npooled trade stats: mean={1e4*ret.mean():.2f}bp  sd={1e4*ret.std():.1f}bp  t={ret.mean()/ret.std()*np.sqrt(len(ret)):.2f}")
print(f"annualised Sharpe if traded daily: {ret.mean()/ret.std()*np.sqrt(365):.2f}  (before costs)")
print(f"Binance taker round trip ~= 8bp; mean gross must exceed that.")
