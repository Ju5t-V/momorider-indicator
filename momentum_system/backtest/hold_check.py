"""Is hold=20 special, or an artifact of non-overlapping sampling?
   Re-test using EVERY day as a potential entry (overlapping), so all holds see the
   same entry dates. Overlapping horizons autocorrelate, so t-stats use Newey-West."""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008
def load(s):
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k]); return a[:,0].astype(np.int64),a[:,4]
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
CACHE={s:load(s) for s in SY}
SPLIT=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)

def nw_t(x,lag):
    x=np.asarray(x,float); n=len(x); mu=x.mean(); e=x-mu
    g0=(e@e)/n; s=g0
    for k in range(1,lag+1):
        w=1.0-k/(lag+1.0); gk=(e[k:]@e[:-k])/n
        s+=2*w*gk
    se=np.sqrt(max(s,1e-18)/n)
    return mu/se

PRE={}
for s in SY:
    t,c=CACHE[s]; n=len(c)
    r=np.diff(np.log(c),prepend=np.log(c[0]))
    rv=np.full(n,np.nan)
    for i in range(30,n): rv[i]=r[i-30:i].std()
    rvp=np.full(n,np.nan)
    for i in range(280,n): rvp[i]=100.0*np.mean(rv[i-250:i]<=rv[i])
    M={LB:np.concatenate([np.full(LB,np.nan),c[LB:]/c[:-LB]-1.0]) for LB in (14,28,56,90)}
    PRE[s]=(t,c,rvp,M,n)

print("OVERLAPPING entries (every day), same entry dates for every hold.")
print("Newey-West t with lag = hold.  TEST period 2024-2026.\n")
print(f"{'hold':>5} {'n':>6} {'hit%':>7} {'mean%':>8} {'NW t':>7} {'ann.SR*':>8}")
for hold in (5,10,15,20,25,30,40,60):
    P=[];Hh=[]
    for s in SY:
        t,c,rvp,M,n=PRE[s]
        for i in range(280,n-hold):
            if t[i]<SPLIT: continue
            v=[M[LB][i] for LB in (14,28,56,90)]
            if any(np.isnan(x) for x in v) or np.isnan(rvp[i]): continue
            sg=[np.sign(x) for x in v]
            if not(all(x>0 for x in sg) or all(x<0 for x in sg)): continue
            tr=1 if sg[0]>0 else -1
            if rvp[i]>60: side=tr
            elif rvp[i]<40: side=-tr
            else: continue
            f=c[i+hold]/c[i]-1.0
            P.append(side*f-COST); Hh.append(side*f>0)
    if len(P)<200: continue
    P=np.array(P);Hh=np.array(Hh)
    tt=nw_t(P,hold)
    sr=P.mean()/P.std(ddof=1)*np.sqrt(365.0/hold)
    print(f"{hold:5d} {len(P):6d} {100*Hh.mean():7.1f} {100*P.mean():8.3f} {tt:7.2f} {sr:8.2f}")
print("\n* SR here assumes non-overlapping deployment at that hold; it is an upper guide.")
print("\nSame, TRAIN period 2020-2023:")
print(f"{'hold':>5} {'n':>6} {'hit%':>7} {'mean%':>8} {'NW t':>7}")
for hold in (5,10,15,20,25,30,40,60):
    P=[];Hh=[]
    for s in SY:
        t,c,rvp,M,n=PRE[s]
        for i in range(280,n-hold):
            if t[i]>=SPLIT: continue
            v=[M[LB][i] for LB in (14,28,56,90)]
            if any(np.isnan(x) for x in v) or np.isnan(rvp[i]): continue
            sg=[np.sign(x) for x in v]
            if not(all(x>0 for x in sg) or all(x<0 for x in sg)): continue
            tr=1 if sg[0]>0 else -1
            if rvp[i]>60: side=tr
            elif rvp[i]<40: side=-tr
            else: continue
            f=c[i+hold]/c[i]-1.0
            P.append(side*f-COST); Hh.append(side*f>0)
    if len(P)<200: continue
    P=np.array(P);Hh=np.array(Hh)
    print(f"{hold:5d} {len(P):6d} {100*Hh.mean():7.1f} {100*P.mean():8.3f} {nw_t(P,hold):7.2f}")
