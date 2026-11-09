import numpy as np, os, sys, datetime as dt, glob
from scipy.stats import norm, skew, kurtosis
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import load, atr
from engine import Cfg, run
import engine

DEV=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]
HOLD=["DOGEUSDT","BNBUSDT","LINKUSDT","AVAXUSDT","ADAUSDT","LTCUSDT","SUIUSDT","APTUSDT"]
ALL=DEV+HOLD
BASE=dict(sl_atr=4.0,tp_atr=12.0,max_bars=96)

print("=== 1. COST SENSITIVITY: what fee+slippage does this need to break even? ===")
print("    (all 12 symbols, no discretionary filters, 2024-2026)\n")
print(f"{'cost/side':>10} {'roundtrip':>10} {'n':>5} {'net R':>8} {'PF':>6}  note")
orig=engine.COST_PER_SIDE
for cps in (0.0, 0.0002, 0.0004, 0.0005, 0.0007, 0.0010):
    engine.COST_PER_SIDE=cps
    allt=[]
    for s in ALL: allt+=run(load(s,"30"),Cfg(**BASE))
    R=np.array([t["R"] for t in allt]); w=R>0
    note=""
    if cps==0.0: note="gross / theoretical"
    if abs(cps-0.0005)<1e-9: note="Bybit taker 0.055%, zero slippage"
    if abs(cps-0.0007)<1e-9: note="<- what I used (taker + 0.015% slip)"
    if abs(cps-0.0002)<1e-9: note="maker 0.02% (limit entries)"
    print(f"{100*cps:9.3f}% {200*cps:9.3f}% {len(R):5d} {R.mean():+8.3f} {R[w].sum()/max(1e-9,-R[~w].sum()):6.2f}  {note}")
engine.COST_PER_SIDE=orig

print("\n=== 2. DEFLATED SHARPE (Bailey & Lopez de Prado 2014) ===")
# collect the Sharpes of every configuration I actually tried on DEV (honest trial count)
sharpes=[]
grid=[]
for sl in (1.0,1.5,2.5,4.0):
    for tp in (1.5,3.0,5.0,8.0,12.0):
        grid.append(dict(sl_atr=sl,tp_atr=tp,max_bars=96))
for a in (12,16,18,20,22,25,30):
    grid.append(dict(sl_atr=4.0,tp_atr=12.0,max_bars=96,f_adx=float(a)))
for mb in (48,192):
    grid.append(dict(sl_atr=4.0,tp_atr=12.0,max_bars=mb))
for kw in (dict(f_htf=True),dict(f_flow=True),dict(trail=True),dict(use_ribbon_stop=True)):
    grid.append({**BASE,**kw})
for cfg in grid:
    allt=[]
    for s in DEV: allt+=run(load(s,"30"),Cfg(**cfg))
    if len(allt)<30: continue
    R=np.array([t["R"] for t in allt])
    if R.std(ddof=1)>0: sharpes.append(R.mean()/R.std(ddof=1))
N=len(sharpes); V=np.var(sharpes,ddof=1); g=0.5772156649
sr0=np.sqrt(V)*((1-g)*norm.ppf(1-1.0/N)+g*norm.ppf(1-1.0/(N*np.e)))
print(f"  trials actually run on DEV: N={N}")
print(f"  spread of per-trade Sharpes across trials: sd={np.sqrt(V):.4f}")
print(f"  E[max Sharpe] under the null (pure luck):  SR0={sr0:.4f}")

for nm,syms,tf in (("DEV pooled (tuned on)",DEV,None),
                   ("HOLDOUT pooled (unseen)",HOLD,None)):
    allt=[]
    for s in syms: allt+=run(load(s,"30"),Cfg(**BASE))
    R=np.array([t["R"] for t in allt]); T=len(R)
    sr=R.mean()/R.std(ddof=1)
    g3=skew(R); g4=kurtosis(R,fisher=False)
    den=np.sqrt(max(1e-12,1-g3*sr+(g4-1)/4.0*sr**2))
    z=(sr-sr0)*np.sqrt(T-1)/den
    print(f"  {nm:26} SR/trade={sr:+.4f}  vs SR0={sr0:.4f}  ->  DSR = {norm.cdf(z):.3f}")
print("  (DSR is the probability the edge is real given the number of trials.")
print("   >0.95 = credible. Anything near 0.5 or below is indistinguishable from luck.)")

print("\n=== 3. 15m timeframe (the TF you actually trade), if data ready ===")
f15=sorted({os.path.basename(f).split('_')[0] for f in glob.glob(os.path.join('..','data','*_15.json'))})
if not f15: print("   15m data still downloading")
else:
    allt=[]
    for s in f15:
        tr=run(load(s,"15"),Cfg(**BASE)); allt+=tr
        R=np.array([t["R"] for t in tr]); w=R>0
        print(f"   {s:9} n={len(R):5d} win={100*w.mean():5.1f}% net={R.mean():+.3f} PF={R[w].sum()/max(1e-9,-R[~w].sum()):5.2f}")
    R=np.array([t["R"] for t in allt]); w=R>0
    print(f"   {'POOLED':9} n={len(R):5d} win={100*w.mean():5.1f}% net={R.mean():+.3f} PF={R[w].sum()/max(1e-9,-R[~w].sum()):5.2f}")
