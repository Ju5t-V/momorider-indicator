# Cross-Sectional Momentum — the strategy that actually tested well

New folder. **Nothing in `../indicators/`, `../strategy/`, `../orderflow/` or `../mt5_indicators/` was modified.**

---

## 1. The short version

| | 4G/4R | MIM (gamma) | **This** |
|---|---|---|---|
| Test-period result | pooled t=0.05 | decayed to t=1.38 | **Sharpe 2.18** |
| Deflated Sharpe | 0.001 | — | 0.57 |
| Permutation p | — | — | **0.016** |
| Every year positive? | no | no | **yes, 6/6** |

**The rule.** Every day, rank ~29 crypto perps by their **14-day return**. Buy the top 25%, short the bottom 25%, equal dollars each side. Size each position inversely to its own volatility, cap any name at 10%. Rebalance every 5 days. That's the whole thing.

**Measured** on real Bybit daily data, 2020–2026, train 2020–23 / **test 2024–26 held back**, costs 25bp round trip, real perp funding charged:

```
TRAIN  annRet 57.4%   Sharpe 2.81   maxDD 14.5%
TEST   annRet 52.9%   Sharpe 2.18   maxDD 13.4%     <- never used to choose anything
```

---

## 2. Why this, when 4G/4R and the gamma trade both failed

This matters more than the numbers, because it tells you *what kind of thing* works.

**4G/4R failed because it's a directional bet with no informational edge.** A chart pattern on one coin. 3,161 signals across 12 markets: pooled forward return t=0.05 at 16 bars. The tiny gross edge was smaller than the fees.

**A directional version of *this* signal also failed** — test Sharpe **0.08**. I ran it: unanimous multi-lookback trend + volatility regime, holding a basket of long/short crypto. Per-trade it looked fine (t=2.00). As a portfolio it was worthless, because **29 crypto perps are ~0.8 correlated**. Holding 15 of them isn't diversification, it's one leveraged bet on crypto beta, and that beta swamps any signal.

**Going market-neutral is the entire unlock.** Long the strong, short the weak, equal dollars. The crypto beta cancels out and what's left is the *relative* signal — which is where the information actually is. Same signal, same data:

| construction | TEST Sharpe | TEST maxDD |
|---|---|---|
| directional basket | 0.08 | 41.7% |
| **dollar-neutral long/short** | **2.18** | **13.4%** |

That's not a parameter tweak. That's the difference between fighting a factor and neutralising it.

---

## 3. Why it works — the economics you need to understand

Do not trade this as a black box. The mechanism is what tells you when it will stop working.

**Cross-sectional momentum is a documented risk premium.** Jegadeesh & Titman (1993) found it in US stocks; it has since been found in essentially every asset class. Crypto is a particularly clean case because:

1. **Slow information diffusion.** Retail-dominated, fragmented, no analyst coverage. News about a token propagates over days, not seconds. A coin that outperformed over 14 days tends to keep outperforming while the flow works through.
2. **Attention and flow herding.** Crypto flows chase visible winners. That's self-reinforcing over weeks.
3. **You are being paid to hold a real risk.** Momentum crashes — hard — at sharp trend reversals. The negative skew (−1.26) and kurtosis (18) in my results *are* the risk premium. You are compensated for holding something that occasionally loses badly and fast.

**Why market-neutral specifically:** the coin-level return decomposes into "crypto did X" plus "this coin relative to crypto." The first term is huge, unpredictable, and dominates any single-coin bet. The second is smaller but *predictable*. Long/short subtracts the first term and leaves you holding only the part you can forecast.

**Why 14 days and 5-day holds:** short enough that the momentum hasn't reversed, long enough that the ~25bp round trip is trivial against the move. In my grid, hold=5 beat hold=20 at every lookback. Costs are why 4G/4R died — here they're rounding error.

---

## 4. The evidence, in full, including what's against it

**For:**

