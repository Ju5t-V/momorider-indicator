"""Real Bybit funding-rate history (8h). Orthogonal to price: it measures positioning."""
import requests, json, os, time, datetime as dt
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
import glob
SY=sorted(os.path.basename(f).split("_")[0] for f in glob.glob(os.path.join(OUT,"*_D.json")))
def fund(sym):
    url="https://api.bybit.com/v5/market/funding/history"
    rows=[]; end=int(dt.datetime(2026,8,22,tzinfo=dt.timezone.utc).timestamp()*1000)
    start=int(dt.datetime(2019,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
    while True:
        try:
            r=requests.get(url,params=dict(category="linear",symbol=sym,
                           startTime=start,endTime=end,limit=200),timeout=30); j=r.json()
        except Exception: time.sleep(1.5); continue
        if j.get("retCode")!=0: break
        lst=j["result"]["list"]
        if not lst: break
        rows.extend(lst)
        oldest=int(lst[-1]["fundingRateTimestamp"])
        if oldest<=start or len(lst)<200: break
        end=oldest-1; time.sleep(0.08)
    return rows
n=0
for s in SY:
    p=os.path.join(OUT,f"{s}_FUND.json")
    if os.path.exists(p): n+=1; continue
    rr=fund(s)
    if len(rr)<200: print(f"  {s}: {len(rr)} pts, skip"); continue
    json.dump(rr,open(p,"w")); n+=1
    print(f"{s}: {len(rr)} funding pts",flush=True)
print("done",n)
