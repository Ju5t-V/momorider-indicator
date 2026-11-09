# Start here

## Just run one thing

**`RUN.cmd`** — double-click it. Menu-driven, does everything.

```
  DAILY
    1.  Momentum basket scan   <- the main tool, run every 5 days
    2.  Refresh GEX regime for MT5
    3.  Do both

  SETUP / CHECKS
    4.  Check + install Python packages
    5.  Show today's saved basket
    6.  Where do my indicator files go?

  VERIFY THE RESEARCH
    7.  Re-run cross-sectional validation (the Sharpe 2.18 result)
    8.  Re-run stress tests
    9.  Re-run permutation test
```

There is also **`MomoRiderDaily.exe`** — double-click, no Python needed, runs options 1+2 back to back and writes its output to an `output\` folder beside it. Use `RUN.cmd` if you want the menu and the ability to re-run the research.

---

## What to do each week

1. Every 5 days, run `RUN.cmd` → option **1**.
2. Close anything no longer on the list. Open/adjust to match the printed weights.
3. **Both sides, always** — long book and short book equal in dollars. Longs only is not this strategy; that version tested at Sharpe 0.08.
4. Do nothing until the next rebalance. The rebalance *is* the exit — there is no per-position stop, deliberately.
5. Portfolio circuit breaker: **−20% from peak → halve size** until a new equity high.

If you also trade US indices in MetaTrader, run option **2** before the US close to refresh the dealer-gamma regime that `MIM_GEX` reads.

---

## What's in each folder

| folder | what it is | verdict |
|---|---|---|
| **`momentum_system/`** | **Cross-sectional momentum. The one that worked.** | **Test Sharpe 2.18, every year positive, permutation p=0.016** |
| `orderflow/` | Gamma/GEX trade + where to get real L1/L2/L3 data | Mechanism published; unconditional version decayed post-2022 |
| `strategy/` | The 4G/4R strategy harness | No significant edge (t=0.05). Kept as evidence. |
| `indicators/` | The original MomoRider TradingView reconstruction | Faithful to Jason's charts; charting aid, not a system |
| `mt5_indicators/` | MomoRider ported to MetaTrader 5 | Compiled and installed in both your terminals |

**Read `momentum_system/README.md` first.** It has the full evidence, the honest limits, and a reading list so you understand *why* it works rather than just following it.

---

## Installing the indicators

**TradingView** — open Pine Editor, paste the file contents, "Add to chart":
- `momentum_system/XSectionalMomentum.pine` ← the ranker for the working strategy
- `indicators/4_JS_Ribbon_Liquidity_Combined.pine` + `indicators/5_JS_MomoRider_Momentum_v2.pine` (the MomoRider pair)

**MetaTrader 5** — already installed and compiled. Navigator → Indicators → **MomoRider**.

---

## If something breaks

- **"Python was not found"** → install Python 3.11+ from python.org, tick *Add python.exe to PATH*, re-run.
- **Scan fails** → connection issue; Bybit's public API is being called with no key.
- **GEX fails** → Yahoo rate-limits sometimes. Wait a minute and retry.
- **Missing packages** → `RUN.cmd` → option 4 installs them.
