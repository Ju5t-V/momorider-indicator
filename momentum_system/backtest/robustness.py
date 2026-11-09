import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008
def load(s):
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k]); return a[:,0].astype(np.int64),a[:,4]
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
CACHE={s:load(s) for s in SY}
SPLIT=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
def sig(hold=20,hi=60,lo=40,lbs=(14,28,56,90)):
    out=[]
    for s in SY:
        t,c=CACHE[s]; n=len(c)
        r=np.diff(np.log(c),prepend=np.log(c[0]))
        rv=np.full(n,np.nan)
        for i in range(30,n): rv[i]=r[i-30:i].std()
        rvp=np.full(n,np.nan)
        for i in range(280,n): rvp[i]=100.0*np.mean(rv[i-250:i]<=rv[i])
        M={LB:np.concatenate([np.full(LB,np.nan),c[LB:]/c[:-LB]-1.0]) for LB in lbs}
        for i in range(280,n-hold,hold):
            v=[M[LB][i] for LB in lbs]
            if any(np.isnan(x) for x in v) or np.isnan(rvp[i]): continue
            sg=[np.sign(x) for x in v]
            if not(all(x>0 for x in sg) or all(x<0 for x in sg)): continue
            tr=1 if sg[0]>0 else -1
            if rvp[i]>hi: side,mode=tr,"MOM"
            elif rvp[i]<lo: side,mode=-tr,"REV"
            else: continue
            f=c[i+hold]/c[i]-1.0
            out.append(dict(sym=s,t=t[i],side=side,mode=mode,pnl=side*f-COST,hit=side*f>0,
                            yr=dt.datetime.fromtimestamp(t[i]/1000,dt.timezone.utc).year))
    return out
S=sig()
def rep(rows,lab):
    if len(rows)<25: print(f"  {lab:22} n={len(rows):5d} (thin)"); return
    p=np.array([r["pnl"] for r in rows]); h=np.array([r["hit"] for r in rows])
    print(f"  {lab:22} n={len(p):5d} hit={100*h.mean():5.1f}% mean={100*p.mean():+7.3f}% t={p.mean()/p.std(ddof=1)*np.sqrt(len(p)):+5.2f}")
print("YEAR BY YEAR (whole sample)")
for y in sorted(set(r["yr"] for r in S)): rep([r for r in S if r["yr"]==y], f"{y}")
print("\nPER-SYMBOL on TEST period only")
te=[r for r in S if r["t"]>=SPLIT]
by={}
for r in te: by.setdefault(r["sym"],[]).append(r)
pos=tot=0; rows=[]
for s in sorted(by):
    rr=by[s]
    if len(rr)<8: continue
    p=np.array([x["pnl"] for x in rr]); h=np.array([x["hit"] for x in rr]); tot+=1
    if p.mean()>0: pos+=1
    rows.append((s,len(p),100*h.mean(),100*p.mean()))
for s,n,h,m in sorted(rows,key=lambda z:-z[3])[:8]: print(f"    {s:10} n={n:3d} hit={h:5.1f}% mean={m:+7.2f}%")
print(f"    ... {pos}/{tot} symbols positive ({100*pos/max(1,tot):.0f}%)")
print("\nHOLD-PERIOD SENSITIVITY (test period)")
for hold in (10,15,20,30,40):
    s2=[r for r in sig(hold=hold) if r["t"]>=SPLIT]
    if len(s2)<30: continue
    p=np.array([r["pnl"] for r in s2]); h=np.array([r["hit"] for r in s2])
    print(f"  hold={hold:3d}d  n={len(p):5d} hit={100*h.mean():5.1f}% mean={100*p.mean():+7.3f}% t={p.mean()/p.std(ddof=1)*np.sqrt(len(p)):+5.2f}")
print("\nLOOKBACK-SET SENSITIVITY (test period)")
for lbs in ((14,28,56,90),(14,28,56),(28,56,90),(7,14,28,56),(10,20,40,80),(21,42,84)):
    s2=[r for r in sig(lbs=lbs) if r["t"]>=SPLIT]
    if len(s2)<30: continue
    p=np.array([r["pnl"] for r in s2]); h=np.array([r["hit"] for r in s2])
    print(f"  {str(lbs):18} n={len(p):5d} hit={100*h.mean():5.1f}% mean={100*p.mean():+7.3f}% t={p.mean()/p.std(ddof=1)*np.sqrt(len(p)):+5.2f}")
