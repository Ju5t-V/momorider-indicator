"""Cross-sectional (market-NEUTRAL) crypto momentum.
   Each day rank the universe by momentum; go long the top group, short the bottom,
   dollar-neutral. This removes the common crypto beta that made the directional
   version one big correlated bet."""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
SPLIT=dt.date(2024,1,1)
raw={}
for s in SY:
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    d=[dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).date() for x in a[:,0]]
    raw[s]=(d,a[:,4])
alldays=sorted(set().union(*[set(v[0]) for v in raw.values()]))
idx={d:i for i,d in enumerate(alldays)}; N=len(alldays)
CL={}
for s in SY:
    c=np.full(N,np.nan)
    for dd,px in zip(*raw[s]): c[idx[dd]]=px
    CL[s]=c
RV={}; MOM={}
for s in SY:
    c=CL[s]; v=~np.isnan(c)
    lg=np.full(N,np.nan); lg[v]=np.log(c[v])
    r=np.full(N,np.nan); r[1:]=lg[1:]-lg[:-1]
    rv=np.full(N,np.nan)
    for i in range(30,N):
        w=r[i-30:i]; w=w[~np.isnan(w)]
        if len(w)>20: rv[i]=w.std()
    RV[s]=rv
    mm={}
    for LB in (14,28,56,90):
        m=np.full(N,np.nan)
        for i in range(LB,N):
            if not np.isnan(c[i]) and not np.isnan(c[i-LB]) and c[i-LB]>0: m[i]=c[i]/c[i-LB]-1.0
        mm[LB]=m
    MOM[s]=mm

def sim(LB=28, frac=0.25, hold=5, volscale=True, lab=""):
    W_prev={s:0.0 for s in SY}
    rets=np.zeros(N); turn=np.zeros(N)
    target={s:0.0 for s in SY}; age=10**9
    for i in range(300,N):
        if age>=hold:
            cand=[(s,MOM[s][LB][i]) for s in SY
                  if not np.isnan(MOM[s][LB][i]) and not np.isnan(RV[s][i]) and RV[s][i]>0 and not np.isnan(CL[s][i])]
            if len(cand)>=10:
                cand.sort(key=lambda z:z[1])
                k=max(2,int(len(cand)*frac))
                shorts=[c[0] for c in cand[:k]]; longs=[c[0] for c in cand[-k:]]
                target={s:0.0 for s in SY}
                for s in longs:  target[s]= (1.0/RV[s][i]) if volscale else 1.0
                for s in shorts: target[s]=-((1.0/RV[s][i]) if volscale else 1.0)
                gl=sum(abs(target[s]) for s in longs);  gs=sum(abs(target[s]) for s in shorts)
                for s in longs:  target[s]= 0.5*target[s]/gl if gl>0 else 0
                for s in shorts: target[s]= 0.5*target[s]/gs if gs>0 else 0
                age=0
        age+=1
        pr=0.0
        for s in SY:
            w=target[s]
            if w!=0 and not np.isnan(CL[s][i]) and not np.isnan(CL[s][i-1]):
                pr+=w*(CL[s][i]/CL[s][i-1]-1.0)
        tu=sum(abs(target[s]-W_prev[s]) for s in SY)
        rets[i]=pr-tu*COST/2.0; turn[i]=tu
        W_prev=dict(target)
    d=np.array(alldays)
    out={}
    for nm,msk in (("TRAIN",np.array([x<SPLIT for x in d])),("TEST",np.array([x>=SPLIT for x in d]))):
        x=rets[msk]; x=x[np.isfinite(x)]
        x=x[x!=0] if False else x
        if len(x)<150: continue
        ann=x.mean()*365; vol=x.std()*np.sqrt(365)
        eq=np.cumprod(1+x); dd=(1-eq/np.maximum.accumulate(eq)).max()
        out[nm]=(100*ann,100*vol,ann/vol if vol>0 else 0,100*dd,100*turn[msk].mean())
    if lab:
        a=out.get("TRAIN"); b=out.get("TEST")
        fa=f"{a[0]:7.1f}{a[1]:7.1f}{a[2]:7.2f}{a[3]:7.1f}" if a else " "*28
        fb=f"{b[0]:7.1f}{b[1]:7.1f}{b[2]:7.2f}{b[3]:7.1f}" if b else " "*28
        print(f"{lab:26} |{fa} |{fb}")
    return out

print("CROSS-SECTIONAL, DOLLAR-NEUTRAL crypto momentum")
print(f"{'variant':26} | {'TRAIN 2020-2023':^28} | {'TEST 2024-2026':^28}")
print(f"{'':26} |{'annR%':>7}{'vol%':>7}{'SR':>7}{'DD%':>7} |{'annR%':>7}{'vol%':>7}{'SR':>7}{'DD%':>7}")
print("-"*88)
for LB in (14,28,56,90):
    for hold in (5,10,20):
        sim(LB=LB,hold=hold,lab=f"LB={LB:3d} hold={hold:2d} q25")
print()
for frac in (0.15,0.20,0.33):
    sim(LB=28,hold=10,frac=frac,lab=f"LB= 28 hold=10 q{int(frac*100)}")
sim(LB=28,hold=10,volscale=False,lab="LB= 28 hold=10 no-volscale")
