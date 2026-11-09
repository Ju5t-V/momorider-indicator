"""Confirmation stack: require several INDEPENDENT reads to agree before acting.
   Same idea as 4G/4R, but each leg is a documented effect rather than a chart shape."""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008
def load(s):
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    return a[:,0].astype(np.int64),a[:,1],a[:,2],a[:,3],a[:,4],a[:,5]
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
DATA={s:load(s) for s in SY}
SPLIT=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
H=20

def feats(s):
    t,o,h,l,c,v=DATA[s]; n=len(c)
    f={}
    for LB in (14,28,56,90):
        m=np.full(n,np.nan)
        m[LB:]=c[LB:]/c[:-LB]-1.0
        f[f"m{LB}"]=m
    r=np.diff(np.log(c),prepend=np.log(c[0]))
    rv=np.full(n,np.nan)
    for i in range(30,n): rv[i]=r[i-30:i].std()
    f["rv"]=rv
    # trailing percentile of rv (causal)
    rvp=np.full(n,np.nan)
    for i in range(260,n): rvp[i]=100.0*np.mean(rv[i-250:i]<=rv[i])
    f["rvp"]=rvp
    f["t"]=t; f["c"]=c
    return f
F={s:feats(s) for s in SY}

def evaluate(rule,label,period):
    R=[];HIT=[]
    for s in SY:
        f=F[s]; c=f["c"]; t=f["t"]; n=len(c)
        for i in range(260,n-H,H):
            if period=="train" and t[i]>=SPLIT: continue
            if period=="test"  and t[i]< SPLIT: continue
            sig=rule(f,i)
            if sig==0 or sig is None: continue
            fwd=c[i+H]/c[i]-1.0
            R.append(sig*fwd-COST); HIT.append(sig*fwd>0)
    if len(R)<60: return None
    R=np.array(R);HIT=np.array(HIT)
    return dict(n=len(R),hit=100*HIT.mean(),mean=100*R.mean(),
                t=R.mean()/R.std(ddof=1)*np.sqrt(len(R)),
                sr=R.mean()/R.std(ddof=1)*np.sqrt(365.0/H))

def agree(f,i,ks,need):
    v=[f[k][i] for k in ks]
    if any(np.isnan(x) for x in v): return 0
    sg=[np.sign(x) for x in v]
    p=sum(1 for x in sg if x>0); m=sum(1 for x in sg if x<0)
    if p>=need: return 1
    if m>=need: return -1
    return 0

RULES=[
 ("m14 alone",                  lambda f,i: 0 if np.isnan(f["m14"][i]) else np.sign(f["m14"][i])),
 ("m28 alone",                  lambda f,i: 0 if np.isnan(f["m28"][i]) else np.sign(f["m28"][i])),
 ("2 of {14,28,56}",            lambda f,i: agree(f,i,["m14","m28","m56"],2)),
 ("3 of {14,28,56} (unanimous)",lambda f,i: agree(f,i,["m14","m28","m56"],3)),
 ("3 of {14,28,56,90}",         lambda f,i: agree(f,i,["m14","m28","m56","m90"],3)),
 ("4 of {14,28,56,90} (unan.)", lambda f,i: agree(f,i,["m14","m28","m56","m90"],4)),
 ("unanimous + vol<=p70",       lambda f,i: 0 if (np.isnan(f["rvp"][i]) or f["rvp"][i]>70) else agree(f,i,["m14","m28","m56","m90"],4)),
 ("unanimous + vol<=p50",       lambda f,i: 0 if (np.isnan(f["rvp"][i]) or f["rvp"][i]>50) else agree(f,i,["m14","m28","m56","m90"],4)),
 ("unanimous + vol>p70",        lambda f,i: 0 if (np.isnan(f["rvp"][i]) or f["rvp"][i]<=70) else agree(f,i,["m14","m28","m56","m90"],4)),
]
print(f"CONFIRMATION STACK   hold={H}d, cost 8bp, non-overlapping, 29 symbols")
print(f"hit% = price actually moved the signalled way over the next {H} days\n")
print(f"{'rule':30} | {'TRAIN 2020-2023':>30} | {'TEST 2024-2026':>30}")
print(f"{'':30} | {'n':>5}{'hit%':>7}{'mean%':>8}{'t':>5}{'SR':>6} | {'n':>5}{'hit%':>7}{'mean%':>8}{'t':>5}{'SR':>6}")
print("-"*98)
for nm,rule in RULES:
    a=evaluate(rule,nm,"train"); b=evaluate(rule,nm,"test")
    fa=f"{a['n']:5d}{a['hit']:7.1f}{a['mean']:8.3f}{a['t']:5.2f}{a['sr']:6.2f}" if a else " "*30
    fb=f"{b['n']:5d}{b['hit']:7.1f}{b['mean']:8.3f}{b['t']:5.2f}{b['sr']:6.2f}" if b else " "*30
    print(f"{nm:30} | {fa} | {fb}")
