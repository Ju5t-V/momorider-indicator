"""
MomoRiderDaily — the whole daily routine in one double-clickable file.

  1. Cross-sectional momentum basket  (Bybit, public API, no key)
  2. Dealer gamma regime for MT5      (free option chain)

Built to a standalone .exe with PyInstaller, so it runs on a machine with no
Python installed. Writes its output next to the .exe, and also into the
MetaTrader Files folders so MIM_GEX.mq5 can read the regime.
"""
import os, sys, csv, json, datetime as dt, glob, traceback

# ---------------------------------------------------------------- paths
def app_dir():
    """Folder the exe (or script) actually lives in — not the temp unpack dir."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

OUT = os.path.join(app_dir(), "output")
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- part 1: basket
UNIVERSE = ["BTCUSDT","ETHUSDT","SOLUSDT","XRPUSDT","DOGEUSDT","BNBUSDT","LINKUSDT",
            "AVAXUSDT","ADAUSDT","LTCUSDT","DOTUSDT","ATOMUSDT","UNIUSDT","FILUSDT",
            "NEARUSDT","APTUSDT","ARBUSDT","OPUSDT","INJUSDT","SUIUSDT","TIAUSDT",
            "SEIUSDT","RUNEUSDT","AAVEUSDT","ALGOUSDT","ETCUSDT","BCHUSDT","TRXUSDT",
            "XLMUSDT"]
LOOKBACK, VOL_WINDOW, FRACTION, HOLD_DAYS, MAX_WEIGHT = 14, 30, 0.25, 5, 0.10

def basket():
    import requests
    import numpy as np
    rows = []
    for i, s in enumerate(UNIVERSE, 1):
        sys.stdout.write(f"\r   fetching {i}/{len(UNIVERSE)}  {s:<12}")
        sys.stdout.flush()
        try:
            r = requests.get("https://api.bybit.com/v5/market/kline",
                             params=dict(category="linear", symbol=s, interval="D", limit=160),
                             timeout=30).json()
            if r.get("retCode") != 0: continue
            k = sorted(r["result"]["list"], key=lambda x: int(x[0]))
            c = np.array([float(x[4]) for x in k]); t = int(k[-1][0])
        except Exception:
            continue
        if len(c) < max(LOOKBACK, VOL_WINDOW) + 5: continue
        mom = c[-1]/c[-1-LOOKBACK] - 1.0
        vol = np.diff(np.log(c))[-VOL_WINDOW:].std()
        if not np.isfinite(mom) or not np.isfinite(vol) or vol <= 0: continue
        rows.append(dict(sym=s, mom=float(mom), vol=float(vol), px=float(c[-1]),
                         asof=dt.datetime.fromtimestamp(t/1000, dt.timezone.utc).date()))
    sys.stdout.write("\r" + " " * 46 + "\r")
    if len(rows) < 10:
        print("   could not fetch enough symbols - check your connection."); return None
    rows.sort(key=lambda r: r["mom"])
    k = max(2, int(len(rows) * FRACTION))
    shorts, longs = rows[:k], rows[-k:]
    for grp in (longs, shorts):
        w = {r["sym"]: 1.0/r["vol"] for r in grp}
        tot = sum(w.values()); w = {a: 0.5*b/tot for a, b in w.items()}
        for _ in range(20):
            over = {a: b for a, b in w.items() if b > MAX_WEIGHT}
            if not over: break
            ex = sum(b - MAX_WEIGHT for b in over.values())
            for a in over: w[a] = MAX_WEIGHT
            room = {a: b for a, b in w.items() if b < MAX_WEIGHT}
            tr = sum(room.values())
            if tr <= 0: break
            for a in room: w[a] = min(MAX_WEIGHT, w[a] + ex*w[a]/tr)
        for r in grp: r["weight"] = w[r["sym"]]
    asof = rows[0]["asof"]
    print(f"   CROSS-SECTIONAL MOMENTUM BASKET  as of {asof} (UTC daily close)")
    print(f"   universe {len(rows)}   lookback {LOOKBACK}d   rebalance every {HOLD_DAYS}d\n")
    print(f"   {'':3}{'symbol':12}{'14d mom':>10}{'30d vol':>10}{'weight':>10}   price")
    print("   " + "-"*59)
    for r in sorted(longs, key=lambda r: -r["mom"]):
        print(f"   L {r['sym']:12}{100*r['mom']:9.1f}%{100*r['vol']:9.1f}%{100*r['weight']:9.2f}%   {r['px']:.6g}")
    print()
    for r in sorted(shorts, key=lambda r: r["mom"]):
        print(f"   S {r['sym']:12}{100*r['mom']:9.1f}%{100*r['vol']:9.1f}%{100*r['weight']:9.2f}%   {r['px']:.6g}")
    print("   " + "-"*59)
    print(f"   long {100*sum(r['weight'] for r in longs):.1f}%  short {100*sum(r['weight'] for r in shorts):.1f}%  "
          f"-> dollar-neutral.  {len(rows)-2*k} middle names: no position.")
    print(f"   next rebalance: {asof + dt.timedelta(days=HOLD_DAYS)}")
    p = os.path.join(OUT, "basket.json")
    json.dump(dict(asof=str(asof), longs=[r["sym"] for r in longs],
                   shorts=[r["sym"] for r in shorts],
                   weights={r["sym"]: round(r["weight"], 5) for r in longs+shorts}),
              open(p, "w"), indent=1)
    print(f"   saved -> {p}")
    return rows

# ---------------------------------------------------------------- part 2: GEX
def bs_gamma(S, K, T, sigma, r=0.045):
    # standard-normal pdf written out so scipy is not needed in the bundle
    import numpy as np
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, float), 1e-4)
    d1 = (np.log(S/np.asarray(K, float)) + (r + 0.5*sigma**2)*T)/(sigma*np.sqrt(T))
    pdf = np.exp(-0.5*d1*d1)/np.sqrt(2.0*np.pi)
    return pdf/(S*sigma*np.sqrt(T))

def gex(ticker="SPY", max_expiries=6):
    import numpy as np, pandas as pd, yfinance as yf
    tk = yf.Ticker(ticker)
    h = tk.history(period="5d")
    if h is None or len(h) == 0: raise RuntimeError("no price history")
    S = float(h["Close"].iloc[-1])
    today = dt.datetime.now(dt.timezone.utc).date()
    C, P = [], []
    for e in tk.options[:max_expiries]:
        try: ch = tk.option_chain(e)
        except Exception: continue
        T = max((dt.date.fromisoformat(e) - today).days, 1)/365.0
        for df, box in ((ch.calls, C), (ch.puts, P)):
            d = df[["strike","openInterest","impliedVolatility"]].copy(); d["T"] = T
            box.append(d)
    if not C or not P: raise RuntimeError("no chain data")
    tot = 0.0; by = {}
    for parts, sgn in ((C, +1.0), (P, -1.0)):
        d = pd.concat(parts)
        g = bs_gamma(S, d["strike"].values, d["T"].values, d["impliedVolatility"].values)
        oi = np.nan_to_num(d["openInterest"].values.astype(float))
        dollar = sgn * oi * g * 100 * S * S * 0.01
        tot += float(np.nansum(dollar))
        for kk, vv in zip(d["strike"].values, dollar):
            if np.isfinite(vv): by[kk] = by.get(kk, 0.0) + vv
    ks = np.array(sorted(by)); cum = np.cumsum([by[x] for x in ks])
    flip = None
    cross = np.where(np.diff(np.sign(cum)) != 0)[0]
    if len(cross):
        cand = []
        for i in cross:
            y0, y1 = cum[i], cum[i+1]
            cand.append(ks[i] - y0*(ks[i+1]-ks[i])/(y1-y0) if y1 != y0 else ks[i])
        flip = float(min(cand, key=lambda x: abs(x-S)))
    return S, tot, flip

def mt5_dirs():
    base = os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal")
    out = []
    c = os.path.join(base, "Common", "Files")
    if os.path.isdir(c): out.append(c)
    out += glob.glob(os.path.join(base, "*", "MQL5", "Files"))
    return out

def run_gex(ticker="SPY"):
    S, g, flip = gex(ticker)
    regime = "MOMENTUM (dealers short gamma)" if g < 0 else "REVERSAL (dealers long gamma)"
    print(f"   {ticker}  spot {S:.2f}")
    print(f"   dealer GEX : ${g/1e9:+.3f} bn per 1% move")
    print(f"   gamma flip : {flip:.2f}" if flip else "   gamma flip : n/a")
    print(f"   REGIME     : {regime}")
    row = [ticker, dt.datetime.now(dt.timezone.utc).strftime("%Y.%m.%d %H:%M"),
           f"{g:.0f}", f"{S:.4f}", f"{flip:.4f}" if flip else "", regime]
    n = 0
    for d in mt5_dirs() + [OUT]:
        try:
            with open(os.path.join(d, "gex_regime.csv"), "w", newline="", encoding="ascii") as f:
                w = csv.writer(f); w.writerow(["ticker","utc","gex","spot","flip","regime"]); w.writerow(row)
            n += 1
        except Exception:
            pass
    print(f"   wrote gex_regime.csv to {n} location(s), including your MetaTrader Files folders")

# ---------------------------------------------------------------- main
def main():
    print("=" * 66)
    print("  MOMORIDER DAILY")
    print("=" * 66)
    print("\n[1/2] Cross-sectional momentum basket\n")
    try:
        basket()
    except Exception:
        print("   basket step failed:"); traceback.print_exc(limit=2)
    print("\n" + "-" * 66)
    print("\n[2/2] Dealer gamma regime (for MIM_GEX in MetaTrader)\n")
    try:
        run_gex("SPY")
    except Exception as e:
        print(f"   GEX step failed ({type(e).__name__}). Yahoo may be rate-limiting; retry shortly.")
    print("\n" + "=" * 66)
    print(f"  Output folder: {OUT}")
    print("=" * 66)

if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
    try:
        input("\nPress Enter to close...")
    except EOFError:
        pass
