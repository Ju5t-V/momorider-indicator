"""Ablation on the Market Intraday Momentum signal.
   TRAIN 2015-2022, TEST 2023-2026 (never touched while choosing).
   OPEX proxy: dealer gamma peaks near option expiry, so Friday / 3rd-Friday are
   observable proxies for the NGE conditioning in Baltussen et al. Table 7."""
import numpy as np, datetime as dt, os, itertools
from scipy import stats
CLOSE={"US500":(23,0),"US30":(23,0),"DAX":(18,30),"FRA40":(18,30),"ESP35":(18,30)}
COST_BP=0.8   # round-trip spread on a retail index CFD

def build(sym):
    r=np.load(os.path.join("..","data",f"mt5_{sym}_M30.npy"))
    t=np.array([dt.datetime.fromtimestamp(x,dt.timezone.utc) for x in r['time']])
    o,c,h,l=r['open'].astype(float),r['close'].astype(float),r['high'].astype(float),r['low'].astype(float)
    hm=np.array([x.hour*60+x.minute for x in t]); days=np.array([x.date() for x in t])
    ch,cm=CLOSE[sym]; last=ch*60+cm-30
    rows=[];prev=None;dayret=[]
    for d in sorted(set(days)):
        m=np.where(days==d)[0]
        il=[i for i in m if hm[i]==last]
        if not il: continue
        i=il[0]
        if prev is not None:
            rod=o[i]/prev-1.0; lh=c[i]/o[i]-1.0
            # realized vol of the day's 30m bars, and range
            rr=c[m]/o[m]-1.0
            rows.append(dict(d=d, rod=rod, lh=lh, rv=rr.std(),
                             dow=d.weekday(), dom=d.day,
                             third_fri=(d.weekday()==4 and 15<=d.day<=21)))
        prev=c[i]
    return rows

DATA={s:build(s) for s in CLOSE}
for s,v in DATA.items(): print(f"{s}: {len(v)} days")
SPLIT=dt.date(2023,1,1)

def evaluate(rows, cond=None):
    sel=[r for r in rows if (cond is None or cond(r))]
    if len(sel)<100: return None
    X=np.array([r["rod"] for r in sel]); Y=np.array([r["lh"] for r in sel])
    ret=np.sign(X)*Y*1e4 - COST_BP
    gross=np.sign(X)*Y*1e4
    sl,ic,rr,p,se=stats.linregress(X,Y)
    return dict(n=len(sel), beta=sl, t=sl/se, gross=gross.mean(), net=ret.mean(),
                sr=ret.mean()/ret.std()*np.sqrt(252) if ret.std()>0 else 0,
                hit=100*np.mean(np.sign(X)==np.sign(Y)))

def pooled(cond, period):
    rows=[]
    for s,v in DATA.items():
        rows+= [r for r in v if (r["d"]<SPLIT if period=="train" else r["d"]>=SPLIT)]
    return evaluate(rows, cond)

rodq={}
allrod=np.abs([r["rod"] for v in DATA.values() for r in v if r["d"]<SPLIT])
rvall=np.array([r["rv"] for v in DATA.values() for r in v if r["d"]<SPLIT])
Q={p:np.percentile(allrod,p) for p in (25,50,75)}
RVQ={p:np.percentile(rvall,p) for p in (50,75)}

TESTS=[
 ("baseline (all days)",            None),
 ("|r_ROD| >= median",              lambda r: abs(r["rod"])>=Q[50]),
 ("|r_ROD| >= p75",                 lambda r: abs(r["rod"])>=Q[75]),
 ("|r_ROD| <= p25 (small moves)",   lambda r: abs(r["rod"])<=Q[25]),
 ("high realised vol (>=median)",   lambda r: r["rv"]>=RVQ[50]),
 ("high realised vol (>=p75)",      lambda r: r["rv"]>=RVQ[75]),
 ("Friday only (weekly OPEX)",      lambda r: r["dow"]==4),
 ("3rd Friday (monthly OPEX)",      lambda r: r["third_fri"]),
 ("NOT Friday",                     lambda r: r["dow"]!=4),
 ("|r_ROD|>=p75 AND high vol",      lambda r: abs(r["rod"])>=Q[75] and r["rv"]>=RVQ[50]),
 ("|r_ROD|>=p75 AND Friday",        lambda r: abs(r["rod"])>=Q[75] and r["dow"]==4),
]
print(f"\n{'condition':32} | {'TRAIN 2015-2022':>34} | {'TEST 2023-2026':>34}")
print(f"{'':32} | {'n':>5}{'t':>7}{'gross':>8}{'net':>7}{'SR':>7} | {'n':>5}{'t':>7}{'gross':>8}{'net':>7}{'SR':>7}")
print("-"*106)
for nm,cond in TESTS:
    a=pooled(cond,"train"); b=pooled(cond,"test")
    fa=f"{a['n']:5d}{a['t']:7.2f}{a['gross']:8.2f}{a['net']:7.2f}{a['sr']:7.2f}" if a else " "*34
    fb=f"{b['n']:5d}{b['t']:7.2f}{b['gross']:8.2f}{b['net']:7.2f}{b['sr']:7.2f}" if b else " "*34
    print(f"{nm:32} | {fa} | {fb}")
print(f"\ncost assumed {COST_BP} bp round trip; gross/net in bp per trade; SR annualised on 252 trades")
