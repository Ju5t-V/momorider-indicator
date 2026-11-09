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
alldays=sorted(set().union(*[set(v[0]) for v in raw.values()]))
idx={d:i for i,d in enumerate(alldays)}; N=len(alldays)
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
    mm={}
    for LB in (7,14,21,28,56,90):
        m=np.full(N,np.nan)
        for i in range(LB,N):
            if not np.isnan(c[i]) and not np.isnan(c[i-LB]) and c[i-LB]>0: m[i]=c[i]/c[i-LB]-1.0
        mm[LB]=m
    MOM[s]=mm
d=np.array(alldays); mte=np.array([x>=SPLIT for x in d])
def sim(LB,hold,frac,cost=0.0025,rng=None):
    Wp={s:0.0 for s in SY}; rets=np.zeros(N); tgt={s:0.0 for s in SY}; age=10**9
    for i in range(300,N):
        if age>=hold:
            cand=[(s,MOM[s][LB][i]) for s in SY if not np.isnan(MOM[s][LB][i]) and not np.isnan(RV[s][i]) and RV[s][i]>0]
            if len(cand)>=10:
                if rng is not None:
                    vals=[c[1] for c in cand]; rng.shuffle(vals)
                    cand=[(cand[j][0],vals[j]) for j in range(len(cand))]
                cand.sort(key=lambda z:z[1]); k=max(2,int(len(cand)*frac))
                sh=[c[0] for c in cand[:k]]; lo=[c[0] for c in cand[-k:]]
                tgt={s:0.0 for s in SY}
                for s in lo: tgt[s]= 1.0/RV[s][i]
                for s in sh: tgt[s]=-1.0/RV[s][i]
                gl=sum(abs(tgt[s]) for s in lo); gs=sum(abs(tgt[s]) for s in sh)
                for s in lo: tgt[s]=0.5*tgt[s]/gl if gl>0 else 0
                for s in sh: tgt[s]=0.5*tgt[s]/gs if gs>0 else 0
                age=0
        age+=1
        pr=0.0
        for s in SY:
            w=tgt[s]
            if w!=0 and not np.isnan(CL[s][i]) and not np.isnan(CL[s][i-1]): pr+=w*(CL[s][i]/CL[s][i-1]-1.0)
        tu=sum(abs(tgt[s]-Wp[s]) for s in SY); rets[i]=pr-tu*cost/2.0; Wp=dict(tgt)
    return rets
def annsr(r):
    x=r[mte]; x=x[np.isfinite(x)]
    return x.mean()/x.std(ddof=1)*np.sqrt(365) if x.std()>0 else 0.0

print("A) DISTRIBUTION OF TEST SHARPE ACROSS THE WHOLE GRID")
print("   (if selection bias were the story, most configs would fail out-of-sample)")
srs=[]
for LB in (7,14,21,28,56,90):
    for hold in (5,10,20):
        for frac in (0.15,0.25,0.33):
            srs.append((annsr(sim(LB,hold,frac)),LB,hold,frac))
srs.sort(reverse=True)
arr=np.array([x[0] for x in srs])
print(f"   n configs={len(arr)}  median={np.median(arr):.2f}  mean={arr.mean():.2f}")
print(f"   fraction with test SR>1.0: {100*np.mean(arr>1.0):.0f}%   >1.5: {100*np.mean(arr>1.5):.0f}%   >0: {100*np.mean(arr>0):.0f}%")
print(f"   best  {srs[0][0]:.2f} (LB={srs[0][1]} hold={srs[0][2]} q={srs[0][3]})")
print(f"   worst {srs[-1][0]:.2f} (LB={srs[-1][1]} hold={srs[-1][2]} q={srs[-1][3]})")

print("\nB) PERMUTATION TEST - shuffle the momentum ranks, keep everything else identical")
print("   tests directly whether the RANKING carries information (no trial-count issue)")
real=annsr(sim(14,5,0.25))
rng=np.random.default_rng(12345)
null=[]
for k in range(60):
    null.append(annsr(sim(14,5,0.25,rng=rng)))
null=np.array(null)
p=(np.sum(null>=real)+1)/(len(null)+1)
print(f"   real test SR = {real:.2f}")
print(f"   shuffled: mean={null.mean():+.2f}  sd={null.std():.2f}  max={null.max():+.2f}  (n={len(null)})")
print(f"   permutation p-value = {p:.4f}")
