"""Real Bybit daily klines + funding history. No synthetic data anywhere."""
import requests, json, time, os, datetime as dt
OUT=os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","data")
os.makedirs(OUT,exist_ok=True)
SYMS=["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT","LINKUSDT","AVAXUSDT",
      "ADAUSDT","LTCUSDT","DOTUSDT","MATICUSDT","ATOMUSDT","UNIUSDT","FILUSDT","NEARUSDT",
      "APTUSDT","ARBUSDT","OPUSDT","INJUSDT","SUIUSDT","TIAUSDT","SEIUSDT","RUNEUSDT",
      "AAVEUSDT","ALGOUSDT","ETCUSDT","BCHUSDT","TRXUSDT","XLMUSDT"]
def kl(sym,interval,start,end):
    url="https://api.bybit.com/v5/market/kline"; rows=[]; cur=end
    while True:
        for a in range(4):
            try:
                r=requests.get(url,params=dict(category="linear",symbol=sym,interval=interval,
                                start=start,end=cur,limit=1000),timeout=30); j=r.json(); break
            except Exception:
                if a==3: return rows
                time.sleep(1.5*(a+1))
        if j.get("retCode")!=0: break
        lst=j["result"]["list"]
        if not lst: break
        rows.extend(lst); old=int(lst[-1][0])
        if old<=start or len(lst)<1000: break
        cur=old-1; time.sleep(0.08)
    return rows
S=int(dt.datetime(2019,1,1,tzinfo=dt.timezone.utc).timestamp()*1000)
E=int(dt.datetime(2026,8,22,tzinfo=dt.timezone.utc).timestamp()*1000)
ok=[]
for s in SYMS:
    p=os.path.join(OUT,f"{s}_D.json")
    if os.path.exists(p): ok.append(s); continue
    raw=kl(s,"D",S,E)
    seen={}
    for r in raw: seen[int(r[0])]=r
    k=[seen[t] for t in sorted(seen)]
    if len(k)<400: print(f"  {s}: only {len(k)} days, skip"); continue
    json.dump(k,open(p,"w")); ok.append(s)
    print(f"{s}: {len(k)} days {dt.datetime.fromtimestamp(int(k[0][0])/1000,dt.timezone.utc):%Y-%m-%d}..{dt.datetime.fromtimestamp(int(k[-1][0])/1000,dt.timezone.utc):%Y-%m-%d}",flush=True)
print("OK:",len(ok))
