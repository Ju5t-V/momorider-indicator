"""Time-series momentum on real Bybit daily data.
   Signal at close of day t uses ONLY data up to t. Enter next open-equivalent (close t),
   hold H days, exit. Costs charged both legs."""
import numpy as np, json, os, glob, datetime as dt
from scipy import stats
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008   # 8bp round trip: Bybit taker 5.5bp + slippage

def load(s):
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    return a[:,0].astype(np.int64),a[:,1],a[:,2],a[:,3],a[:,4],a[:,5]

SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
DATA={s:load(s) for s in SY}
print(f"{len(SY)} symbols\n")

SPLIT=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)

def run(LB,H,period):
    R=[];HIT=[]
    for s in SY:
        t,o,h,l,c,v=DATA[s]
        n=len(c)
        if n<LB+H+30: continue
        for i in range(LB, n-H, H):          # non-overlapping holds
            if period=="train" and t[i]>=SPLIT: continue
            if period=="test"  and t[i]< SPLIT: continue
            past=c[i]/c[i-LB]-1.0
            if past==0: continue
            sig=np.sign(past)
            fwd=c[i+H]/c[i]-1.0
            R.append(sig*fwd-COST); HIT.append(sig*fwd>0)
    if len(R)<80: return None
    R=np.array(R);HIT=np.array(HIT)
    return dict(n=len(R),mean=R.mean(),hit=100*HIT.mean(),
                t=R.mean()/R.std(ddof=1)*np.sqrt(len(R)),
                sr=R.mean()/R.std(ddof=1)*np.sqrt(365.0/H))

print("TIME-SERIES MOMENTUM  (sign of past LB-day return, hold H days, non-overlapping)")
print("cost 8bp round trip.  hit% = did price actually go the signalled way\n")
print(f"{'LB':>4}{'H':>4} | {'TRAIN 2020-2023':>36} | {'TEST 2024-2026':>36}")
print(f"{'':>8} | {'n':>5}{'hit%':>7}{'mean%':>8}{'t':>6}{'SR':>7} | {'n':>5}{'hit%':>7}{'mean%':>8}{'t':>6}{'SR':>7}")
print("-"*88)
best=[]
for LB in (7,14,21,28,56,90):
    for H in (1,3,5,10,20):
        a=run(LB,H,"train"); b=run(LB,H,"test")
        fa=f"{a['n']:5d}{a['hit']:7.1f}{100*a['mean']:8.3f}{a['t']:6.2f}{a['sr']:7.2f}" if a else " "*36
        fb=f"{b['n']:5d}{b['hit']:7.1f}{100*b['mean']:8.3f}{b['t']:6.2f}{b['sr']:7.2f}" if b else " "*36
        print(f"{LB:4d}{H:4d} | {fa} | {fb}")
        if a and b: best.append((LB,H,a,b))
print("\nfull-sample check on the configs that were positive in BOTH halves:")
for LB,H,a,b in best:
    if a['t']>1.5 and b['t']>1.5:
        print(f"   LB={LB:3d} H={H:2d}  train t={a['t']:.2f} hit={a['hit']:.1f}%   test t={b['t']:.2f} hit={b['hit']:.1f}%  SR_test={b['sr']:.2f}")
