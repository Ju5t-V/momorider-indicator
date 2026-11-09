import numpy as np, os, sys, glob
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from core import load, signals, atr, heikin
from engine import Cfg, run, stats, COST_PER_SIDE

DEV = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT"]

print("=== 1. Does the SIGNAL have edge at all? forward real-price return after entry ===")
print("    (sign-adjusted: long = +ret, short = -ret; compared with all-bars baseline)\n")
print(f"{'sym':9} {'n':>5} " + " ".join(f"{f'+{k}b':>9}" for k in (4,8,16,32,48)) + "   | baseline sd of 16b move")
for s in DEV:
    d=load(s,"30"); sig,aux=signals(d); c=d["c"]
    row=[]
    for k in (4,8,16,32,48):
        r=[]
        for i,side in sig:
            if i+k>=len(c): continue
            x=(c[i+k]-c[i])/c[i]
            r.append(x if side=="L" else -x)
        row.append(np.mean(r)*100 if r else np.nan)
    base=np.std((c[16:]-c[:-16])/c[:-16])*100
    print(f"{s:9} {len(sig):5d} " + " ".join(f"{x:8.3f}%" for x in row) + f"   | {base:.2f}%")

print("\n=== 2. how big are costs in R terms? ===")
for s in DEV:
    d=load(s,"30"); A=atr(d["h"],d["l"],d["c"],14)
    ap=np.nanmedian(A/d["c"])
    for slm in (1.0,1.5,3.0,5.0):
        rp=slm*ap
        print(f"   {s:9} ATR/price={ap*100:.3f}%  stop={slm}xATR -> risk={rp*100:.3f}%  cost={2*COST_PER_SIDE/rp:.3f} R", end="")
        print()
    break

print("\n=== 3. GROSS (no cost) vs NET, pooled over DEV, by stop/target ===")
print(f"{'sl':>5} {'tp':>5} {'n':>5} {'win%':>6} {'grossR':>8} {'netR':>8} {'costR':>7} {'PF net':>7}")
for sl in (1.0,1.5,2.5,4.0):
    for tp in (1.5,3.0,5.0):
        allt=[]
        for s in DEV:
            d=load(s,"30"); allt+=run(d,Cfg(sl_atr=sl,tp_atr=tp,max_bars=48))
        if not allt: continue
        R=np.array([t["R"] for t in allt])
        # recover gross by adding back the cost we charged
        cost=np.array([2*COST_PER_SIDE*(t["entry"])/t["risk_px"] for t in allt])
        G=R+cost
        w=R>0; pf = R[w].sum()/max(1e-9,-R[~w].sum())
        print(f"{sl:5.1f} {tp:5.1f} {len(R):5d} {100*w.mean():6.1f} {G.mean():8.3f} {R.mean():8.3f} {cost.mean():7.3f} {pf:7.2f}")
