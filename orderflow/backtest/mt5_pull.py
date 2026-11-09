import MetaTrader5 as mt5, numpy as np, datetime as dt, os, json, sys
OUT=os.path.join("..","data"); os.makedirs(OUT,exist_ok=True)
SYMS=["US500","US30","DAX","UK100","JP225","XAUUSD","EURUSD","USDJPY","GBPUSD","AUS200","FRA40","ESP35"]
if not mt5.initialize(): print("fail",mt5.last_error()); sys.exit()
got=[]
for s in SYMS:
    if not mt5.symbol_select(s,True): print(f"  {s}: not available"); continue
    r=mt5.copy_rates_range(s, mt5.TIMEFRAME_M30,
        dt.datetime(2015,1,1,tzinfo=dt.timezone.utc), dt.datetime(2026,8,22,tzinfo=dt.timezone.utc))
    if r is None or len(r)<5000: print(f"  {s}: only {0 if r is None else len(r)} bars, skip"); continue
    np.save(os.path.join(OUT,f"mt5_{s}_M30.npy"), r)
    t0=dt.datetime.fromtimestamp(r['time'][0],dt.timezone.utc); t1=dt.datetime.fromtimestamp(r['time'][-1],dt.timezone.utc)
    print(f"  {s}: {len(r)} bars {t0:%Y-%m-%d}..{t1:%Y-%m-%d}"); got.append(s)
mt5.shutdown()
print("saved:",got)
