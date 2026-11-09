import numpy as np, os, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import load, vpin, bvc_delta, adx, signals
from engine import Cfg, run, COST_PER_SIDE
DEV=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]
D={s:load(s,"30") for s in DEV}

print("=== VPIN / flow distributions (why the absolute thresholds were wrong) ===")
for s in DEV[:2]:
    d=D[s]; tox=vpin(d["c"],d["v"],50); fl=bvc_delta(d["c"],d["v"],50); ad=adx(d["h"],d["l"],d["c"],14)
    print(f"  {s}: VPIN p10/50/90 = {np.percentile(tox,10):.3f}/{np.percentile(tox,50):.3f}/{np.percentile(tox,90):.3f}"
          f"   ADX p25/50/75 = {np.percentile(ad,25):.1f}/{np.percentile(ad,50):.1f}/{np.percentile(ad,75):.1f}")

print("\n=== is the BVC flow filter redundant with the 4G green-close rule? ===")
for s in DEV[:2]:
    d=D[s]; sig,_=signals(d); fl=bvc_delta(d["c"],d["v"],50)
    agree=sum(1 for i,sd in sig if (fl[i]>0)==(sd=="L"))
    print(f"  {s}: flow already agrees with side on {100*agree/len(sig):.1f}% of signals  -> filter is near-vacuous")

def ev(**kw):
    allt=[]
    for s in DEV: allt+=run(D[s],Cfg(**kw))
    if len(allt)<30: return None
    R=np.array([t["R"] for t in allt]); w=R>0
    cost=np.array([2*COST_PER_SIDE*t["entry"]/t["risk_px"] for t in allt])
    return dict(n=len(R),win=100*w.mean(),net=R.mean(),gross=(R+cost).mean(),
                pf=R[w].sum()/max(1e-9,-R[~w].sum()),sh=R.mean()/R.std(ddof=1))

print("\n=== ADX threshold sweep (the one filter that worked), base sl=4 tp=12 mb=96 ===")
B=dict(sl_atr=4.0,tp_atr=12.0,max_bars=96)
print(f"{'ADX>=':>7} {'n':>5} {'win%':>6} {'gross':>7} {'net':>7} {'PF':>6} {'sh/t':>6}")
for a in (0,12,16,18,20,22,25,30):
    r=ev(**{**B,**({} if a==0 else dict(f_adx=float(a)))})
    if r is None: print(f"{a:7d}  too few trades"); continue
    print(f"{a:7d} {r['n']:5d} {r['win']:6.1f} {r['gross']:7.3f} {r['net']:7.3f} {r['pf']:6.2f} {r['sh']:6.3f}")

print("\n=== VPIN as a percentile filter (per-symbol), base + ADX>=20 ===")
print(f"{'VPIN<=p':>8} {'n':>5} {'win%':>6} {'gross':>7} {'net':>7} {'PF':>6}")
import engine
for pct in (100,90,75,50,25):
    allt=[]
    for s in DEV:
        d=D[s]; tox=vpin(d["c"],d["v"],50); thr=np.percentile(tox,pct)
        allt+=[t for t in run(d,Cfg(**B,f_adx=20.0)) if tox[t["i"]]<=thr]
    R=np.array([t["R"] for t in allt]); w=R>0
    cost=np.array([2*COST_PER_SIDE*t["entry"]/t["risk_px"] for t in allt])
    print(f"{pct:8d} {len(R):5d} {100*w.mean():6.1f} {(R+cost).mean():7.3f} {R.mean():7.3f} {R[w].sum()/max(1e-9,-R[~w].sum()):6.2f}")
