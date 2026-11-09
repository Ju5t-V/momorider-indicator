"""Fetch Bybit linear-perp klines for a basket of markets, for cross-market testing."""
import requests, json, time, os, sys, datetime as dt
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(OUT, exist_ok=True)

SYMS = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT",
        "LINKUSDT","AVAXUSDT","ADAUSDT","LTCUSDT","SUIUSDT","APTUSDT"]
TFS  = {"30": dt.datetime(2024,1,1,tzinfo=dt.timezone.utc),
        "15": dt.datetime(2025,1,1,tzinfo=dt.timezone.utc)}
END  = dt.datetime(2026,8,20,tzinfo=dt.timezone.utc)

def klines(sym, interval, start_ms, end_ms):
    url="https://api.bybit.com/v5/market/kline"; rows=[]; cur=end_ms; n=0
    while True:
        for attempt in range(4):
            try:
                r=requests.get(url,params=dict(category="linear",symbol=sym,interval=interval,
                                               start=start_ms,end=cur,limit=1000),timeout=30)
                j=r.json(); break
            except Exception as e:
                if attempt==3: print(f"  !! {sym} {interval} net fail {e}",flush=True); return rows
                time.sleep(1.5*(attempt+1))
        if j.get("retCode")!=0:
            print(f"  !! {sym} {interval} retCode {j.get('retCode')} {j.get('retMsg')}",flush=True); break
        lst=j["result"]["list"]
        if not lst: break
        rows.extend(lst); n+=1
        oldest=int(lst[-1][0])
        if oldest<=start_ms or len(lst)<1000: break
        cur=oldest-1; time.sleep(0.09)
    return rows

total=0
for tf, start_dt in TFS.items():
    s_ms=int(start_dt.timestamp()*1000); e_ms=int(END.timestamp()*1000)
    for sym in SYMS:
        path=os.path.join(OUT,f"{sym}_{tf}.json")
        if os.path.exists(path):
            print(f"skip {sym} {tf}m (exists)",flush=True); continue
        raw=klines(sym,tf,s_ms,e_ms)
        seen={}
        for r in raw: seen[int(r[0])]=r
        k=[seen[t_] for t_ in sorted(seen)]
        if len(k)<500:
            print(f"  -- {sym} {tf}m only {len(k)} bars, skipping",flush=True); continue
        json.dump(k,open(path,"w")); total+=len(k)
        print(f"{sym} {tf}m: {len(k)} bars  {dt.datetime.fromtimestamp(int(k[0][0])/1000,dt.timezone.utc):%Y-%m-%d} -> {dt.datetime.fromtimestamp(int(k[-1][0])/1000,dt.timezone.utc):%Y-%m-%d}",flush=True)
print(f"DONE total {total} bars",flush=True)
