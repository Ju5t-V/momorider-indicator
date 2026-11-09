# MomoRider on MetaTrader 5

Port of the TradingView indicators to MQL5. **Nothing in `../indicators/`, `../strategy/` or `../orderflow/` was modified.**

Both files compile clean (0 errors, 0 warnings) and are already installed and compiled in **both** of your MT5 terminals under `MQL5\Indicators\MomoRider\`.

---

## Answering the two questions

### Can MIM_GEX be rebuilt in TradingView?

Partly. The signal maths is trivial in Pine; the **gamma gate is the blocker**.

| piece | Pine |
|---|---|
| r_ROD, session timing, entry window, ATR stop/target | ✅ straightforward |
| **reading the GEX number** | ❌ **not possible** |

Pine has **no file I/O and no HTTP**. It can only read instruments that exist on TradingView, and there is no GEX ticker. The only workaround is an `input.float("Today's GEX")` that you paste in by hand each morning from `run_gex.py`.

MT5 doesn't have that problem — it reads `gex_regime.csv` off disk automatically, which is why `MIM_GEX.mq5` lives on that side.

### Can the TradingView indicators be rebuilt in MQL5?

Yes — done, and it's a straight upgrade:

- **The 2-indicator limit disappears.** That cap is a TradingView free-plan restriction, not a market one. So the whole `force_overlay` contortion in `4_JS_Ribbon_Liquidity_Combined.pine` — which existed *only* to squeeze two panes into one slot — is unnecessary. These are just two normal indicators.
- **Heikin-Ashi is computed explicitly**, so the result no longer depends on the chart being set to HA. In Pine, `close` silently changes meaning with the chart type; here it can't. That's strictly safer.
- **The higher-timeframe staircase is cleaner** — MQL5 pulls H4 bars directly instead of `request.security`, and only uses *closed* HTF bars, so it cannot repaint.

---

## ⚠️ Before you rely on this: your broker has no crypto

Your terminal is on **`MetaQuotes-Demo`**, which carries **zero crypto pairs** — I checked all 12,495 symbols, there is no BTCUSD/ETHUSD/anything. It has indices, FX and metals only:

```
US500   116,398 M30 bars   2015-01-02 .. 2026-08-21
US30    116,170            2015-01-02 .. 2026-08-21
DAX      19,906            2015-01-05 .. 2026-08-21
XAUUSD  136,874            EURUSD 144,620 ...
```

So on **this** account the port runs on indices/FX/metals, **not** on the Bybit perps (BTCUSDT.P, SXTUSDT.P) the MomoRider system is actually used for. If you want it on crypto in MT5 you need a broker that offers crypto CFDs (IC Markets, Pepperstone and most others do) — and note those are CFDs with different pricing and funding than Bybit perps, so signals will not tick-for-tick match your TradingView charts.

**Practical split:** TradingView for the crypto charts, MT5 for indices/FX and for `MIM_GEX`.

---

## The two indicators

### `MomoRider_Ribbon.mq5` — price pane

| plot | formula | verified against JS's chart |
|---|---|---|
| Ribbon fast | EMA(26) of HA close | BTC 30m **64,141.3** / SXT 15m **0.007306** — exact |
| Ribbon slow | EMA(52) of HA close | **63,853.7** / **0.007257** — exact |
| Staircase | EMA(26) of HA close from a higher TF | **63,465.0** — exact (4H anchor on a 30m chart) |
| 1G / 1R | pullback candle touching the ribbon | — |

Inputs: ribbon lengths, **staircase anchor timeframe** (default H4 — the original used 4H on BTC 30m and 3H on SXT 15m, so it *is* a per-chart setting), markers on/off, alerts on/off.

### `MomoRider_Momentum.mq5` — separate pane

Same engine as the verified Pine defaults:

```
src = (HA high + HA low) / 2
dt  = src − EMA(src, 39)
v1  = Stoch(dt, 14)  →  pf  = pf[1]  + 0.72·(v1 − pf[1])
v3  = Stoch(pf, 26)  →  osc = osc[1] + 0.67·(v3 − osc[1])
```

Draws the oscillator, the 0/10/90/100 levels (measured off JS's own pixels — red core 1.05–8.1, green core 91.4–99.9), the **HH/HL/LH/LL** structure labels, and 4G/4R arrows.

The label rule is the part that matters, because **the labels are the 3G/3R trigger**: pivots are found on the *oscillator*, forced to alternate high/low, then **named by comparing price at consecutive same-type pivots**. Position from momentum, name from price — that's what makes it a divergence read rather than price structure.

One deliberate change: labels sit a few points above/below the pivot instead of pinned at 112/−12 as in Pine, so they track the swing. The pane is fixed to −25…125 to leave room, matching how the original's scale looks.

---

## Install

Already done — both terminals have the compiled `.ex5`. If you ever need to redo it:

1. MT5 → **File → Open Data Folder** → `MQL5\Indicators\`
2. Drop the two `.mq5` files in (a `MomoRider\` subfolder is fine)
3. Right-click → **Compile** in MetaEditor, or just restart MT5
4. They appear under **Navigator → Indicators → MomoRider**

## Use

1. Open a chart, set **M15 or M30** (the timeframes this system is built for).
2. Drag on **MomoRider_Ribbon** first — it draws on the price pane.
3. Drag on **MomoRider_Momentum** — it creates its own pane below.
4. Set the **staircase anchor TF**: H4 for a 30m chart, H3 for 15m, matching the original.
5. Leave the chart on **normal candles** if you like — HA is computed internally either way.

Reading it, same as on TradingView:

- **1G** — red candle above a bullish ribbon whose low reaches back and touches it
- **2G** — momentum in the lower zone (≤10)
- **3G** — an **HL** or **HH** label prints on that leg ← the actual trigger
- **4G** — the next candle closes green

4R is the mirror. Alerts are off by default; switch `InpAlerts` on to get MT5 popups on 4G/4R and ribbon flips.

---

## Honest note, carried over

The mechanised 4G/4R showed **no significant directional edge** — 12 markets, 3,161 signals, pooled t=0.05 at +16 bars (see `../strategy/README.md`). This port is faithful to the original and is a good *charting* tool for reading setups by eye, which is how Jason actually uses it. It is not an automatic system, and nothing here changes that finding.

What the port does give you: no 2-indicator cap, no chart-type dependency, no repainting staircase, and native alerts.

## Files

```
mt5_indicators/
  MomoRider_Ribbon.mq5     price pane: ribbon + staircase + 1G/1R
  MomoRider_Momentum.mq5   own pane: oscillator + HH/HL/LH/LL + 4G/4R
  README.md                this file
```

`MIM_GEX.mq5` lives in `../orderflow/` with its own instructions and is installed alongside these.
