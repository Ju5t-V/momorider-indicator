# Order flow & gamma — a research-backed intraday strategy

New folder. **Nothing in `../indicators/` or `../strategy/` was touched.**

---

## 1. Where to get real L1 / L2 / L3 data (free, not TradingView)

This was your core question. Here is the honest map.

| source | what you get | level | cost |
|---|---|---|---|
| **`data.binance.vision`** | `bookDepth/` (order-book depth snapshots), `bookTicker/` (every best bid/ask update), `aggTrades/` (full tape **with the maker/taker flag**, so true buy/sell classification, not an approximation) | **L1 + L2 + tape** | **free**, daily zips, ~550 KB/day/symbol, history back to 2019 |
| **Binance/Bybit REST + WebSocket** | live `@depth` book stream, `@aggTrade` tape, open interest, funding, taker long/short ratio | L1/L2 live | free |
| **MetaTrader 5 Python bridge** (`pip install MetaTrader5`) | indices, FX, metals, futures CFDs. I pulled **116,398 M30 bars of US500 back to 2015** from your own terminal | OHLCV + DOM where the broker provides it | free, already installed |
| **Free option chains** (`yfinance`) | full chain with open interest + IV → lets you compute **dealer GEX yourself** | options positioning | free |
| **Deribit public API** | full crypto option chain / OI by strike, no auth | crypto GEX | free |
| TradingView Pine | **no order book at all, on any plan.** `request.footprint()` exists (Mar 2026) but needs Premium/Ultimate | — | — |

The important correction to my earlier answer: **you can absolutely get L1/L2/L3 — just not inside Pine.** Binance publishes it as flat files, and MT5 hands you decades of index data through Python.

---

## 2. The strategy, and why this one and not another

I went looking for a setup with the same shape as 4G/4R — a directional trigger with a stop and a target — but backed by peer-reviewed evidence instead of chart reading. The one that qualifies:

**Market Intraday Momentum** — Baltussen, Da, Lammers & Martens (2021), *Journal of Financial Economics* 142:377–403.

> The return in the **last 30 minutes before the cash close** is positively predicted by the return **from the previous close up to that point** (`r_ROD`). Tested on 60+ futures across equities, bonds, commodities and currencies, **1974–2020**. Annualised Sharpe **0.87–1.73** by asset class.

The mechanism is gamma: dealers who are **short gamma** must hedge *in the direction of* the move, and that hedging concentrates into the close. Which is why their **Table 7** is the part that actually matters:

| dealer net gamma (NGE) | β on `r_ROD` | t | R² |
|---|---|---|---|
| NGE ≥ 0 (dealers long gamma) | 0.82 | (1.03) — not significant | 0.05% |
| **NGE < 0 (dealers short gamma)** | **6.63** | **(4.78)** | **3.58%** |

Confirmed and extended by **Dim, Eraker & Vilkov (2025)**, *0DTEs: Trading, Gamma Risk and Volatility Propagation*: **positive dealer gamma strengthens intraday REVERSAL, negative gamma strengthens MOMENTUM.**

So this is a genuinely two-sided rule — it tells you when to buy *and* when to sell — and the side is chosen by an observable variable rather than by taste.

---

## 3. What I verified myself, including what failed

### It replicates — on markets with a close

Pulled from your MT5 terminal, 2015–2026, five index CFDs. Cash close located empirically from the volume profile (US cash open 09:30 ET shows up at 16:30 server ⇒ **server = ET + 7**, so the S&P cash close is 23:00 server).

| market | β | t | R²% | mean bp | SR/yr |
|---|---|---|---|---|---|
| US500 | 0.0154 | 2.55 | 0.28 | 0.76 | 0.37 |
| US30 | 0.0221 | 3.65 | 0.58 | 0.51 | 0.26 |
| DAX | 0.0093 | 3.33 | 0.70 | 1.11 | 0.91 |
| FRA40 | 0.0259 | **5.79** | 1.77 | 1.06 | 0.76 |
| ESP35 | 0.0152 | 3.49 | 0.69 | 0.79 | 0.57 |
| **US pool** | 0.0186 | **4.36** | 0.41 | 0.64 | 0.32 |