- **Test Sharpe 2.18** (2024–26, held back), annRet 52.9%, maxDD 13.4%
- **Every year positive**, with 25bp costs and funding charged: 2021 SR 1.66 · 2022 3.99 · 2023 3.69 · 2024 2.66 · 2025 1.90 · 2026 1.71
- **78% of test months positive**, best +25.4%, worst −11.2%
- **96% of 54 parameter configurations were positive out-of-sample**, median test Sharpe 1.08. If you'd picked settings at random you'd still have won — so this is not a cherry-picked config.
- **Permutation test p = 0.016.** Shuffle the momentum ranks, keep every other mechanic identical: real SR +2.18 vs shuffled mean −0.98 (sd 0.58, max +0.78 over 60 shuffles). The *ranking* carries information. This test has no trial-counting problem.
- **Survives cost stress to 60bp** (7.5× realistic): Sharpe 1.68
- **Real perp funding charged** from Bybit's own funding history: no change (long/short funding largely nets)
- **Excluding BTC/ETH** (pure alt cross-section): test Sharpe **3.33**
- **Pre-2022 listings only** (partial survivorship control): test Sharpe **2.61**

**Against — read this properly:**

- **Deflated Sharpe = 0.57, not >0.95.** The DSR penalises me for running 54 configs, treating them as independent trials when they're variations of one idea, and it's hit hard by the fat tails. I think the permutation test and the 96%-of-configs result are stronger evidence — but you deserve both numbers, and the DSR does not clear its bar.
- **Survivorship bias is real and only partly measured.** My universe is coins *listed on Bybit today*. Coins that were delisted or died are absent. The pre-2022-listings test helps but does not eliminate this. Expect live results below backtest.
- **Negative skew (−1.26), kurtosis 18.** Occasional violent losing weeks are structural, not a bug.
- **Sharpe 2+ will not survive contact with reality intact.** Slippage on small alts, imperfect fills, and the survivorship gap will all take a bite. If you get half of it live, that's a good outcome.

---

## 5. How to trade it manually — step by step

**Every 5 days** (pick a fixed day, e.g. every Monday and Wednesday alternating, or just every 5th day — consistency matters more than the specific day):

```bash
python momentum_system/backtest/scanner.py
```

It prints exactly this:

```
CROSS-SECTIONAL MOMENTUM BASKET   as of 2026-08-23 (UTC daily close)

    symbol         14d mom   30d vol    weight   price
  L XRPUSDT          41.2%      4.1%     7.03%   1.4535
  L LINKUSDT         38.1%      3.6%     7.94%   11.297
  ...
  S UNIUSDT           2.8%      4.8%     4.68%   4.096
  S TRXUSDT           3.8%      0.7%    10.00%   0.3423
  ...
  long book 50.0%  |  short book 49.8%  |  net ~0 (dollar-neutral)
```

**Then:**

1. **Close** anything you hold that is no longer on the list.
2. **Open/adjust** to match: `weight` is the % of your total account for that position. `L` = long, `S` = short.
3. **Both sides, always.** The long book and short book must be roughly equal in dollars. Trading only the longs is *not* this strategy — it's a directional crypto bet, and that version tested at Sharpe 0.08.
4. Use **market or limit orders on Bybit perps**, 1× notional. Don't add leverage on top until you've traded it for months.
5. **Do nothing until the next rebalance.** No discretionary exits, no stop-hunting your own positions.

### Where's my stop-loss?

There isn't a per-position stop, and that is deliberate. **The exit is the rebalance.** A coin that weakens drops out of the top quartile and you close it in ≤5 days.

Per-position stops actively hurt cross-sectional momentum: they cut the fat right tail (the runners that pay for everything) while doing nothing about the real risk, which is a *whole-book* reversal. Your risk control is at the portfolio level instead:

- Vol-scaled sizing (each name contributes equal risk)
- 10% cap per name
- Dollar-neutrality (removes the beta)
- **A portfolio-level circuit breaker:** if the whole book draws down more than **20%** from its peak, halve your size and don't restore it until it makes a new equity high. Backtest maxDD was 13–15%; 20% means something has changed.

### Reading the TradingView indicator

`XSectionalMomentum.pine` — drop on any chart of a coin in the universe (daily or 4H).

- **Green background / "LONG" label** — this coin is in the top quartile right now
- **Red background / "SHORT" label** — bottom quartile
- **No tint** — middle, no position
- **Table, top right** — the live ranking, longs in green at the top, shorts in red at the bottom

It's a *reader*, not the whole system: it tells you where the coin you're looking at sits. The scanner gives you the full basket and the weights. Alerts fire on bucket entry/exit.

---

