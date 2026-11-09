# MomoRider 4G/4R — strategy research

**Nothing in `../indicators/` was modified.** This folder is entirely new.

---

## The verdict first

I mechanised 4G/4R exactly as reconstructed and tested it on **12 Bybit perps, 2024-01 → 2026-08, 3,161 signals on 30m**, with realistic costs. Then I tried to improve it with four research-backed techniques.

**It does not have a reliable, transferable edge after costs.** The core reason is upstream of any exit or filter design:

> **The 4G/4R signal does not significantly predict direction.**

Sign-adjusted forward return on real prices after every signal, pooled over all 12 markets:

| horizon | mean move | t | p |
|---|---|---|---|
| +8 bars | +0.035% | 1.15 | 0.249 |
| +16 bars | +0.003% | 0.05 | **0.957** |
| +32 bars | −0.052% | −0.84 | 0.404 |
| +48 bars | +0.117% | 1.56 | 0.118 |
| +96 bars | +0.187% | 1.78 | 0.075 |

A round trip costs **~0.14%** (Bybit taker + slippage). So even the best horizon barely clears its own transaction cost, and it isn't statistically significant at 5%. Per-symbol the signs are inconsistent — BTC/BNB/APT positive, SOL/LINK/SUI negative.

**Deflated Sharpe Ratio** ([Bailey & López de Prado 2014](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)), correcting for the 33 configurations I actually tried:

| | Sharpe/trade | SR₀ (luckiest of 33 trials) | **DSR** |
|---|---|---|---|
| Tuning symbols | +0.0267 | 0.1243 | **0.001** |
| 8 unseen symbols | +0.0119 | 0.1243 | **0.000** |

DSR is the probability the edge is real given how many things I tried. >0.95 is credible. This is ~0. The observed Sharpe is *below* what the luckiest of 33 random trials would produce.

**This does not mean Jason isn't making money.** It means the edge is not in the *visible mechanical rules*. He trades discretionarily, on 4–5 indicators, choosing which setups to take. That selection is the part I cannot see and could not reproduce.

---

## Your Level 2 / Level 3 question — the definitive answer

**You cannot use L2 or L3 data in Pine Script. Not on any plan.** There is no order-book, depth, or DOM access, and no API for it. Anything claiming to be "L2" in a Pine script is fabricated.

What does exist, and what I found while checking:

| capability | status for you |
|---|---|
| Order book / depth / DOM / L2 / L3 | **Does not exist in Pine at all** |
| `request.footprint()` — tick bid/ask volume, delta, imbalance per price level | Exists (added **March 2026**) but requires **Premium or Ultimate**. You are on Free. |
| `request.security_lower_tf()` — intrabar data, lets you build a volume-delta proxy | Works on Free, but intrabar depth is plan-limited |
| **Bulk Volume Classification** — order-flow toxicity from OHLCV alone | **Works on any plan.** Implemented and tested. |

