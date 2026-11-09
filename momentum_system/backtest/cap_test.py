import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
SPLIT=dt.date(2024,1,1)
raw={}
for s in SY:
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    d=[dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).date() for x in a[:,0]]
    raw[s]=(d,a[:,4])
alldays=sorted(set().union(*[set(v[0]) for v in raw.values()])); idx={d:i for i,d in enumerate(alldays)}; N=len(alldays)
CL={}
for s in SY:
    c=np.full(N,np.nan)
    for dd,px in zip(*raw[s]): c[idx[dd]]=px
    CL[s]=c
RV={};MOM={}
for s in SY:
    c=CL[s]; v=~np.isnan(c); lg=np.full(N,np.nan); lg[v]=np.log(c[v])
    r=np.full(N,np.nan); r[1:]=lg[1:]-lg[:-1]
    rv=np.full(N,np.nan)
    for i in range(30,N):
        w=r[i-30:i]; w=w[~np.isnan(w)]
        if len(w)>20: rv[i]=w.std()
    RV[s]=rv
    m=np.full(N,np.nan)
    for i in range(14,N):
        if not np.isnan(c[i]) and not np.isnan(c[i-14]) and c[i-14]>0: m[i]=c[i]/c[i-14]-1.0
    MOM[s]=m
d=np.array(alldays); mte=np.array([x>=SPLIT for x in d]); mtr=np.array([x<SPLIT for x in d])
def sim(cap=None,cost=0.0025,equal=False):
    Wp={s:0.0 for s in SY}; rets=np.zeros(N); tgt={s:0.0 for s in SY}; age=10**9
    for i in range(300,N):
        if age>=5:
            cand=[(s,MOM[s][i]) for s in SY if not np.isnan(MOM[s][i]) and not np.isnan(RV[s][i]) and RV[s][i]>0]
            if len(cand)>=10:
                cand.sort(key=lambda z:z[1]); k=max(2,int(len(cand)*0.25))
                sh=[c[0] for c in cand[:k]]; lo=[c[0] for c in cand[-k:]]
                tgt={s:0.0 for s in SY}
                for grp,sgn in ((lo,1.0),(sh,-1.0)):
                    w={s:(1.0 if equal else 1.0/RV[s][i]) for s in grp}
                    tot=sum(w.values())
                    w={s:0.5*x/tot for s,x in w.items()}
                    if cap:
                        for _ in range(20):
                            over={s:x for s,x in w.items() if x>cap}
                            if not over: break
                            ex=sum(x-cap for x in over.values())
                            for s in over: w[s]=cap
                            room={s:x for s,x in w.items() if x<cap}
                            tr=sum(room.values())
                            if tr<=0: break
                            for s in room: w[s]=min(cap,w[s]+ex*w[s]/tr)
                    for s,x in w.items(): tgt[s]=sgn*x
                age=0
        age+=1
        pr=0.0
        for s in SY:
            w=tgt[s]
            if w!=0 and not np.isnan(CL[s][i]) and not np.isnan(CL[s][i-1]): pr+=w*(CL[s][i]/CL[s][i-1]-1.0)
        tu=sum(abs(tgt[s]-Wp[s]) for s in SY); rets[i]=pr-tu*cost/2.0; Wp=dict(tgt)
    o={}
    for nm,msk in (("TRAIN",mtr),("TEST",mte)):
        x=rets[msk]; x=x[np.isfinite(x)]
        ann=x.mean()*365; vol=x.std()*np.sqrt(365)
        eq=np.cumprod(1+x); dd=(1-eq/np.maximum.accumulate(eq)).max()
        o[nm]=(100*ann,ann/vol if vol>0 else 0,100*dd)
    return o
print("Does capping single-name weight hurt? (LB14 hold5 q25, 25bp)")
print(f"{'sizing':28} | {'TRAIN annR/SR/DD':^22} | {'TEST annR/SR/DD':^22}")
print("-"*78)
for lab,kw in (("inverse-vol, no cap",dict()),
               ("inverse-vol, cap 15%",dict(cap=0.15)),
               ("inverse-vol, cap 10%",dict(cap=0.10)),
               ("inverse-vol, cap 8%",dict(cap=0.08)),
               ("equal weight (no vol scale)",dict(equal=True))):
    o=sim(**kw); a=o["TRAIN"]; b=o["TEST"]
    print(f"{lab:28} |{a[0]:8.1f}{a[1]:7.2f}{a[2]:7.1f} |{b[0]:8.1f}{b[1]:7.2f}{b[2]:7.1f}")
