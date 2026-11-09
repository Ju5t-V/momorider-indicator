"""
MomoRider strategy — shared engine.

The 4G/4R entry logic here is a faithful port of 5_JS_MomoRider_Momentum_v2.pine
(same oscillator, same zig-zag structure labels, same four conditions). It was
validated against the original JS charts: on the BTC 30m window in the
2026-08-19 recording it reproduces Jason's label sequence LL,HH,HL,HH,HL exactly.

Everything ABOVE the entry (exits, sizing, filters) is new and is what this
folder is testing.
"""
import json, os
import numpy as np
import datetime as dt
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import lfilter
from scipy.stats import norm

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")

# --------------------------------------------------------------------------- data
def load(sym, tf):
    k = json.load(open(os.path.join(DATA, f"{sym}_{tf}.json")))
    a = np.array([[float(x) for x in r[:6]] for r in k])
    return dict(t=a[:, 0].astype(np.int64), o=a[:, 1], h=a[:, 2],
                l=a[:, 3], c=a[:, 4], v=a[:, 5])

def heikin(o, h, l, c):
    hc = (o + h + l + c) / 4.0
    ho = np.empty_like(hc); ho[0] = (o[0] + c[0]) / 2.0
    for i in range(1, len(hc)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2.0
    return ho, np.maximum.reduce([h, ho, hc]), np.minimum.reduce([l, ho, hc]), hc

# --------------------------------------------------------------------------- ta
def ema(x, n):
    a = 2.0 / (n + 1.0)
    return lfilter([a], [1.0, -(1.0 - a)], x, zi=np.array([(1.0 - a) * x[0]]))[0]

def rma(x, n):
    a = 1.0 / n
    return lfilter([a], [1.0, -(1.0 - a)], x, zi=np.array([(1.0 - a) * x[0]]))[0]

def stoch(x, n):
    n = max(2, int(n))
    pad = np.concatenate([np.full(n - 1, x[0]), x])
    w = sliding_window_view(pad, n)
    hi, lo = w.max(1), w.min(1)
    rng = hi - lo
    return np.where(rng <= 0, 50.0, 100.0 * (x - lo) / np.where(rng <= 0, 1.0, rng))

def smooth(v, f):
    return lfilter([f], [1.0, -(1.0 - f)], v, zi=np.array([(1.0 - f) * v[0]]))[0]

def true_range(h, l, c):
    pc = np.concatenate([[c[0]], c[:-1]])
    return np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])

def atr(h, l, c, n=14):
    return rma(true_range(h, l, c), n)

def adx(h, l, c, n=14):
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    plus  = np.where((up > dn) & (up > 0), up, 0.0)
    minus = np.where((dn > up) & (dn > 0), dn, 0.0)
    tr = rma(true_range(h, l, c), n)
    tr = np.where(tr <= 0, 1e-12, tr)
    pdi = 100.0 * rma(plus, n) / tr
    mdi = 100.0 * rma(minus, n) / tr
    s = pdi + mdi
    dx = 100.0 * np.abs(pdi - mdi) / np.where(s <= 0, 1e-12, s)
    return rma(dx, n)

# --------------------------------------------------------------------------- oscillator
JS_PARAMS = (39, 14, 0.72, 26, 0.67)   # the verified defaults — do not tune these

def momentum(hh, hl, p=JS_PARAMS):
    dtl, c1, s1, c2, s2 = p
    src = (hh + hl) / 2.0
    d = src - ema(src, int(dtl))
    return smooth(stoch(smooth(stoch(d, c1), s1), c2), s2)

# --------------------------------------------------------------------------- structure labels
def pivots(o, L):
    ph = np.zeros(len(o), bool); pl = np.zeros(len(o), bool)
    for i in range(L, len(o) - L):
        w = o[i - L:i + L + 1]
        if o[i] == w.max() and w.argmax() == L: ph[i] = True
        if o[i] == w.min() and w.argmin() == L: pl[i] = True
    return ph, pl

