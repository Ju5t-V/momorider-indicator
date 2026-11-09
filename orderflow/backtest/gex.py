"""
Dealer Gamma Exposure (GEX) computed from a FREE options chain.

Convention follows Baltussen, Da, Lammers & Martens (2021, JFE 142:377-403), sec 4.1:
  (ii)  call options are sold by investors and BOUGHT by option market makers
  (iii) put  options are bought by investors and SOLD  by option market makers
  (iv)  market makers delta-hedge

so dealer net gamma per 1% move, in dollars:

    GEX = SUM_calls OI * Gamma * 100 * S^2 * 0.01
        - SUM_puts  OI * Gamma * 100 * S^2 * 0.01

Sign is what matters:
    GEX < 0  dealers are SHORT gamma -> they hedge WITH the move -> MOMENTUM into the close
    GEX > 0  dealers are LONG  gamma -> they hedge AGAINST the move -> REVERSAL into the close

Evidence:
  Baltussen et al. Table 7 (S&P500 futures, 1996-2020): regressing last-half-hour return
  on rest-of-day return gives beta 0.82 (t=1.03, ns) when NGE>=0 but 6.63 (t=4.78) when
  NGE<0. Dim, Eraker & Vilkov (2025) find positive dealer gamma strengthens intraday
  REVERSAL and negative gamma strengthens MOMENTUM.
"""
import numpy as np
import datetime as dt
from scipy.stats import norm

def bs_gamma(S, K, T, sigma, r=0.045, q=0.0):
    """Black-Scholes gamma. Same for calls and puts."""
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, float), 1e-4)
    d1 = (np.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))

def chain_gex(calls, puts, S, r=0.045, contract_mult=100):
    """calls/puts: DataFrames with strike, openInterest, impliedVolatility, T (years)."""
    out = {}
    tot = 0.0
    by_strike = {}
    for df, sign, tag in ((calls, +1.0, "call"), (puts, -1.0, "put")):
        if df is None or len(df) == 0: continue
        g = bs_gamma(S, df["strike"].values, df["T"].values,
                     df["impliedVolatility"].values, r)
        oi = np.nan_to_num(df["openInterest"].values.astype(float))
        dollar = sign * oi * g * contract_mult * S * S * 0.01
        tot += np.nansum(dollar)
        out[tag] = np.nansum(dollar)
        for k, d in zip(df["strike"].values, dollar):
            if np.isfinite(d): by_strike[k] = by_strike.get(k, 0.0) + d
    out["total"] = tot
    out["by_strike"] = dict(sorted(by_strike.items()))
    return out

def gamma_flip(by_strike, S):
    """Spot level where cumulative GEX crosses zero (the 'flip' / zero-gamma level)."""
    ks = np.array(sorted(by_strike))
    if len(ks) < 3: return None
    vals = np.array([by_strike[k] for k in ks])
    cum = np.cumsum(vals)
    sgn = np.sign(cum)
    idx = np.where(np.diff(sgn) != 0)[0]
    if len(idx) == 0: return None
    # take the crossing nearest spot
    cands = []
    for i in idx:
        x0, x1 = ks[i], ks[i + 1]; y0, y1 = cum[i], cum[i + 1]
        x = x0 - y0 * (x1 - x0) / (y1 - y0) if y1 != y0 else x0
        cands.append(x)
    return float(min(cands, key=lambda x: abs(x - S)))

def fetch_gex(ticker="SPY", max_expiries=6, r=0.045):
    """Free chain via yfinance. Returns dict with total GEX, sign, flip level."""
    import yfinance as yf
    import pandas as pd
    tk = yf.Ticker(ticker)
    hist = tk.history(period="5d")
    if hist is None or len(hist) == 0: raise RuntimeError("no price history")
    S = float(hist["Close"].iloc[-1])
    exps = tk.options[:max_expiries]
    now = dt.datetime.now(dt.timezone.utc).date()
    C = []; P = []
    for e in exps:
        try: ch = tk.option_chain(e)
        except Exception: continue
        T = max((dt.date.fromisoformat(e) - now).days, 0) / 365.0
        for df, box in ((ch.calls, C), (ch.puts, P)):
            d = df[["strike", "openInterest", "impliedVolatility"]].copy()
            d["T"] = max(T, 1.0 / 365.0)
            box.append(d)
    if not C or not P: raise RuntimeError("no chain data")
    calls = pd.concat(C); puts = pd.concat(P)
    g = chain_gex(calls, puts, S, r)
    flip = gamma_flip(g["by_strike"], S)
    return dict(ticker=ticker, spot=S, gex=g["total"], call_gex=g["call"],
                put_gex=g["put"], flip=flip, n_expiries=len(exps),
                regime="MOMENTUM (dealers short gamma)" if g["total"] < 0
                       else "REVERSAL (dealers long gamma)")

if __name__ == "__main__":
    import sys
    for t in (sys.argv[1:] or ["SPY", "QQQ"]):
        try:
            r = fetch_gex(t)
            print(f"\n{r['ticker']}  spot {r['spot']:.2f}   ({r['n_expiries']} expiries)")
            print(f"  dealer GEX : ${r['gex']/1e9:+.3f} bn per 1% move")
            print(f"    calls    : ${r['call_gex']/1e9:+.3f} bn")
            print(f"    puts     : ${r['put_gex']/1e9:+.3f} bn")
            print(f"  gamma flip : {r['flip']:.2f}" if r['flip'] else "  gamma flip : n/a")
            print(f"  REGIME     : {r['regime']}")
        except Exception as e:
            print(f"{t}: failed - {type(e).__name__}: {e}")


# --------------------------------------------------------------------------- export
def mt5_files_dirs():
    """Locate MetaTrader Files folders so the indicator can read the regime."""
    import glob, os
    base = os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal")
    out = []
    common = os.path.join(base, "Common", "Files")
    if os.path.isdir(common): out.append(common)
    for d in glob.glob(os.path.join(base, "*", "MQL5", "Files")):
        out.append(d)
    return out

def export_regime(tickers=("SPY",), filename="gex_regime.csv", extra_dirs=()):
    """Write ticker,iso_utc,gex for MIM_GEX.mq5 to read."""
    import os, csv
    rows = []
    for t in tickers:
        try:
            r = fetch_gex(t)
            rows.append([r["ticker"], dt.datetime.now(dt.timezone.utc).strftime("%Y.%m.%d %H:%M"),
                         f"{r['gex']:.0f}", f"{r['spot']:.4f}",
                         f"{r['flip']:.4f}" if r["flip"] else "", r["regime"]])
            print(f"  {t}: GEX ${r['gex']/1e9:+.3f} bn -> {r['regime']}")
        except Exception as e:
            print(f"  {t}: FAILED {type(e).__name__}: {e}")
    if not rows: print("nothing to export"); return []
    written = []
    for d in list(mt5_files_dirs()) + list(extra_dirs):
        try:
            p = os.path.join(d, filename)
            with open(p, "w", newline="", encoding="ascii") as f:
                w = csv.writer(f)
                w.writerow(["ticker", "utc", "gex", "spot", "flip", "regime"])
                w.writerows(rows)
            written.append(p)
        except Exception as e:
            print(f"  ! could not write {d}: {e}")
    for p in written: print(f"  wrote {p}")
    return written
