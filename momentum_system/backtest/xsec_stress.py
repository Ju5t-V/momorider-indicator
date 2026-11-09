"""Attack the cross-sectional result. Three things could be faking it:
   1. costs too optimistic for small alts
   2. perp FUNDING not charged (you pay it every 8h)
   3. survivorship - only coins still listed on Bybit today are in the file set"""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
SPLIT=dt.date(2024,1,1)
raw={}
for s in SY:
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    d=[dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).date() for x in a[:,0]]
    raw[s]=(d,a[:,4],a[:,5])
alldays=sorted(set().union(*[set(v[0]) for v in raw.values()]))
idx={d:i for i,d in enumerate(alldays)}; N=len(alldays)
CL={};VO={}
for s in SY:
    c=np.full(N,np.nan); v=np.full(N,np.nan)
    for dd,px,vv in zip(*raw[s]): c[idx[dd]]=px; v[idx[dd]]=vv
    CL[s]=c; VO[s]=v
# daily funding per symbol (sum of 8h prints) - a LONG pays positive funding
FU={}
for s in SY:
    f=np.zeros(N); p=os.path.join(D,f"{s}_FUND.json")
    if os.path.exists(p):
        fr=json.load(open(p))
        for x in fr:
            ts=int(x["fundingRateTimestamp"])
            dd=dt.datetime.fromtimestamp(ts/1000,dt.timezone.utc).date()
            if dd in idx: f[idx[dd]]+=float(x["fundingRate"])
    FU[s]=f
RV={};MOM={}
for s in SY:
    c=CL[s]; vv=~np.isnan(c)
    lg=np.full(N,np.nan); lg[vv]=np.log(c[vv])
    r=np.full(N,np.nan); r[1:]=lg[1:]-lg[:-1]
    rv=np.full(N,np.nan)
    for i in range(30,N):
        w=r[i-30:i]; w=w[~np.isnan(w)]
        if len(w)>20: rv[i]=w.std()
    RV[s]=rv
    mm={}
    for LB in (14,28):
        m=np.full(N,np.nan)
        for i in range(LB,N):
            if not np.isnan(c[i]) and not np.isnan(c[i-LB]) and c[i-LB]>0: m[i]=c[i]/c[i-LB]-1.0
        mm[LB]=m
    MOM[s]=mm

def sim(LB=14,hold=5,frac=0.25,cost=0.0008,use_funding=False,universe=None,minhist=300):
    U=universe if universe else SY
    Wp={s:0.0 for s in U}; rets=np.zeros(N); tgt={s:0.0 for s in U}; age=10**9
    for i in range(300,N):
        if age>=hold:
            cand=[(s,MOM[s][LB][i]) for s in U
                  if not np.isnan(MOM[s][LB][i]) and not np.isnan(RV[s][i]) and RV[s][i]>0 and not np.isnan(CL[s][i])]
            if len(cand)>=10:
                cand.sort(key=lambda z:z[1]); k=max(2,int(len(cand)*frac))
                sh=[c[0] for c in cand[:k]]; lo=[c[0] for c in cand[-k:]]
                tgt={s:0.0 for s in U}
                for s in lo: tgt[s]= 1.0/RV[s][i]
                for s in sh: tgt[s]=-1.0/RV[s][i]
                gl=sum(abs(tgt[s]) for s in lo); gs=sum(abs(tgt[s]) for s in sh)
                for s in lo: tgt[s]= 0.5*tgt[s]/gl if gl>0 else 0
                for s in sh: tgt[s]= 0.5*tgt[s]/gs if gs>0 else 0
                age=0
        age+=1
        pr=0.0
        for s in U:
            w=tgt[s]
            if w!=0 and not np.isnan(CL[s][i]) and not np.isnan(CL[s][i-1]):
                pr+=w*(CL[s][i]/CL[s][i-1]-1.0)
                if use_funding: pr-= w*FU[s][i]     # long pays positive funding
        tu=sum(abs(tgt[s]-Wp[s]) for s in U)
        rets[i]=pr-tu*cost/2.0
        Wp=dict(tgt)
    d=np.array(alldays); out={}
    for nm,msk in (("TRAIN",np.array([x<SPLIT for x in d])),("TEST",np.array([x>=SPLIT for x in d]))):
        x=rets[msk]; x=x[np.isfinite(x)]
        if len(x)<150: continue
        ann=x.mean()*365; vol=x.std()*np.sqrt(365)
        eq=np.cumprod(1+x); dd=(1-eq/np.maximum.accumulate(eq)).max()
        out[nm]=(100*ann,ann/vol if vol>0 else 0,100*dd)
    return out,rets,np.array(alldays)

def line(lab,o):
    a=o.get("TRAIN"); b=o.get("TEST")
    fa=f"{a[0]:8.1f}{a[1]:7.2f}{a[2]:7.1f}" if a else " "*22
    fb=f"{b[0]:8.1f}{b[1]:7.2f}{b[2]:7.1f}" if b else " "*22
    print(f"{lab:34} |{fa} |{fb}")

print("BASE = LB14 hold5 q25 vol-scaled dollar-neutral")
print(f"{'stress':34} | {'TRAIN annR/SR/DD':^22} | {'TEST annR/SR/DD':^22}")
print("-"*84)
print("--- 1. transaction cost ---")
for c in (0.0008,0.0015,0.0025,0.0040,0.0060):
    o,_,_=sim(cost=c); line(f"cost {c*1e4:.0f} bp round trip",o)
print("--- 2. + real perp funding charged ---")
for c in (0.0008,0.0025):
    o,_,_=sim(cost=c,use_funding=True); line(f"cost {c*1e4:.0f}bp + funding",o)
print("--- 3. survivorship: restrict to coins listed before 2022 (older, more liquid) ---")
old=[s for s in SY if not np.isnan(CL[s][idx[alldays[0]]]) or True]
early=[]
for s in SY:
    first=np.argmax(~np.isnan(CL[s]))
    if alldays[first] < dt.date(2022,1,1): early.append(s)
print(f"    ({len(early)} of {len(SY)} symbols listed pre-2022)")
o,_,_=sim(universe=early); line("pre-2022 universe only",o)
o,_,_=sim(universe=early,cost=0.0025,use_funding=True); line("pre-2022 + 25bp + funding",o)
print("--- 4. drop the 8 newest listings (they never had a pre-listing price) ---")
firsts=sorted(SY,key=lambda s: np.argmax(~np.isnan(CL[s])))
o,_,_=sim(universe=firsts[:-8]); line("drop 8 newest",o)
print("--- 5. BTC/ETH excluded (pure alt cross-section) ---")
o,_,_=sim(universe=[s for s in SY if s not in ("BTCUSDT","ETHUSDT")]); line("no BTC/ETH",o)
print("--- 6. year by year, base with 25bp + funding ---")
o,r,dd=sim(cost=0.0025,use_funding=True)
for y in range(2021,2027):
    m=np.array([x.year==y for x in dd]); x=r[m]; x=x[np.isfinite(x)]
    if len(x)<150: continue
    ann=x.mean()*365; vol=x.std()*np.sqrt(365)
    print(f"    {y}  annRet={100*ann:7.1f}%  SR={ann/vol if vol>0 else 0:5.2f}")
