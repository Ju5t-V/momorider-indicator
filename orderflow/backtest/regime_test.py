"""Test the Dim/Eraker/Vilkov (2025) prediction on recent data using a proxy:
   positive dealer gamma suppresses realised vol -> LOW vol ~ long-gamma ~ REVERSAL
   negative dealer gamma amplifies             -> HIGH vol ~ short-gamma ~ MOMENTUM
   If true, beta(r_LH ~ r_ROD) should be NEGATIVE on quiet days and POSITIVE on wild ones."""
import numpy as np, datetime as dt, os
from scipy import stats
CLOSE={"US500":(23,0),"US30":(23,0),"DAX":(18,30),"FRA40":(18,30),"ESP35":(18,30)}
def build(sym):
    r=np.load(os.path.join("..","data",f"mt5_{sym}_M30.npy"))
    t=np.array([dt.datetime.fromtimestamp(x,dt.timezone.utc) for x in r['time']])
    o,c=r['open'].astype(float),r['close'].astype(float)
    hm=np.array([x.hour*60+x.minute for x in t]); days=np.array([x.date() for x in t])
    ch,cm=CLOSE[sym]; last=ch*60+cm-30
    out=[];prev=None;rvhist=[]
    for d in sorted(set(days)):
        m=np.where(days==d)[0]; il=[i for i in m if hm[i]==last]
        if not il: continue
        i=il[0]; rr=c[m]/o[m]-1.0; rv=rr.std()
        if prev is not None: out.append(dict(d=d,rod=o[i]/prev-1.0,lh=c[i]/o[i]-1.0,rv=rv))
        prev=c[i]; rvhist.append(rv)
    # causal vol percentile: rank today's RV against the trailing 250 days only
    for k,row in enumerate(out):
        j=k+1
        w=[out[x]["rv"] for x in range(max(0,j-250),j)]
        row["rvpct"]=100.0*np.mean(np.array(w)<=row["rv"]) if len(w)>30 else np.nan
    return out
ALL=[]
for s in CLOSE: ALL+=[dict(sym=s,**r) for r in build(s)]
ALL=[r for r in ALL if np.isfinite(r.get("rvpct",np.nan))]
print(f"{len(ALL)} symbol-days with a causal trailing vol percentile\n")

def blk(rows,label):
    if len(rows)<80: print(f"{label:38} n={len(rows):5d}  too few"); return
    X=np.array([r["rod"] for r in rows]); Y=np.array([r["lh"] for r in rows])
    sl,ic,rr,p,se=stats.linregress(X,Y)
    mom=np.sign(X)*Y*1e4          # momentum P&L
    rev=-np.sign(X)*Y*1e4         # reversal P&L
    tag=""
    if sl/se>1.96: tag="  <- MOMENTUM sig"
    if sl/se<-1.96: tag="  <- REVERSAL sig"
    print(f"{label:38} n={len(rows):5d} beta={sl:+8.4f} t={sl/se:+6.2f} momP&L={mom.mean():+6.2f}bp revP&L={rev.mean():+6.2f}bp{tag}")

for per,lo,hi in (("2015-2022",2015,2022),("2023-2026 (recent)",2023,2026)):
    rows=[r for r in ALL if lo<=r["d"].year<=hi]
    print(f"===== {per} =====")
    blk(rows,"  all days")
    blk([r for r in rows if r["rvpct"]<=25],"  quiet  (vol pct <=25) ~ long gamma")
    blk([r for r in rows if 25<r["rvpct"]<=75],"  normal (25-75)")
    blk([r for r in rows if r["rvpct"]>75],"  wild   (vol pct >75) ~ short gamma")
    blk([r for r in rows if r["rvpct"]>90],"  extreme(vol pct >90)")
    print()
