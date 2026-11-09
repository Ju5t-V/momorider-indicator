import numpy as np, os, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import load
from engine import Cfg, run, COST_PER_SIDE

DEV=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]
D={s:load(s,"30") for s in DEV}
def ev(**kw):
    allt=[]
    for s in DEV: allt+=run(D[s],Cfg(**kw))
    if not allt: return None
    R=np.array([t["R"] for t in allt]); w=R>0
    cost=np.array([2*COST_PER_SIDE*t["entry"]/t["risk_px"] for t in allt])
    return dict(n=len(R),win=100*w.mean(),net=R.mean(),gross=(R+cost).mean(),
                tot=R.sum(),pf=R[w].sum()/max(1e-9,-R[~w].sum()),
                sh=R.mean()/R.std(ddof=1) if R.std(ddof=1)>0 else 0)

print("=== A. horizon: does letting winners run help? (sl=4 ATR, no filters) ===")
print(f"{'tp':>5} {'maxbars':>8} {'n':>5} {'win%':>6} {'gross':>7} {'net':>7} {'PF':>6} {'sh/t':>6}")
base=dict(sl_atr=4.0)
for tp in (3.0,5.0,8.0,12.0):
    for mb in (48,96,192):
        r=ev(tp_atr=tp,max_bars=mb,**base)
        print(f"{tp:5.1f} {mb:8d} {r['n']:5d} {r['win']:6.1f} {r['gross']:7.3f} {r['net']:7.3f} {r['pf']:6.2f} {r['sh']:6.3f}")

print("\n=== B. filters, one at a time, vs the same base (sl=4 tp=8 maxbars=192) ===")
B=dict(sl_atr=4.0,tp_atr=8.0,max_bars=192)
r0=ev(**B); print(f"{'no filter':28} n={r0['n']:5d} win={r0['win']:5.1f} gross={r0['gross']:7.3f} net={r0['net']:7.3f} PF={r0['pf']:5.2f}")
tests=[("HTF trend (EMA200)",dict(f_htf=True)),
       ("ADX >= 20",dict(f_adx=20.0)),
       ("ADX >= 25",dict(f_adx=25.0)),
       ("BVC flow agrees",dict(f_flow=True)),
       ("VPIN <= 0.30",dict(f_vpin_max=0.30)),
       ("VPIN <= 0.20",dict(f_vpin_max=0.20)),
       ("trailing stop",dict(trail=True)),
       ("ribbon stop",dict(use_ribbon_stop=True))]
for nm,kw in tests:
    r=ev(**{**B,**kw})
    d=r['net']-r0['net']
    print(f"{nm:28} n={r['n']:5d} win={r['win']:5.1f} gross={r['gross']:7.3f} net={r['net']:7.3f} PF={r['pf']:5.2f}  dNet={d:+.3f}")
