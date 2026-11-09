# MomoRider — reconstruction notes

## Which files to load

**Recommended on the free plan — two slots, all three panes:**

| Slot | File | Draws |
|---|---|---|
| 1 | `4_JS_Ribbon_Liquidity_Combined.pine` | ribbon + staircase **on the price chart**, volume histogram **in its own pane** |
| 2 | `2_JS_MomoRider_Momentum.pine` | momentum oscillator, HH/HL/LH/LL labels, 4G/4R signal + alert |

`#4` gets two panes out of one indicator slot by declaring itself `overlay=false` (so it owns
the lower pane for volume) and pushing the ribbon, staircase and 1G/1R markers up onto the
price chart with `force_overlay=true`.

**The separate versions**, if you ever have three slots or want them split:

| File | Pane | What it is |
|---|---|---|
| `1_JS_TrendRibbon_LiquidityHunter.pine` | price (overlay) | the two EMAs + the grey "staircase" |
| `3_JS_LiquidityHunter_Volume.pine` | separate | the volume / "where size traded and got trapped" pane |

`#4` = `#1` + `#3`. Don't load #4 together with #1 or #3 — you'll get everything twice.

There is also a fallback inside `#2` (*Liquidity volume → Show liquidity volume columns*)
that draws the volume as faint columns behind the oscillator. That was the workaround before
`#4` existed; with `#4` you no longer need it, so leave it off.

### One caveat on `#4`

`fill()` has no `force_overlay` parameter — its only arguments are
`color, title, editable, show_last, fillgaps` — so the shaded ribbon cannot be pushed to the
price pane from a pane script. The optional *Shade between the lines* setting uses
`plotcandle()` instead, which draws the band as blocks rather than one continuous fill.
It is **off by default**, because the original JS chart draws two plain lines with no shading
anyway.

Set the chart to **Heikin Ashi** (the original system runs on HA). If you ever run normal
candles, flip `Candle source` to `Force Heikin Ashi`.

---

## How this was worked out

Not guessed. The method was:

1. Pixel-extracted the plotted lines out of your screenshots/recording frames.
2. Pulled the **real OHLC for the exact same bars** from Bybit's public API
   (BTCUSDT.P 30m around 17–18 Aug 2026, SXTUSDT.P 15m around 19 Aug 2026).
3. Locked the bar alignment three independent ways — the Heikin-Ashi OHLC printed in the
   chart header (match error 0.08), the crosshair x-position, and a volume-histogram
   fingerprint (correlation 0.906). All three agreed.
4. Calibrated the price axis off the gridlines (validated: the staircase read 63464.6 vs the
   63,465.0 printed on the axis).
5. Fitted candidate formulas against the extracted curves.

## What was recovered

| Element | Result | Confidence |
|---|---|---|
| Fast ribbon EMA | **EMA(26) of Heikin-Ashi close** | **Exact.** 64,141.3 on BTC 30m and 0.007306 on SXT 15m — both reproduced to the last printed digit |
| Slow ribbon EMA | **EMA(52) of Heikin-Ashi close** | **Exact.** 63,853.7 and 0.007257 likewise |
| Staircase (grey step line) | **EMA(26) of Heikin-Ashi close, taken from a higher timeframe** | **Very high.** It steps every 8 bars on a 30m chart = a 4H anchor; 4H EMA(26) fit the 8 measured steps to a mean error of 1.4 points on a 63,000 instrument (sub-pixel) |
| Volume pane — **this is the real "JS Liquidity Hunter (20)"** | orange line = **SMA(volume, 20)**; bars go **orange at ≥2× that average, dark red at ≥4×**, otherwise teal/dusty-red by HA candle direction | **Exact.** SMA(20) reproduced the printed 1,334.1 uniquely (searched 4 MA types × lengths 2–120). The colour rule reproduced **61 of 61** bars, and the 2× boundary is clean — highest plain bar 1.98×, lowest orange 2.03× |
| Anchor timeframe | **user input** | BTC 30m wanted 4H, SXT 15m wanted 3H — same EMA length (26) both times, so the timeframe is a setting, not a formula. Default 4H |
| Zone bands | **green 90–100, red 0–10** | **Exact.** Measured identically on three separate charts |
| Line colour | green when ≤ 10, red when ≥ 90, orange between | **Exact.** This is your "the orange line turns green in the momentum red zone" = **2G** |
| HH/HL/LH/LL labels | pivots **on the oscillator**, forced to alternate high/low (a zigzag), then **named by comparing PRICE at consecutive same-type pivots** | **High.** Reproduces the observed label sequence LL → HH → HL → HH → HL exactly |
| Oscillator formula | double-smoothed stochastic of a detrended price series (Schaff/STC family) | **Close, not exact** — see below |

