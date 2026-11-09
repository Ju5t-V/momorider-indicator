"""
Meta-labeling (Lopez de Prado, AFML 2018).

Primary model  = the 4G/4R setup. High recall, low precision - it fires often and
                 is right slightly more than chance before costs.
Secondary model= a classifier that looks at the state of the market AT the signal
                 and decides whether to TAKE the trade. It never changes the side,
                 only whether to act. This is the formal version of the discretion
                 a human applies when they skip a setup that "looks wrong".

Trained on DEV symbols, 2024-2025 only. Tested on:
  * the 8 HOLDOUT symbols (never used in any tuning), and
  * DEV symbols in 2026 (unseen time)
"""
import numpy as np, os, sys, datetime as dt
from scipy.stats import norm, skew, kurtosis
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core import (load, signals, atr, adx, ema, bvc_delta, vpin, heikin)
from engine import Cfg, run, COST_PER_SIDE
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

DEV     = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]
HOLDOUT = ["DOGEUSDT", "BNBUSDT", "LINKUSDT", "AVAXUSDT",
           "ADAUSDT", "LTCUSDT", "SUIUSDT", "APTUSDT"]
SPLIT   = int(dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000)
BASE    = dict(sl_atr=4.0, tp_atr=12.0, max_bars=96)   # no discretionary filters

FEATS = ["osc", "adx", "atrp", "vpin", "flow", "rib_dist", "rib_slope",
         "trend_dev", "vol_ratio", "body", "hour", "side", "gap_bars"]

def featurise(sym):
    d = load(sym, "30")
    tr = run(d, Cfg(**BASE))
    if not tr: return None, None, None
    o, h, l, c, v = d["o"], d["h"], d["l"], d["c"], d["v"]
    ho, hh, hl, hc = heikin(o, h, l, c)
    A = atr(h, l, c, 14); AD = adx(h, l, c, 14)
    ef, es = ema(hc, 26), ema(hc, 52)
    ribTop, ribBot = np.maximum(ef, es), np.minimum(ef, es)
    tox = vpin(c, v, 50); fl = bvc_delta(c, v, 50)
    tr200 = ema(hc, 200)
    vma = ema(v, 20)
    from core import momentum
    osc = momentum(hh, hl)
    slope = np.diff(ef, prepend=ef[0]) / np.where(A <= 0, 1e-12, A)

    X, y, meta = [], [], []
    prev_i = -10**9
    for t in tr:
        i = t["i"]; side = 1.0 if t["side"] == "L" else -1.0
        rib = ribBot[i] if side > 0 else ribTop[i]
        rng = max(1e-12, hh[i] - hl[i])
        X.append([osc[i], AD[i], A[i] / c[i], tox[i], fl[i] * side,
                  (c[i] - rib) / max(1e-12, A[i]) * side, slope[i] * side,
                  (c[i] / tr200[i] - 1.0) * side,
                  v[i] / max(1e-12, vma[i]), abs(hc[i] - ho[i]) / rng,
                  float(dt.datetime.fromtimestamp(d["t"][i] / 1000, dt.timezone.utc).hour),
                  side, min(500, i - prev_i)])
        y.append(1 if t["R"] > 0 else 0)
        meta.append(t)
        prev_i = i
    return np.array(X, float), np.array(y), meta

def perf(trades, label):
    if len(trades) < 10:
        print(f"{label:40} n={len(trades):4d}  (too few)"); return None
    R = np.array([t["R"] for t in trades]); w = R > 0
    pf = R[w].sum() / max(1e-9, -R[~w].sum())
    sh = R.mean() / R.std(ddof=1) if R.std(ddof=1) > 0 else 0
    print(f"{label:40} n={len(R):4d} win={100*w.mean():5.1f}% net={R.mean():+.3f} PF={pf:5.2f} sh/t={sh:+.3f}")
    return dict(R=R, sh=sh, net=R.mean(), pf=pf, n=len(R))

if __name__ == "__main__":
    print("building features...")
    data = {}
    for s in DEV + HOLDOUT:
        X, y, m = featurise(s)
        if X is not None: data[s] = (X, y, m)
    print(f"  {len(data)} symbols, {sum(len(v[1]) for v in data.values())} primary signals\n")

    # ---- train on DEV, 2024-2025 only -------------------------------------
    Xtr, ytr = [], []
    for s in DEV:
        X, y, m = data[s]
        k = np.array([t["t"] < SPLIT for t in m])
        Xtr.append(X[k]); ytr.append(y[k])
    Xtr = np.vstack(Xtr); ytr = np.concatenate(ytr)
    print(f"training rows {len(ytr)}, base rate {100*ytr.mean():.1f}% winners")

    clf = HistGradientBoostingClassifier(max_depth=3, max_iter=200,
                                         learning_rate=0.05, l2_regularization=1.0,
                                         min_samples_leaf=40, random_state=0)
    clf.fit(Xtr, ytr)
    print(f"in-sample AUC {roc_auc_score(ytr, clf.predict_proba(Xtr)[:,1]):.3f}")

    # ---- evaluate ---------------------------------------------------------
    for thr in (0.0, 0.45, 0.50, 0.55, 0.60):
        print(f"\n===== meta-label threshold p >= {thr:.2f} =====")
        for grp, syms, tfilt, nm in (
                ("DEV",     DEV,     lambda t: t["t"] >= SPLIT, "DEV 2026 (unseen time)"),
                ("HOLD",    HOLDOUT, lambda t: True,            "HOLDOUT symbols (all time)"),
                ("HOLDOOS", HOLDOUT, lambda t: t["t"] >= SPLIT, "HOLDOUT symbols, 2026 only")):
            sel, allr = [], []
            for s in syms:
                X, y, m = data[s]
                p = clf.predict_proba(X)[:, 1]
                for j, t in enumerate(m):
                    if not tfilt(t): continue
                    allr.append(t)
                    if p[j] >= thr: sel.append(t)
            if thr == 0.0: perf(allr, f"  {nm} [no meta filter]")
            else:          perf(sel,  f"  {nm} [meta]")