5 of 6 significant and positive. (AUS200 was flat — Asian session, different close dynamics.)

### It does NOT work on crypto — exactly as the theory predicts

Same test on 12 Bybit perps: pooled **β=0.0001, t=0.13, sign-match 48.8%** — below a coin flip, 0.13 bp against ~8 bp costs. That is the correct result: crypto trades 24/7, so there is **no closing auction and no close-concentrated hedging flow**. The mechanism isn't there, so neither is the effect. Don't run this on BTC.

### The unconditional effect has decayed — this is the important warning

| period | t | gross bp/day |
|---|---|---|
| 2015–2019 | 3.18 | 0.45 (below cost) |
| **2020–2022** | **5.85** | **2.00 (tradable)** |
| **2023–2026** | **1.38** | **0.02 (dead)** |

### Ablation — and the regime proxy that proves the mechanism

I used realised volatility as a *causal* proxy for the gamma regime (positive gamma suppresses realised vol, negative amplifies it), ranked against a trailing 250-day window so there is no lookahead:

| vol regime | 2015–2022 | 2023–2026 |
|---|---|---|
| quiet (≤p25) ≈ long gamma | β=−0.002, t=−0.49 → nothing | β=+0.011, t=2.50 |
| wild (>p75) ≈ short gamma | β=+0.031, **t=4.86, +3.98 bp** | β=+0.001, t=0.20, **−0.72 bp** |
| extreme (>p90) | β=+0.044, **t=4.01, +7.97 bp** | t=0.36, **−1.02 bp** |

Pre-2022 this is a textbook confirmation: **momentum appears only in the short-gamma regime, and on extreme days it paid ~8 bp against ~0.8 bp of cost.** Post-2022 it is gone.

Full ablation (train 2015–22 / test 2023–26) on `|r_ROD|` thresholds, vol regimes, Friday and 3rd-Friday OPEX proxies, and combinations: **every variant was positive in train and negative in test.** Including the untuned baseline — so this is regime change, not overfitting.

**Why**: 0DTE. Since 2022 a large share of SPX option volume expires the same day, so dealer gamma now resets intraday and is on average *positive* (Dim/Eraker/Vilkov). Realised vol stopped being a usable proxy for it. **The conclusion is not "the effect is fake" — it is "you now need the actual gamma number instead of a proxy."**

That is what `gex.py` is for. And it is the one thing I could **not** backtest: free *historical* option open interest doesn't exist, so the GEX-gated version is forward-test-only. I am not going to claim a number I could not measure.

---

## 4. The tools

### `backtest/gex.py` — dealer gamma from a free option chain

Black-Scholes gamma × open interest, using the paper's dealer convention (MMs long calls, short puts):

```
GEX = Σ_calls OI·Γ·100·S²·0.01  −  Σ_puts OI·Γ·100·S²·0.01
```

Verified working live:

```
SPY  spot 765.72   (6 expiries)
  dealer GEX : $-4.215 bn per 1% move
  gamma flip : 671.75
  REGIME     : MOMENTUM (dealers short gamma)
```

It also finds the **gamma flip level** (where cumulative GEX crosses zero) — above it dealers are long gamma and suppress moves, below it they amplify. That is a genuine support/resistance level with a mechanism behind it, unlike a drawn line.

### `MIM_GEX.mq5` — the MT5 indicator

Marks the entry bar 30 min before the cash close, computes `r_ROD`, reads the gamma regime, and draws entry / SL / TP.

- **GEX < 0** → trade **with** `r_ROD` (momentum)
- **GEX > 0** → **fade** `r_ROD` (reversal)
- no GEX file → stands aside (safe default)

---

## 5. How to use it

**Install**

