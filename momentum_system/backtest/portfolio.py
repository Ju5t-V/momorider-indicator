"""Portfolio simulation - how you would ACTUALLY trade this.
   Each day: every symbol gets a target position from the rule (+1/-1/0), sized
   inversely to its own volatility. Equal risk budget, daily rebalance, costs on turnover."""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
SPLIT=dt.date(2024,1,1)

# align everything on a common daily calendar
raw={}
for s in SY:
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    d=[dt.datetime.fromtimestamp(x/1000,dt.timezone.utc).date() for x in a[:,0]]
    raw[s]=(d,a[:,4])
alldays=sorted(set().union(*[set(v[0]) for v in raw.values()]))
idx={d:i for i,d in enumerate(alldays)}
N=len(alldays)
CL={}; 
for s in SY:
    c=np.full(N,np.nan)
    for dd,px in zip(*raw[s]): c[idx[dd]]=px
    CL[s]=c

def build_positions(hold=20,hi=60,lo=40):
    POS={}
    for s in SY:
        c=CL[s]; pos=np.zeros(N); 
        valid=~np.isnan(c)
        lg=np.full(N,np.nan); lg[valid]=np.log(c[valid])
        r=np.full(N,np.nan); r[1:]=lg[1:]-lg[:-1]
        rv=np.full(N,np.nan)
        for i in range(30,N):
            w=r[i-30:i]; w=w[~np.isnan(w)]
            if len(w)>20: rv[i]=w.std()
        rvp=np.full(N,np.nan)
        for i in range(280,N):
            w=rv[i-250:i]; w=w[~np.isnan(w)]
            if len(w)>150 and not np.isnan(rv[i]): rvp[i]=100.0*np.mean(w<=rv[i])
        M={}
        for LB in (14,28,56,90):
            m=np.full(N,np.nan)
            for i in range(LB,N):
                if not np.isnan(c[i]) and not np.isnan(c[i-LB]) and c[i-LB]>0: m[i]=c[i]/c[i-LB]-1.0
            M[LB]=m
        desired=np.zeros(N)
        for i in range(280,N):
            v=[M[LB][i] for LB in (14,28,56,90)]
            if any(np.isnan(x) for x in v) or np.isnan(rvp[i]) or np.isnan(rv[i]) or rv[i]<=0: continue
            sg=[np.sign(x) for x in v]
            if not(all(x>0 for x in sg) or all(x<0 for x in sg)): continue
            tr=1 if sg[0]>0 else -1
            side = tr if rvp[i]>hi else (-tr if rvp[i]<lo else 0)
            desired[i]=side/rv[i]        # vol-scaled sizing
        # hold for `hold` days after each signal day: carry the most recent non-zero
        held=np.zeros(N); age=10**9; cur=0.0
        for i in range(N):
            if desired[i]!=0: cur=desired[i]; age=0
            else: age+=1
            held[i]= cur if age<hold else 0.0
        POS[s]=held
    return POS

def simulate(POS, lab, target_vol=0.40):
    rets=np.full(N,0.0); turn=np.full(N,0.0)
    prevw={s:0.0 for s in SY}
    for i in range(1,N):
        act={s:POS[s][i-1] for s in SY if POS[s][i-1]!=0 and not np.isnan(CL[s][i]) and not np.isnan(CL[s][i-1])}
        gross=sum(abs(x) for x in act.values())
        w={s:(x/gross if gross>0 else 0.0) for s,x in act.items()}
        pr=0.0
        for s,ws in w.items():
            pr+= ws*(CL[s][i]/CL[s][i-1]-1.0)
        tu=sum(abs(w.get(s,0.0)-prevw.get(s,0.0)) for s in SY)
        rets[i]=pr-tu*COST/2.0
        turn[i]=tu
        prevw={s:w.get(s,0.0) for s in SY}
    d=np.array(alldays)
    m_tr=np.array([x< SPLIT for x in d]); m_te=np.array([x>=SPLIT for x in d])
    print(f"\n=== {lab} ===")
    for nm,msk in (("TRAIN 2020-2023",m_tr),("TEST 2024-2026",m_te)):
        x=rets[msk]; x=x[280//1:] if nm.startswith("TRAIN") else x
        x=x[np.isfinite(x)]
        if len(x)<100: continue
        ann=x.mean()*365; vol=x.std()*np.sqrt(365)
        eq=np.cumprod(1+x); dd=(1-eq/np.maximum.accumulate(eq)).max()
        pos_days=100*np.mean(x!=0)
        print(f"  {nm:16} days={len(x):5d} annRet={100*ann:6.1f}% annVol={100*vol:5.1f}% Sharpe={ann/vol if vol>0 else 0:5.2f} "
              f"maxDD={100*dd:5.1f}% avgTurn={100*turn[msk].mean():4.1f}%/d")
    return rets

POS=build_positions()
r1=simulate(POS,"Two-sided regime rule (vol-scaled, equal risk, 20d hold)")

# benchmark: equal-weight long-only crypto basket
bh=np.full(N,0.0)
for i in range(1,N):
    xs=[CL[s][i]/CL[s][i-1]-1.0 for s in SY if not np.isnan(CL[s][i]) and not np.isnan(CL[s][i-1])]
    if xs: bh[i]=np.mean(xs)
d=np.array(alldays); m_te=np.array([x>=SPLIT for x in d]); m_tr=np.array([x<SPLIT for x in d])
print("\n=== BENCHMARK: equal-weight long-only basket ===")
for nm,msk in (("TRAIN 2020-2023",m_tr),("TEST 2024-2026",m_te)):
    x=bh[msk]; x=x[np.isfinite(x)]
    ann=x.mean()*365; vol=x.std()*np.sqrt(365)
    eq=np.cumprod(1+x); dd=(1-eq/np.maximum.accumulate(eq)).max()
    print(f"  {nm:16} annRet={100*ann:6.1f}% annVol={100*vol:5.1f}% Sharpe={ann/vol if vol>0 else 0:5.2f} maxDD={100*dd:5.1f}%")
