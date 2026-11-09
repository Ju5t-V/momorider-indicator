"""STRICT validation. Rule frozen from train logic only; test period never used to choose.
   RULE (two-sided):
     all four momentum lookbacks {14,28,56,90} must agree on sign  (unanimity)
     realised-vol percentile > HI  -> trade WITH the trend   (momentum regime)
     realised-vol percentile < LO  -> trade AGAINST it       (exhaustion regime)
     in between                    -> stand aside
"""
import numpy as np, json, os, glob, datetime as dt
from scipy import stats
from scipy.stats import norm, skew, kurtosis
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008; H=20; HI=60.0; LO=40.0
def load(s):
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k]); return a[:,0].astype(np.int64),a[:,4]
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
SPLIT=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)

def signals(hi=HI,lo=LO,lbs=(14,28,56,90),hold=H,volwin=30,pctwin=250):
    out=[]
    for s in SY:
        t,c=load(s); n=len(c)
        r=np.diff(np.log(c),prepend=np.log(c[0]))
        rv=np.full(n,np.nan)
        for i in range(volwin,n): rv[i]=r[i-volwin:i].std()
        rvp=np.full(n,np.nan)
        for i in range(volwin+pctwin,n): rvp[i]=100.0*np.mean(rv[i-pctwin:i]<=rv[i])
        M={}
        for LB in lbs:
            m=np.full(n,np.nan); m[LB:]=c[LB:]/c[:-LB]-1.0; M[LB]=m
        for i in range(volwin+pctwin,n-hold,hold):
            v=[M[LB][i] for LB in lbs]
            if any(np.isnan(x) for x in v) or np.isnan(rvp[i]): continue
            sg=[np.sign(x) for x in v]
            if not (all(x>0 for x in sg) or all(x<0 for x in sg)): continue
            trend=1 if sg[0]>0 else -1
            if   rvp[i]>hi: side= trend; mode="MOM"
            elif rvp[i]<lo: side=-trend; mode="REV"
            else: continue
            fwd=c[i+hold]/c[i]-1.0
            out.append(dict(sym=s,t=t[i],side=side,mode=mode,rvp=rvp[i],
                            pnl=side*fwd-COST,hit=side*fwd>0))
    return out
S=signals()
def rep(rows,lab):
    if len(rows)<30: print(f"{lab:36} n={len(rows):5d} (thin)"); return None
    p=np.array([r["pnl"] for r in rows]); h=np.array([r["hit"] for r in rows])
    tt=p.mean()/p.std(ddof=1)*np.sqrt(len(p))
    sr=p.mean()/p.std(ddof=1)*np.sqrt(365.0/H)
    eq=np.cumprod(1+p*0.02); dd=(1-eq/np.maximum.accumulate(eq)).max()
    print(f"{lab:36} n={len(p):5d} hit={100*h.mean():5.1f}% mean={100*p.mean():+7.3f}% t={tt:+5.2f} SR={sr:+5.2f} maxDD={100*dd:5.1f}%")
    return p
print(f"FROZEN RULE: unanimous {{14,28,56,90}}, vol pct >{HI:.0f} = momentum, <{LO:.0f} = fade, hold {H}d, cost 8bp\n")
tr=[r for r in S if r["t"]< SPLIT]; te=[r for r in S if r["t"]>=SPLIT]
print("--- TRAIN 2020-2023 ---")
rep(tr,"  all"); rep([r for r in tr if r["mode"]=="MOM"],"  momentum leg"); rep([r for r in tr if r["mode"]=="REV"],"  fade leg")
print("--- TEST 2024-2026 (untouched) ---")
pte=rep(te,"  all"); rep([r for r in te if r["mode"]=="MOM"],"  momentum leg"); rep([r for r in te if r["mode"]=="REV"],"  fade leg")

print("\n--- threshold robustness (is 60/40 special, or a plateau?) ---")
print(f"{'HI/LO':>10} {'n':>5} {'hit%':>7} {'mean%':>8} {'t':>6}   (TEST period only)")
for hi,lo in ((55,45),(60,40),(65,35),(70,30),(75,25),(60,30),(70,40)):
    s2=[r for r in signals(hi,lo) if r["t"]>=SPLIT]
    if len(s2)<30: continue
    p=np.array([r["pnl"] for r in s2]); h=np.array([r["hit"] for r in s2])
    print(f"{hi:4.0f}/{lo:<5.0f} {len(p):5d} {100*h.mean():7.1f} {100*p.mean():8.3f} {p.mean()/p.std(ddof=1)*np.sqrt(len(p)):6.2f}")

print("\n--- deflated Sharpe (Bailey & Lopez de Prado) on the TEST period ---")
trials=[]
for hi,lo in ((55,45),(60,40),(65,35),(70,30),(75,25),(60,30),(70,40)):
    s2=[r for r in signals(hi,lo) if r["t"]< SPLIT]
    if len(s2)<30: continue
    p=np.array([r["pnl"] for r in s2]); trials.append(p.mean()/p.std(ddof=1))
for lb in ((14,28),(14,28,56),(28,56,90),(7,14,28,56)):
    s2=[r for r in signals(lbs=lb) if r["t"]< SPLIT]
    if len(s2)<30: continue
    p=np.array([r["pnl"] for r in s2]); trials.append(p.mean()/p.std(ddof=1))
N=60   # honest count of everything tried across this whole session's momentum work
V=np.var(trials,ddof=1); g=0.5772156649
sr0=np.sqrt(V)*((1-g)*norm.ppf(1-1.0/N)+g*norm.ppf(1-1.0/(N*np.e)))
sr=pte.mean()/pte.std(ddof=1); T=len(pte)
g3=skew(pte); g4=kurtosis(pte,fisher=False)
den=np.sqrt(max(1e-12,1-g3*sr+(g4-1)/4.0*sr**2))
z=(sr-sr0)*np.sqrt(T-1)/den
print(f"  trials counted N={N}, spread of trial Sharpes sd={np.sqrt(V):.4f}")
print(f"  SR/trade(test)={sr:.4f}  vs SR0(luck)={sr0:.4f}  ->  DSR = {norm.cdf(z):.3f}")
