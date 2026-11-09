import numpy as np, json, os, glob, datetime as dt
from scipy.stats import norm, skew, kurtosis
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
def sim(LB=14,hold=5,frac=0.25,cost=0.0025):
    Wp={s:0.0 for s in SY}; rets=np.zeros(N); tgt={s:0.0 for s in SY}; age=10**9
    for i in range(300,N):
        if age>=hold:
            cand=[(s,MOM[s][LB][i]) for s in SY if not np.isnan(MOM[s][LB][i]) and not np.isnan(RV[s][i]) and RV[s][i]>0]
            if len(cand)>=10:
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
d=np.array(alldays); mte=np.array([x>=SPLIT for x in d]); mtr=np.array([x<SPLIT for x in d])
trials=[]
for LB in (7,14,21,28,56,90):
    for hold in (5,10,20):
        for frac in (0.15,0.25,0.33):
            r=sim(LB,hold,frac); x=r[mtr]; x=x[np.isfinite(x)]
            if len(x)>200 and x.std()>0: trials.append(x.mean()/x.std())
base=sim(14,5,0.25); xt=base[mte]; xt=xt[np.isfinite(xt)]
sr=xt.mean()/xt.std(ddof=1); T=len(xt)
N_TRIALS=100
V=np.var(trials,ddof=1); g=0.5772156649
sr0=np.sqrt(V)*((1-g)*norm.ppf(1-1.0/N_TRIALS)+g*norm.ppf(1-1.0/(N_TRIALS*np.e)))
g3=skew(xt); g4=kurtosis(xt,fisher=False)
den=np.sqrt(max(1e-12,1-g3*sr+(g4-1)/4.0*sr**2))
z=(sr-sr0)*np.sqrt(T-1)/den
print("DEFLATED SHARPE - cross-sectional momentum, TEST period, cost 25bp")
print(f"  configurations actually tried (train only): {len(trials)}; honest session trial count N={N_TRIALS}")
print(f"  spread of trial daily-Sharpes sd={np.sqrt(V):.4f}")
print(f"  daily SR(test)={sr:.4f} (annualised {sr*np.sqrt(365):.2f})   SR0(luck)={sr0:.4f}")
print(f"  DSR = {norm.cdf(z):.4f}")
print(f"\n  test days={T}  skew={g3:+.2f}  kurtosis={g4:.1f}")
# monthly consistency
import collections
mm=collections.defaultdict(list)
for i,dd in enumerate(alldays):
    if dd>=SPLIT and np.isfinite(base[i]): mm[(dd.year,dd.month)].append(base[i])
months=[(k,np.prod([1+x for x in v])-1) for k,v in sorted(mm.items()) if len(v)>15]
pos=sum(1 for _,r in months if r>0)
print(f"  monthly consistency on test: {pos}/{len(months)} months positive ({100*pos/len(months):.0f}%)")
print(f"  best month {100*max(r for _,r in months):+.1f}%   worst month {100*min(r for _,r in months):+.1f}%")