BVC is the honest substitute. [Easley, López de Prado & O'Hara](https://cfr.ivo-welch.org/published/papers/easley-prado-hara.pdf) designed it precisely to recover order-flow information without trade-level classification:

```
buy volume  V_B = V · Φ( ΔP / σ_ΔP )
sell volume V_S = V − V_B
VPIN_t      = (1/W) · Σ |V_S − V_B| / V
```

I implemented it in both the Python harness and the Pine strategy. **It did not help** — details below. So the answer to "use L2 if you need to" is: you can't, I used the best legitimate substitute, and it wasn't the missing piece.

---

## What I tested, and what each thing did

### 1. Exit design — the one change that genuinely helped

Cost per trade in **R** scales as `1 / stop-distance`. With a tight stop the fee is a huge fraction of the risk unit:

| stop | risk as % of price | round-trip cost in R |
|---|---|---|
| 1.0 × ATR | 0.45% | **0.315 R** |
| 1.5 × ATR | 0.67% | 0.210 R |
| 4.0 × ATR | 2.23% | **0.063 R** |

So tight stops mathematically cannot work here. Widening the stop and letting winners run (the forward-return table says the edge, such as it is, appears at 48–96 bars — not 8–16) moved the pooled result from **−0.085 R / PF 0.87** to **+0.024 R / PF 1.04**. That is a real, mechanical, non-fitted improvement, and it is reflected in the strategy defaults.

### 2. Filters — looked great in-sample, all failed out-of-sample

Tested one at a time on 4 tuning symbols, then validated on 8 symbols never used in any sweep:

| filter | effect on tuning symbols | verdict |
|---|---|---|
| ADX ≥ 20 | **+0.060 R** (best single filter) | sweep was **non-monotonic** (18→+0.077, 20→+0.130, 22→+0.112, 25→+0.083) — a lucky peak |
| VPIN ≤ trailing median | +0.078 R, **monotonic** as tightened | monotonic looked promising, still failed holdout |
| HTF trend (EMA200) | **−0.015 R** | hurts — 4G/4R is already ribbon-aligned, so it's redundant |
| BVC flow agrees with side | **−0.024 R** | **near-vacuous**: 4G requires a green close, which mechanically implies positive delta. Flow already agreed on **81–90%** of signals. |

Final holdout test of the best combination (ADX ≥ 20 + VPIN ≤ trailing p50):

| | n | net R | PF |
|---|---|---|---|
| Tuning symbols | 372 | **+0.156** | 1.28 |
| **8 unseen symbols** | 701 | **+0.006** | 1.01 |
| In-sample 2024–25 | 805 | +0.078 | 1.14 |
| **Out-of-sample 2026** | 268 | **−0.002** | 1.00 |
| Unseen symbols, **no filters at all** | 2125 | **+0.017** | 1.03 |

The filtered version scored **worse on unseen markets than no filter at all**. That is the definition of overfitting, and it is why both filters ship **off by default**.

*(Note: my first VPIN test had a lookahead bug — a full-sample percentile. Fixed to a trailing, past-only percentile before these numbers were produced.)*

### 3. Meta-labeling — also failed

[López de Prado's meta-labeling](https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/) is the right tool for exactly this problem: keep 4G/4R as the high-recall primary signal, train a secondary model to decide *whether to take* each one. It is the formal version of the discretion Jason applies.

Trained a gradient-boosted classifier on 13 causal features (momentum, ADX, ATR/price, VPIN, BVC delta, ribbon distance and slope, trend deviation, volume ratio, candle body, hour, side, signal gap), on tuning symbols in 2024–25 only.

- In-sample AUC **0.923** — memorised.
- Unseen symbols, by probability threshold: **+0.018 → +0.006 → +0.072 → −0.061**. Non-monotonic and unstable.

A high in-sample AUC with unstable out-of-sample results is the textbook signature of a model that learned noise. With only 808 training signals and 13 features, that is expected.

### 4. Volatility-scaled sizing — kept, on principle

Position size = risk$ / stop distance, so a stop-out always costs the same fraction of equity regardless of the instrument's volatility. This is what makes one setting transferable across markets ([Moskowitz, Ooi & Pedersen 2012](https://www.sciencedirect.com/science/article/pii/S0304405X11002613); [Harvey et al.](https://www.cmegroup.com/education/files/improving-time-series-momentum-strategies.pdf)). It doesn't create edge — it makes results comparable and stops one wild market dominating the P&L. Retained in the strategy.

---

## Two findings you can act on immediately

**1. Trade this on 30m, not 15m.** The same rules on 15m are clearly negative:

| timeframe | n | win% | net R | PF |
|---|---|---|---|---|
| 30m | 3,161 | 38.8% | **+0.024** | 1.04 |
| 15m | 3,400 | 33.7% | **−0.127** | 0.80 |

On 15m only XRP was positive. The moves are smaller but the fees are identical, so cost eats proportionally more.

**2. Fees are the whole game here.** Break-even is at 0.10% per side:

| cost/side | round trip | net R | PF |
|---|---|---|---|
| 0.000% | 0.00% | +0.078 | 1.15 |
| 0.020% (maker/limit) | 0.04% | **+0.063** | 1.11 |
| 0.055% (Bybit taker) | 0.11% | +0.039 | 1.07 |
| 0.070% (taker + slip) | 0.14% | +0.024 | 1.04 |
| 0.100% | 0.20% | **0.000** | 1.00 |

Moving from taker to maker entries roughly **triples** the net edge. That is a bigger lever than every filter I tested combined. **Caveat:** resting a limit order introduces adverse selection — you only get filled when price comes to you, which is disproportionately when you're wrong. The table is an upper bound, not a promise.

---

## If you want to keep going, here is where the odds are best

Ranked by expected payoff, given what the evidence showed:

1. **Reduce cost, not signal count.** Maker entries, and fewer/longer trades. The edge is ~0.08 R gross; anything that shaves 0.02 R of cost is worth more than any filter I found.
2. **Find the discretion.** The mechanical rules have no edge but Jason presumably does. The highest-value thing you could give me is a log of the setups *he took vs skipped*. That turns meta-labeling from unsupervised guessing into a supervised problem with real labels — and it's the one experiment here that failed only for lack of data, not for lack of merit.
3. **Test on the markets he actually shows.** He runs this on NDX 15m and SP500 5m too. Index futures have different cost and trend structure than crypto perps; the setup may transfer better where trends are more persistent. I could not test these — no free historical feed.
4. **Don't chase the filters.** ADX and VPIN both looked good and both failed. If you re-test them, use the holdout discipline in `backtest/validate.py`, not in-sample results.

---

## Files

| file | what it is |
|---|---|
| `MomoRider_Strategy.pine` | The Pine v5 strategy. Entries identical to the verified indicator; ATR triple-barrier exits, volatility-scaled sizing, both filters off by default. Honest stats in the header. |
| `backtest/core.py` | Signal engine — a faithful port of `5_JS_MomoRider_Momentum_v2.pine`, plus BVC/VPIN, ADX, ATR |
| `backtest/engine.py` | Backtester. HA closes are never treated as tradable; all fills/stops on real OHLC |
| `backtest/validate.py` | Symbol holdout + time holdout + deflated Sharpe |
| `backtest/meta.py` | Meta-labeling experiment |
| `backtest/signif.py` | The root-cause significance test |
| `backtest/final.py` | Cost sensitivity, DSR, 15m comparison |
| `data/` | 12 Bybit perps, 30m from 2024-01 and 15m from 2025-01 |

Reproduce everything: `cd backtest && python signif.py && python validate.py && python final.py`

---

## Research consulted

- **Bailey & López de Prado (2014)** — [The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551). Used to correct my own results for the 33 trials I ran. This is what turned "PF 1.28 on the tuning set" into "DSR 0.001".
- **Easley, López de Prado & O'Hara** — [Bulk Volume Classification / VPIN](https://cfr.ivo-welch.org/published/papers/easley-prado-hara.pdf). The order-flow substitute when L2 is unavailable. Implemented; didn't help here.
- **López de Prado (2018), *Advances in Financial Machine Learning*** — [triple-barrier labeling](https://hudsonthames.org/does-meta-labeling-add-to-signal-efficacy-triple-barrier-method/) (used for exits) and meta-labeling (tested).
- **Moskowitz, Ooi & Pedersen (2012)** — [Time Series Momentum](https://www.sciencedirect.com/science/article/pii/S0304405X11002613). Volatility-scaled sizing for cross-market transfer.
- **Cont, Kukanov & Stoikov (2014)** — [The Price Impact of Order Book Events](https://academic.oup.com/jfec/article-abstract/12/1/47/816163). Confirms OFI is the informative microstructure variable — and that it needs the book, which Pine cannot give you.
- **Combinatorial purged cross-validation** — [Arian, Norouzi & Seco](https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID4686376_code4361537.pdf?abstractid=4686376&mirid=1). Walk-forward tests one path and overfits easily; I used symbol + time holdout plus DSR for the same reason.
