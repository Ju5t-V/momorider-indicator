"""Improve the base rule. Every candidate has a stated reason, tested on the SAME
   frozen base so the comparison is fair. Newey-West t throughout."""
import numpy as np, json, os, glob, datetime as dt
D=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
COST=0.0008; HOLD=20
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(D,"*_D.json")))
SPLIT=int(dt.datetime(2024,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
def nw_t(x,lag):
    x=np.asarray(x,float); n=len(x)
    if n<20: return 0.0
    mu=x.mean(); e=x-mu; s=(e@e)/n
    for k in range(1,lag+1):
        s+=2*(1-k/(lag+1.0))*((e[k:]@e[:-k])/n)
    return mu/np.sqrt(max(s,1e-18)/n)

PRE={}
for s in SY:
    k=json.load(open(os.path.join(D,f"{s}_D.json")))
    a=np.array([[float(x) for x in r[:6]] for r in k])
    t=a[:,0].astype(np.int64); c=a[:,4]; v=a[:,5]; n=len(c)
    r=np.diff(np.log(c),prepend=np.log(c[0]))
    rv=np.full(n,np.nan)
    for i in range(30,n): rv[i]=r[i-30:i].std()
    rvp=np.full(n,np.nan)
    for i in range(280,n): rvp[i]=100.0*np.mean(rv[i-250:i]<=rv[i])
    M={LB:np.concatenate([np.full(LB,np.nan),c[LB:]/c[:-LB]-1.0]) for LB in (14,28,56,90)}
    # daily funding (sum of the 8h prints that fall in the day), then trailing percentile
    fp=np.full(n,np.nan)
    fpath=os.path.join(D,f"{s}_FUND.json")
    if os.path.exists(fpath):
        fr=json.load(open(fpath))
        ft=np.array([int(x["fundingRateTimestamp"]) for x in fr]); fv=np.array([float(x["fundingRate"]) for x in fr])
        o=np.argsort(ft); ft,fv=ft[o],fv[o]
        daily=np.full(n,np.nan)
        for i in range(n):
            m=(ft>=t[i])&(ft<t[i]+86400000)
            if m.any(): daily[i]=fv[m].sum()
        for i in range(280,n):
            w=daily[max(0,i-250):i]; w=w[~np.isnan(w)]
            if len(w)>60 and not np.isnan(daily[i]): fp[i]=100.0*np.mean(w<=daily[i])
    PRE[s]=(t,c,rvp,M,fp,n)

def base_side(rvp_i,sg):
    tr=1 if sg[0]>0 else -1
    if rvp_i>60: return tr
    if rvp_i<40: return -tr
    return 0

def collect(fresh=False,fund_mode=None,period="test"):
    P=[];H=[]
    for s in SY:
        t,c,rvp,M,fp,n=PRE[s]
        prev=0
        for i in range(280,n-HOLD):
            v=[M[LB][i] for LB in (14,28,56,90)]
            ok = not(any(np.isnan(x) for x in v) or np.isnan(rvp[i]))
            sg=[np.sign(x) for x in v] if ok else None
            side = base_side(rvp[i],sg) if (ok and (all(x>0 for x in sg) or all(x<0 for x in sg))) else 0
            fire = side!=0 and (not fresh or prev==0 or prev!=side)
            prev = side
            if not fire: continue
            if (period=="test") != (t[i]>=SPLIT): continue
            if fund_mode is not None:
                if np.isnan(fp[i]): continue
                # crowded-against-us is good: long wants LOW funding, short wants HIGH
                fav = (fp[i]<=50) if side>0 else (fp[i]>=50)
                if fund_mode=="favour" and not fav: continue
                if fund_mode=="against" and fav: continue
            f=c[i+HOLD]/c[i]-1.0
            P.append(side*f-COST); H.append(side*f>0)
    if len(P)<60: return None
    P=np.array(P);H=np.array(H)
    return dict(n=len(P),hit=100*H.mean(),mean=100*P.mean(),t=nw_t(P,HOLD))

TESTS=[("base (every qualifying day)",dict()),
       ("FRESH signal only",dict(fresh=True)),
       ("base + funding favourable",dict(fund_mode="favour")),
       ("base + funding against",dict(fund_mode="against")),
       ("FRESH + funding favourable",dict(fresh=True,fund_mode="favour"))]
print(f"hold={HOLD}d, cost 8bp, Newey-West t\n")
print(f"{'variant':32} | {'TRAIN 2020-2023':>30} | {'TEST 2024-2026':>30}")
print(f"{'':32} | {'n':>6}{'hit%':>7}{'mean%':>9}{'t':>7} | {'n':>6}{'hit%':>7}{'mean%':>9}{'t':>7}")
print("-"*104)
for nm,kw in TESTS:
    a=collect(period="train",**kw); b=collect(period="test",**kw)
    fa=f"{a['n']:6d}{a['hit']:7.1f}{a['mean']:9.3f}{a['t']:7.2f}" if a else " "*30
    fb=f"{b['n']:6d}{b['hit']:7.1f}{b['mean']:9.3f}{b['t']:7.2f}" if b else " "*30
    print(f"{nm:32} | {fa} | {fb}")
