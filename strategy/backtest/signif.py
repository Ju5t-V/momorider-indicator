import numpy as np, os, sys, glob
from scipy import stats
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import load, signals
ALL=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT",
     "LINKUSDT","AVAXUSDT","ADAUSDT","LTCUSDT","SUIUSDT","APTUSDT"]
HOR=(8,16,32,48,96)
print("Does a 4G/4R signal predict DIRECTION? sign-adjusted forward return on REAL prices.")
print("H0: mean = 0. t-stat uses the per-signal dispersion, so it accounts for how noisy crypto is.\n")
print(f"{'symbol':10} {'n':>5} " + "  ".join(f"{f'+{k}b mean':>10} {'t':>6}" for k in (16,48,96)))
print("-"*82)
pool={k:[] for k in HOR}
for s in ALL:
    d=load(s,"30"); sig,_=signals(d); c=d["c"]
    row=f"{s:10} {len(sig):5d} "
    for k in HOR:
        r=[]
        for i,side in sig:
            if i+k>=len(c): continue
            x=(c[i+k]-c[i])/c[i]
            r.append(x if side=="L" else -x)
        r=np.array(r); pool[k]+=list(r)
        if k in (16,48,96):
            t=stats.ttest_1samp(r,0.0)
            row+=f"  {100*r.mean():9.3f}% {t.statistic:6.2f}"
    print(row)
print("-"*82)
row=f"{'POOLED':10} {len(pool[16]):5d} "
for k in (16,48,96):
    r=np.array(pool[k]); t=stats.ttest_1samp(r,0.0)
    row+=f"  {100*r.mean():9.3f}% {t.statistic:6.2f}"
print(row)
print("\nfull pooled detail:")
for k in HOR:
    r=np.array(pool[k]); t=stats.ttest_1samp(r,0.0)
    print(f"  +{k:3d} bars: mean={100*r.mean():+.4f}%  sd={100*r.std():.2f}%  t={t.statistic:+.2f}  p={t.pvalue:.3f}  n={len(r)}")
print("\n  reference: a round trip costs ~0.14% (taker+slippage), so the mean move")
print("  must clear ~0.14% just to break even before any stop/target logic.")
