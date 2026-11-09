"""
Backtest engine.

Realism rules that matter and are easy to get wrong:
  * Heikin-Ashi closes are NOT tradable. Signals are computed on HA, but every
    fill, stop and target uses the REAL OHLC.
  * Entry is at the real close of the signal bar (bar-close execution, taker).
  * Stops/targets are checked against the real high/low of each subsequent bar.
    If a bar touches BOTH, the stop is assumed first (conservative).
  * Costs are charged on both legs.
"""
import numpy as np
from core import (load, heikin, ema, atr, adx, momentum, signals,
                  bvc_delta, vpin, JS_PARAMS)

COST_PER_SIDE = 0.0007        # 0.055% Bybit taker + ~0.015% slippage

class Cfg:
    def __init__(self, sl_atr=1.5, tp_atr=3.0, max_bars=48, risk=0.01,
                 use_ribbon_stop=False, f_htf=False, f_adx=0.0,
                 f_flow=False, f_vpin_max=0.0, atr_len=14, trail=False):
        self.sl_atr = sl_atr; self.tp_atr = tp_atr; self.max_bars = max_bars
        self.risk = risk; self.use_ribbon_stop = use_ribbon_stop
        self.f_htf = f_htf; self.f_adx = f_adx; self.f_flow = f_flow
        self.f_vpin_max = f_vpin_max; self.atr_len = atr_len; self.trail = trail

def run(d, cfg, p=JS_PARAMS):
    o, h, l, c, v = d["o"], d["h"], d["l"], d["c"], d["v"]
    sig, aux = signals(d, p)
    n = len(c)
    A = atr(h, l, c, cfg.atr_len)
    AD = adx(h, l, c, 14)
    trend = ema(aux["hc"], 200)
    flow = bvc_delta(c, v, 50)
    tox = vpin(c, v, 50)
    ribTop, ribBot = aux["ribTop"], aux["ribBot"]

    trades = []
    for i, side in sig:
        if i + 1 >= n: continue
        if A[i] <= 0 or not np.isfinite(A[i]): continue
        # ---- filters -------------------------------------------------------
        if cfg.f_htf:
            if side == "L" and not (c[i] > trend[i]): continue
            if side == "S" and not (c[i] < trend[i]): continue
        if cfg.f_adx > 0 and not (AD[i] >= cfg.f_adx): continue
        if cfg.f_flow:
            if side == "L" and flow[i] <= 0: continue
            if side == "S" and flow[i] >= 0: continue
        if cfg.f_vpin_max > 0 and tox[i] > cfg.f_vpin_max: continue

        # ---- levels --------------------------------------------------------
        entry = c[i]
        if cfg.use_ribbon_stop:
            stop = ribBot[i] - 0.25 * A[i] if side == "L" else ribTop[i] + 0.25 * A[i]
            if side == "L" and stop >= entry: continue
            if side == "S" and stop <= entry: continue
        else:
            stop = entry - cfg.sl_atr * A[i] if side == "L" else entry + cfg.sl_atr * A[i]
        risk_px = abs(entry - stop)
        if risk_px <= 0: continue
        target = entry + cfg.tp_atr * A[i] if side == "L" else entry - cfg.tp_atr * A[i]

        # ---- walk forward to an exit ----------------------------------------
        exit_px, exit_i, why = None, None, None
        st = stop
        for j in range(i + 1, min(n, i + 1 + cfg.max_bars)):
            if side == "L":
                if l[j] <= st: exit_px, exit_i, why = st, j, "sl"; break
                if h[j] >= target: exit_px, exit_i, why = target, j, "tp"; break
                if cfg.trail: st = max(st, c[j] - cfg.sl_atr * A[j])
            else:
                if h[j] >= st: exit_px, exit_i, why = st, j, "sl"; break
                if l[j] <= target: exit_px, exit_i, why = target, j, "tp"; break
                if cfg.trail: st = min(st, c[j] + cfg.sl_atr * A[j])
        if exit_px is None:
            exit_i = min(n - 1, i + cfg.max_bars); exit_px = c[exit_i]; why = "time"

        # ---- P&L, volatility-scaled size -----------------------------------
        # size so that a stop-out loses exactly `risk` of equity -> R-multiples
        gross = (exit_px - entry) if side == "L" else (entry - exit_px)
        r_mult = gross / risk_px
        cost_r = COST_PER_SIDE * (entry + exit_px) / risk_px    # both legs, in R
        trades.append(dict(i=i, exit_i=exit_i, side=side, why=why,
                           entry=entry, exit=exit_px, risk_px=risk_px,
                           R=r_mult - cost_r, bars=exit_i - i, t=d["t"][i]))
    return trades

# --------------------------------------------------------------------------- stats
def stats(trades, risk=0.01, bars_per_year=None):
    if not trades: return dict(n=0)
    R = np.array([t["R"] for t in trades])
    ret = R * risk                                   # equity fraction per trade
    eq = np.cumprod(1.0 + ret)
    wins = R > 0
    pf_num = R[wins].sum(); pf_den = -R[~wins].sum()
    dd = 1.0 - eq / np.maximum.accumulate(eq)
    out = dict(n=len(R), winrate=float(wins.mean()), meanR=float(R.mean()),
               medR=float(np.median(R)), totR=float(R.sum()),
               pf=float(pf_num / pf_den) if pf_den > 0 else np.inf,
               maxdd=float(dd.max()), final=float(eq[-1]))
    # per-trade Sharpe, annualised by observed trade frequency
    if R.std(ddof=1) > 0:
        out["sharpe_trade"] = float(R.mean() / R.std(ddof=1))
        if bars_per_year is not None and len(trades) > 1:
            span = trades[-1]["t"] - trades[0]["t"]
            yrs = span / (365.25 * 24 * 3600 * 1000)
            if yrs > 0:
                tpy = len(R) / yrs
                out["sharpe_ann"] = float(out["sharpe_trade"] * np.sqrt(tpy))
                out["trades_per_year"] = float(tpy)
    else:
        out["sharpe_trade"] = 0.0
    return out