def structure(o, px, L=3, minSep=4):
    """Zig-zag pivots on the OSCILLATOR, named by comparing PRICE at consecutive
    same-type pivots. Returns (confirm_bar, pivot_bar, kind, osc_at_pivot)."""
    ph, pl = pivots(o, L)
    lastType, lastBar, lastOsc = 0, -10**9, 0.0
    curHi = curLo = refHi = refLo = np.nan
    ev = []
    for i in range(len(o)):
        if not (ph[i] or pl[i]): continue
        isHigh = ph[i]
        same = lastType == (1 if isHigh else -1)
        better = same and (o[i] > lastOsc if isHigh else o[i] < lastOsc)
        far = lastBar < 0 or (i - lastBar) >= minSep
        if not ((not same and far) or better): continue
        if better and ev: ev.pop()          # replaces the previous same-type pivot
        if isHigh:
            if not better: refHi = curHi
            kind = "HH" if (np.isnan(refHi) or px[i] >= refHi) else "LH"
            curHi = px[i]
        else:
            if not better: refLo = curLo
            kind = "HL" if (np.isnan(refLo) or px[i] >= refLo) else "LL"
            curLo = px[i]
        ev.append((i + L, i, kind, o[i]))
        lastType = 1 if isHigh else -1; lastBar = i; lastOsc = o[i]
    return ev

# --------------------------------------------------------------------------- order flow (no L2 needed)
def bvc_delta(c, v, win=50):
    """Bulk Volume Classification (Easley, Lopez de Prado & O'Hara).
    buy_frac = Phi(dP / sigma_dP);  returns signed delta fraction in [-1, 1]."""
    dp = np.diff(c, prepend=c[0])
    sd = np.full(len(dp), np.nan)
    pad = np.concatenate([np.full(win - 1, dp[0]), dp])
    sd = sliding_window_view(pad, win).std(1)
    sd = np.where(sd <= 0, 1e-12, sd)
    buy_frac = norm.cdf(dp / sd)
    return 2.0 * buy_frac - 1.0            # +1 all buy, -1 all sell

def vpin(c, v, win=50):
    """Order-flow toxicity from OHLCV alone: rolling mean of |Vs-Vb|/V."""
    d = np.abs(bvc_delta(c, v, win))
    pad = np.concatenate([np.full(win - 1, d[0]), d])
    return sliding_window_view(pad, win).mean(1)

# --------------------------------------------------------------------------- 4G/4R entries
def signals(d, p=JS_PARAMS, ribFast=26, ribSlow=52, zLo=10.0, zHi=90.0,
            win=5, pivLen=3, minSep=4):
    """Returns list of (bar_index, 'L'|'S') at bar close. Faithful to the Pine."""
    ho, hh, hl, hc = heikin(d["o"], d["h"], d["l"], d["c"])
    osc = momentum(hh, hl, p)
    ef, es = ema(hc, ribFast), ema(hc, ribSlow)
    ribTop, ribBot = np.maximum(ef, es), np.minimum(ef, es)
    bull = ef > es
    red, green = hc < ho, hc >= ho

    ev = structure(osc, hc, pivLen, minSep)
    n = len(osc)
    bullS = np.zeros(n, bool); bearS = np.zeros(n, bool); sOsc = np.full(n, np.nan)
    for cb, pb, k, ov in ev:
        if cb >= n: continue
        if k in ("HH", "HL"): bullS[cb] = True
        else: bearS[cb] = True
        sOsc[cb] = ov

    oneG = bull & red & (hl <= ribTop) & (hc > ribBot)
    oneR = (~bull) & green & (hh >= ribBot) & (hc < ribTop)

    out = []
    for i in range(60, n - 1):
        w = slice(max(0, i - win), i + 1)
        g = np.where(oneG[w])[0]
        if len(g):
            b1 = max(0, i - win) + g[-1]
            if i == b1 + 1 and green[i] and osc[w].min() <= zLo \
               and (bullS[w] & (sOsc[w] <= zLo + 15)).any():
                out.append((i, "L"))
        r = np.where(oneR[w])[0]
        if len(r):
            b1 = max(0, i - win) + r[-1]
            if i == b1 + 1 and red[i] and osc[w].max() >= zHi \
               and (bearS[w] & (sOsc[w] >= zHi - 15)).any():
                out.append((i, "S"))
    return out, dict(osc=osc, ribTop=ribTop, ribBot=ribBot, bull=bull,
                     ho=ho, hh=hh, hl=hl, hc=hc)