### The oscillator — the one honest gap

Family is certain (nothing else plateaus at 0/100 with that shape). Parameters are a fit:

```
src = (HA high + HA low) / 2
dt  = src − EMA(src, 39)
v1  = Stoch(dt, 14)          →  pf  = pf[1] + 0.72·(v1 − pf[1])
v3  = Stoch(pf, 26)          →  osc = osc[1] + 0.67·(v3 − osc[1])
```

Accuracy against the original, measured on 60 bars of BTCUSDT.P 30m:

- **correlation r = 0.986**, mean absolute error **4.0** on a 0–100 scale
- independently reproduced SXTUSDT.P 15m's printed **74.563** to within **0.01**

Consequence: label **positions land 1–3 bars later** than the original. The label
**types and their order are right**; the exact bar can differ slightly. All five parameters
are inputs — nudge `Smoothing factor #1/#2` up to make it faster.

---

## The 4G / 4R setup (as you described it)

Long (**4G**) — all four inside the `Setup window`:

1. **1G** — a red HA candle sitting above the bullish ribbon whose low reaches back and touches it
2. **2G** — momentum is in the red zone (≤ 10), i.e. the orange line has turned **green**
3. **3G** — an **HL or HH** label prints on that same green leg (momentum bottoms while price holds a higher low — the divergence tell)
4. **4G** — the candle immediately after the 1G red candle closes **green**

**4R** is the mirror: green candle into a bearish ribbon, momentum ≥ 90 (line red), an **LH or LL** on that leg, next candle closes red.

The signal fires once per setup, on bar close, and prints `4G`/`4R` in the momentum pane.

---

## Alerts

On indicator 2: *4G LONG setup complete*, *4R SHORT setup complete*, plus the individual
building blocks. The 4G/4R alert message carries side, symbol, timeframe, entry price,
the momentum reading, and **the ribbon level to lean your stop on**.

Indicator 1 adds: price crossing the staircase, ribbon flips, and 1G/1R touches.
Indicator 3 adds high-volume (≥2×) and extreme-volume (≥4×) alerts — the alert you already
had, *"JS Liquidity Hunter (20) Crossing 249.1"*, is a level-cross on **this** plot: 249.1 is
a volume figure on a 1-minute chart, and the "(20)" is its SMA length.

### Level 2 data — deliberately not included

You asked me to add it *only if* it would genuinely help. It would not, for two reasons:

1. **It is not possible.** Pine Script has no access to order-book / depth / DOM data on any
   TradingView plan. There is no API for it. Anything "L2" in a Pine alert would be fabricated.
2. **Even if it existed, it would not help this setup.** 4G/4R is a bar-close momentum-continuation
   entry on 15m–30m candles. Resting book depth at that horizon is dominated by spoofed and
   pulled liquidity and has very little predictive value. The microstructure input that *does*
   carry information at this horizon is aggressive taker flow (CVD), which is trade-tape data,
   not L2.

So the alert instead carries everything needed to execute immediately. If you want depth at the
moment of execution, read it in the Bybit DOM — the alert fires on bar close, which gives you
the time to.

---

# Second pass — what the 2026-08-19 screen recording added

Source: `screen-20260819-205619.mp4` (10:39, silent, 1602x720). Analysed frame-by-frame at
native resolution. **The momentum engine was NOT changed as a result. Here is why, and what
was learned.**

## 1. Three exact momentum values (new ground truth)

JS's price scale prints the oscillator's current value. Each reading below is anchored to a
specific bar, and the bar is not in doubt: the ribbon EMAs / volume SMA printed on the *same
frame* match that bar to the last printed digit.

| chart | bar (UTC) | printed momentum | how the bar was pinned |
|---|---|---|---|
| BTCUSDT.P 30m | 2026-08-18 00:30 | **29.8** | EMA26 = 64,141.3, EMA52 = 63,853.7, volSMA20 = 1,334.1, HA close 64,387.9 — all exact |
| SXTUSDT.P 15m | 2026-08-19 06:45 | **74.563001** | EMA26 = 0.007306, EMA52 = 0.007257 |
| SXTUSDT.P 15m | 2026-08-19 08:15 | **8.617047** | EMA26 = 0.007309, EMA52 = 0.007269 |

Only the middle one was known before (as "74.563"). These are now baked into
`5_JS_MomoRider_Momentum_v2.pine` behind the *Calibration readout* switch, so the engine can
be re-verified against any future JS screenshot without redoing any of this.

