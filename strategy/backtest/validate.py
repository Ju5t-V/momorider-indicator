"""
Honest validation.

Three separate guards against fooling ourselves:
  1. SYMBOL holdout  - tuned only on BTC/ETH/SOL/XRP; 8 other markets never touched.
  2. TIME holdout    - tuned on 2024-2025; 2026 held back.
  3. Deflated Sharpe - corrects the reported Sharpe for the number of trials run
                       (Bailey & Lopez de Prado 2014), using the actual spread of
                       Sharpes across those trials.

Also fixes a lookahead bug: the VPIN threshold is a TRAILING rolling percentile,
computed only from bars before the signal - never the full sample.
"""
import numpy as np, os, sys, datetime as dt
from scipy.stats import norm, skew, kurtosis
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import load, vpin
from engine import Cfg, run, COST_PER_SIDE

DEV     = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
HOLDOUT = ["DOGEUSDT", "BNBUSDT", "LINKUSDT", "AVAXUSDT",
           "ADAUSDT", "LTCUSDT", "SUIUSDT", "APTUSDT"]
SPLIT   = int(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)

# the candidate, chosen from the DEV sweeps (deliberately NOT the sweep maximum)
CAND = dict(sl_atr=4.0, tp_atr=12.0, max_bars=96, f_adx=20.0)
VPIN_PCT   = 50      # keep signals whose toxicity is below its trailing median
VPIN_LOOK  = 2000    # trailing window for that percentile (~6 weeks on 30m)

def rolling_pct_threshold(x, look, pct):
    """Causal: threshold at bar i uses only x[:i]."""
    out = np.full(len(x), np.inf)
    for i in range(look, len(x)):
        out[i] = np.percentile(x[i - look:i], pct)
    return out

def trades_for(sym, tf="30", cfg_kw=None, use_vpin=True):
    d = load(sym, tf)
    cfg = Cfg(**(cfg_kw or CAND))
    tr = run(d, cfg)
    if use_vpin:
        tox = vpin(d["c"], d["v"], 50)
        thr = rolling_pct_threshold(tox, VPIN_LOOK, VPIN_PCT)
        tr = [t for t in tr if tox[t["i"]] <= thr[t["i"]]]
    return tr

def summarise(tr, label):
    if len(tr) < 10:
        print(f"{label:34} n={len(tr):4d}   (too few to judge)"); return None
    R = np.array([t["R"] for t in tr]); w = R > 0
    cost = np.array([2 * COST_PER_SIDE * t["entry"] / t["risk_px"] for t in tr])
    sh = R.mean() / R.std(ddof=1) if R.std(ddof=1) > 0 else 0.0
    pf = R[w].sum() / max(1e-9, -R[~w].sum())
    eq = np.cumprod(1 + R * 0.01)
    dd = (1 - eq / np.maximum.accumulate(eq)).max()
    print(f"{label:34} n={len(tr):4d} win={100*w.mean():5.1f}% gross={(R+cost).mean():+.3f} "
          f"net={R.mean():+.3f} PF={pf:5.2f} sh/t={sh:+.3f} maxDD={100*dd:5.1f}%")
    return dict(R=R, sh=sh, pf=pf, n=len(R), net=R.mean())

def deflated_sharpe(R, sharpes_across_trials, N_trials):
    """Bailey & Lopez de Prado (2014). Returns (SR0, DSR probability)."""
    T = len(R)
    sr = R.mean() / R.std(ddof=1)
    V = np.var(sharpes_across_trials, ddof=1)
    g = 0.5772156649
    sr0 = np.sqrt(V) * ((1 - g) * norm.ppf(1 - 1.0 / N_trials)
                        + g * norm.ppf(1 - 1.0 / (N_trials * np.e)))
    g3 = skew(R); g4 = kurtosis(R, fisher=False)
    denom = np.sqrt(max(1e-12, 1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2))
    z = (sr - sr0) * np.sqrt(T - 1) / denom
    return sr, sr0, float(norm.cdf(z))

if __name__ == "__main__":
    print("=" * 100)
    print("CANDIDATE:", CAND, f"+ VPIN <= trailing p{VPIN_PCT}")
    print("=" * 100)

    print("\n--- 1. DEV symbols (these were tuned on - expect them to look good) ---")
    dev = []
    for s in DEV:
        tr = trades_for(s); dev += tr; summarise(tr, f"  {s}")
    dsum = summarise(dev, "  DEV POOLED")

    print("\n--- 2. HOLDOUT symbols (never used in any sweep) ---")
    hold = []
    for s in HOLDOUT:
        tr = trades_for(s); hold += tr; summarise(tr, f"  {s}")
    hsum = summarise(hold, "  HOLDOUT POOLED")

    print("\n--- 3. TIME split (all 12 symbols) ---")
    allt = dev + hold
    summarise([t for t in allt if t["t"] < SPLIT],  "  in-sample  2024-2025")
    summarise([t for t in allt if t["t"] >= SPLIT], "  OUT-OF-SAMPLE 2026")

    print("\n--- 4. baseline for comparison: same exits, NO filters, holdout symbols ---")
    base = []
    for s in HOLDOUT:
        base += trades_for(s, cfg_kw=dict(sl_atr=4.0, tp_atr=12.0, max_bars=96), use_vpin=False)
    summarise(base, "  HOLDOUT no-filter")