## 6. Learning path — read these, in this order

**Start here (the core idea):**
1. **Jegadeesh & Titman (1993)**, "Returns to Buying Winners and Selling Losers", *Journal of Finance*. The original cross-sectional momentum paper. Take from it: the long/short construction and why relative ranking is the unit of analysis.
2. **Moskowitz, Ooi & Pedersen (2012)**, [Time Series Momentum](https://www.sciencedirect.com/science/article/pii/S0304405X11002613), *JFE*. Take from it: **volatility scaling**, and why it's what makes one setting work across different instruments.

**Then (why it's a premium, not free money):**
3. **Daniel & Moskowitz**, [Momentum Crashes](https://www.nber.org/system/files/working_papers/w20439/w20439.pdf), *JFE*. Take from it: momentum's crash risk, when it happens, and why the negative skew in my results is expected rather than alarming. **Read this before you size up.**
4. **Asness, Moskowitz & Pedersen (2013)**, "Value and Momentum Everywhere", *JF*. Take from it: this is a cross-asset phenomenon, not a crypto quirk.

**Crypto-specific:**
5. [Time-Series and Cross-Sectional Momentum in the Cryptocurrency Market](https://acfr.aut.ac.nz/__data/assets/pdf_file/0009/918729/Time_Series_and_Cross_Sectional_Momentum_in_the_Cryptocurrency_Market_with_IA.pdf) — direct precedent for what you're trading.
6. [Momentum Trading in Cryptocurrencies: Time-Series vs Cross-Sectional](https://www.journals.vu.lt/BATP/en/article/download/44540/42590/138419) — confirms vol-scaled beats plain.

**Methodology — how not to fool yourself (this is the important half):**
7. **Bailey & López de Prado (2014)**, [The Deflated Sharpe Ratio](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551). Take from it: why a good backtest usually isn't one, and why I reported DSR 0.57 against myself.
8. **López de Prado (2018)**, *Advances in Financial Machine Learning*, ch. 7 & 11 — purging, embargo, and the ways backtests leak.

**How to actually read a strategy result — the checklist I used on this one:**

- Is it positive **out-of-sample**, on data never used to choose anything?
- Is it a **plateau or a spike** across parameters? (Spike = fitted. Here: 96% of configs positive.)
- Does it survive **realistic costs**, stressed several times over?
- Is it consistent **year by year**, or is it one lucky period?
- Does a **permutation/shuffle test** kill it?
- Is there an **economic reason** it should exist?
- What's the **worst month**, and could you actually sit through it?

Any strategy anyone shows you — including this one — run that list. Most things die at step 2.

---

## 7. When to stop trading it

Decide these *now*, not in the middle of a drawdown:

- **Portfolio drawdown > 20%** → halve size until a new equity high
- **Drawdown > 30%** → stop entirely and re-examine; backtest max was 13–15%
- **6 consecutive months negative** → the premium may be arbitraged out
- **Turnover costs > 1.5% per month** → your execution is worse than modelled; fix fills before continuing
- Log every rebalance. After 3 months, compare your live hit rate and monthly returns to the backtest. If live is less than half of backtest, something in your execution is broken.

---

## 8. Files

```
momentum_system/
  XSectionalMomentum.pine   TradingView ranker: table + LONG/SHORT tint + alerts
  backtest/scanner.py       THE DAILY TOOL - prints the exact basket and weights
  backtest/xsec.py          the cross-sectional grid
  backtest/xsec_stress.py   cost / funding / survivorship stress tests
  backtest/perm_test.py     permutation test + grid distribution
  backtest/final_stats.py   deflated Sharpe, monthly consistency
  backtest/portfolio.py     the directional version that FAILED (Sharpe 0.08)
  backtest/tsm_test.py      time-series momentum grid
  backtest/stack_test.py    the 4G/4R-style confirmation stack
  backtest/diag_vol.py      volatility-regime conditioning
  backtest/fetch_daily.py   real Bybit daily klines
  backtest/fetch_funding.py real Bybit funding history
  data/                     29 symbols daily + funding, and today's basket.json
```

Reproduce the headline: `cd backtest && python xsec.py && python xsec_stress.py && python perm_test.py`

**Every number in this document came from those scripts on real Bybit data. Nothing is simulated or assumed.**