Note the chart is in **bar replay** — Jason steps it forward, which is why the same symbol
shows different EMA values 40 seconds apart. Every step is a fresh calibration point.

## 2. Why the defaults were NOT retuned

The shipped defaults `[39, 14, 0.72, 26, 0.67]` miss the BTC reading badly:

```
BTC 30m @ 2026-08-18 00:30   shipped -> 10.64    printed -> 29.8    (-19.2)
SXT 15m @ 2026-08-19 06:45   shipped -> 74.572   printed -> 74.563  (+0.009)
SXT 15m @ 2026-08-19 08:15   shipped ->  6.262   printed ->  8.617  (-2.36)
```

That looks like something to fix. **It is not**, and this is the most important result of
the second pass.

The **label pills are the real test**, because the labels *are* the 3G/3R trigger. On the BTC
30m window the original chart prints, left to right: `LL, HH, HL, HH, HL`. Pill positions were
detected from the pixels and mapped to bars (bar pitch 17.0px, confirmed from the modal
candle-body spacing).

- **Shipped defaults reproduce all five** — right types, right side of the pane, right order.
- A parameter set fitted to the three exact values above (`[45, 8, 0.601, 25, 0.322]`, which
  hits them to ±0.05) **invents a spurious sixth pivot** — an HH at 2026-08-17 12:30 that is
  not on the original chart.

So "correcting" the engine to hit the printed numbers **breaks the entry trigger**. On a
20-day backtest that retune also cut BTC 4G/4R signals from 7 to 3 and SXT from 18 to 7. The
defaults were left alone.

## 3. Measured limitation: the pivots are late

Quantified properly for the first time. Across those five pivots the shipped defaults are
**8 bars late in total — 1.6 bars each** (offsets +3, +2, +1, +2, 0). Types and order are
right; the bar is not. The README's earlier "1–3 bars later" was correct but vaguer.

A search found sets that cut this to **1 bar in total** while still reproducing the exact
sequence — `[13, 11, 0.473, 15, 0.691]` is shipped as the **Fast pivots** preset. But 16,136
parameter sets reproduce that same sequence, and the minimum-lag pick is fitted to one 60-bar
window on one instrument, so it is **EXPERIMENTAL and off by default**. Treat it as an A/B
test, not a truth.

## 4. Confirmed, not changed

- **Zone bands measured off the pixels**: green core 91.4–99.9, red core 1.05–8.1 → **90–100
  and 0–10**. Exactly what was already drawn.
- **Bounded 0–100 with plateaus at both rails** — the Schaff/STC family is right. A **third
  smoothing stage was tested and rejected**: fit RMSE 11.06 vs 11.08, i.e. it buys nothing.
- **Source is Heikin-Ashi `(high+low)/2`** as shipped. HA close and the real (non-HA) candles
  were both tested and both fit worse.
- **4G/4R anatomy confirmed by Jason's own handwriting.** At 09:56–10:20 he annotates a live
  SP500 setup: "4R" on the pullback candles at the ribbon, "1R" on the candle after, and
  **"2R"/"3R" written against a circle he draws round the momentum plateau in the upper zone
  together with the `LH` pill**. That is exactly the implemented rule — 2R = momentum ≥ 90,
  3R = the LH/LL label on that leg.

## 5. Also seen

- The system is not crypto-only: the same two panes, same bands, same pills run on
  **NDX 15m** and **SP500USD 5m (BingX)**, alongside BTCUSDT.P 30m and SXTUSDT.P 15m.
- Jason runs **4–5 indicators** per chart (from his right-click menu), so more is loaded than
  the three reconstructed here.

## 6. Honest gaps

- **The small green ▲ / red ▼ on the PRICE pane are not modelled.** They are clearly visible
  and sit at a fixed offset above/below bars, but their rule could not be determined from this
  recording, and they belong to one of his other scripts. Nothing here invents them.
- **No indicator settings dialog is opened anywhere in the 10:39.** Two right-click menus
  appear, neither reaches Settings. No parameter was ever revealed on screen — everything
  above is measurement, not disclosure.
- **The oscillator is still "close, not exact."** No parameter set fits both the BTC curve and
  the SXT printed values under this family; the parameter space is genuinely ill-conditioned
  (very different sets score nearly identically). The family is right; the exact constants
  remain unrecovered.

## Which files to load now

| Slot | File |
|---|---|
| 1 | `4_JS_Ribbon_Liquidity_Combined.pine` (unchanged) |
| 2 | `5_JS_MomoRider_Momentum_v2.pine` — drop-in replacement for `#2`, same maths and same defaults |

`2_JS_MomoRider_Momentum.pine` is kept as-is so the two can be compared.