1. Copy `MIM_GEX.mq5` → `MQL5\Indicators\` in your terminal folder (MT5 → File → Open Data Folder), then right-click → Compile in MetaEditor.
2. `pip install yfinance MetaTrader5` (both already installed here).

**Daily routine** — run once, an hour or so before the close:

```bash
python orderflow/backtest/run_gex.py SPY
```

It writes `gex_regime.csv` into your MT5 `Files` folders automatically (already verified — it found both of your terminals).

**On the chart**

- Attach to **US500 / US30 / DAX / FRA40 / ESP35 on M30**. Not crypto.
- Set `InpCloseHour/Minute` to the **cash close in server time**: US indices **23:00**, European indices **18:30**. (Server = ET+7 on your terminal — re-check after a DST change.)
- `InpMinMovePct` default 0.15% — skip days where the market has barely moved; those carry no hedging imbalance.
- Panel at top-left shows the live regime.

**Risk** — defaults are 1.0 ATR stop / 1.5 ATR target on a 30-minute hold. This is a *fast* trade: in by 30-min-to-close, out at the close. Size it so a stop costs a fixed fraction of equity, as in `../strategy/`.

---

## 6. Honest status

| claim | evidence |
|---|---|
| The intraday-momentum effect is real and published | ✅ JFE 2021, 60+ futures, 46 years |
| It replicates on your MT5 index data | ✅ my test, t=4.36 pooled, 5/6 markets |
| It does not work on crypto | ✅ my test, t=0.13 — and theory says so |
| It decayed after 2022 unconditionally | ✅ my test, t=1.38, ~0 bp |
| Momentum concentrates in the short-gamma regime | ✅ pre-2022 in my data (+7.97 bp on extreme days); ✅ published (Table 7) |
| **The live GEX gate restores the edge today** | ❌ **unverified.** No free historical option OI, so I could not test it. Paper-trade it first. |

**Do not size this up on my say-so.** Log it daily for a month or two against the live GEX print, then decide. If the gate works you should see the momentum leg pay only on negative-GEX days — that is the specific thing to look for, and it is falsifiable.

---

## 7. Papers

- **Baltussen, Da, Lammers & Martens (2021)** — [Hedging demand and market intraday momentum](https://www.sciencedirect.com/science/article/abs/pii/S0304405X21001598), *JFE* 142:377–403. Core signal + Table 7 gamma conditioning. Full text in `research/`.
- **Dim, Eraker & Vilkov (2025)** — [0DTEs: Trading, Gamma Risk and Volatility Propagation](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4692190). Positive dealer gamma → reversal; negative → momentum. Explains the post-2022 decay.
- **Barbon & Buraschi (2021)** — [Gamma Fragility](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3725454). Dealer gamma imbalance drives intraday momentum/reversal; stronger in illiquid underlyings.
- **Baltussen, Da & Soebhag (2024)** — [End-of-Day Reversal](https://www.efmaefm.org/0EFMAMEETINGS/EFMA%20ANNUAL%20MEETINGS/2024-Lisbon/papers/EndofDayReversal_withnames.pdf). Checked and **not used**: it is a cross-sectional single-stock effect and the authors state it is *not* gamma-driven. Full text in `research/`.
- **Cont, Kukanov & Stoikov (2014)** — [The Price Impact of Order Book Events](https://academic.oup.com/jfec/article-abstract/12/1/47/816163). The OFI reference if you later build on Binance `bookDepth`.
- **Easley, López de Prado & O'Hara** — [Bulk Volume Classification / VPIN](https://cfr.ivo-welch.org/published/papers/easley-prado-hara.pdf).

## 8. Files

```
orderflow/
  MIM_GEX.mq5              MT5 indicator: entry window, r_ROD, GEX gate, SL/TP
  backtest/gex.py          dealer GEX + gamma flip from a free option chain
  backtest/run_gex.py      daily refresh -> writes gex_regime.csv into MT5
  backtest/mim_index.py    replication on MT5 index CFDs
  backtest/mim_crypto.py   the crypto null result
  backtest/ablation.py     train/test ablation
  backtest/regime_test.py  gamma-regime proxy test
  backtest/mt5_pull.py     pulls index history out of your terminal
  research/                extracted full text of the two Baltussen papers
  data/                    MT5 M30 history + the current gex_regime.csv
```

Reproduce: `cd backtest && python mim_index.py && python regime_test.py && python ablation.py`
