"""Is the vol conditioning real or a lucky bucket? Checks:
   1. monotonicity across vol buckets
   2. agreement level x vol (2D)
   3. per-symbol consistency
   4. year by year"""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008; H=20
def load(s):
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k]); return a[:,0].astype(np.int64),a[:,4]
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
REC=[]
for s in SY:
    t,c=load(s); n=len(c)
    r=np.diff(np.log(c),prepend=np.log(c[0]))
    rv=np.full(n,np.nan)
    for i in range(30,n): rv[i]=r[i-30:i].std()
    rvp=np.full(n,np.nan)
    for i in range(280,n): rvp[i]=100.0*np.mean(rv[i-250:i]<=rv[i])
    M={}
    for LB in (14,28,56,90):
        m=np.full(n,np.nan); m[LB:]=c[LB:]/c[:-LB]-1.0; M[LB]=m
    for i in range(280,n-H,H):
        v=[M[LB][i] for LB in (14,28,56,90)]
        if any(np.isnan(x) for x in v) or np.isnan(rvp[i]): continue
        sg=[np.sign(x) for x in v]
        p=sum(1 for x in sg if x>0); mn=sum(1 for x in sg if x<0)
        agree=max(p,mn); sig=1 if p>mn else -1
        fwd=c[i+H]/c[i]-1.0
        REC.append(dict(sym=s,t=t[i],agree=agree,sig=sig,rvp=rvp[i],
                        pnl=sig*fwd-COST,hit=sig*fwd>0,
                        yr=dt.datetime.fromtimestamp(t[i]/1000,dt.timezone.utc).year))
print(f"{len(REC)} signal observations\n")
def sm(rows,lab):
    if len(rows)<40: print(f"  {lab:34} n={len(rows):5d}  (thin)"); return
    p=np.array([r["pnl"] for r in rows]); h=np.array([r["hit"] for r in rows])
    print(f"  {lab:34} n={len(rows):5d} hit={100*h.mean():5.1f}% mean={100*p.mean():+7.3f}% t={p.mean()/p.std(ddof=1)*np.sqrt(len(p)):+5.2f}")

print("1) VOL BUCKETS, unanimous (4/4) signals only - is it monotonic?")
U=[r for r in REC if r["agree"]==4]
for lo,hi in ((0,20),(20,40),(40,60),(60,75),(75,90),(90,101)):
    sm([r for r in U if lo<=r["rvp"]<hi], f"vol pct {lo}-{hi}")
print("\n2) AGREEMENT x VOL")
for a in (2,3,4):
    for lo,hi in ((0,60),(60,101)):
        sm([r for r in REC if r["agree"]==a and lo<=r["rvp"]<hi], f"agree={a}  vol {lo}-{hi}")
print("\n3) THE CANDIDATE (agree=4, vol>70) per year")
C=[r for r in REC if r["agree"]==4 and r["rvp"]>70]
for y in sorted(set(r["yr"] for r in C)): sm([r for r in C if r["yr"]==y], f"year {y}")
print("\n4) per symbol (candidate)")
bysym={}
for r in C: bysym.setdefault(r["sym"],[]).append(r)
pos=0;tot=0
for s in sorted(bysym):
    rows=bysym[s]
    if len(rows)<6: continue
    p=np.array([x["pnl"] for x in rows]); tot+=1
    if p.mean()>0: pos+=1
print(f"   symbols with >=6 signals: {tot}, of which positive mean: {pos} ({100*pos/max(1,tot):.0f}%)")
print("\n5) MIRROR CHECK - agree=4 and vol<=40 (should be the reversal side)")
sm([r for r in REC if r["agree"]==4 and r["rvp"]<=40], "agree=4, vol<=40")
sm([{**r,"pnl":-r["pnl"]-2*COST,"hit":not r["hit"]} for r in REC if r["agree"]==4 and r["rvp"]<=40], "  ...FADED instead")
