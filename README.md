# MomoRider: Momentum and Liquidity Indicator Toolkit

A reconstruction and extension of a discretionary crypto-perp momentum system ("4G/4R" signals on Heikin Ashi), packaged for **TradingView (Pine Script)** and **MetaTrader 5 (MQL5)**, plus Python research tooling.

## Contents
- `indicators/`: Pine Script v5 trend ribbon, liquidity-hunter staircase, momentum oscillator with HH/HL/LH/LL labels and alerts. Designed to fit TradingView's free-plan 2-indicator limit.
- `mt5_indicators/`: MQL5 ports of the ribbon and momentum indicators
- `momentum_system/`: cross-sectional momentum basket scanner, with backtest, validation and stress tests
- `orderflow/`: GEX (gamma exposure) regime indicator for MT5, with research
- `build_exe/`: packages the daily scanner into a standalone Windows app
- `RUN.cmd`: menu-driven launcher. See [`START_HERE.md`](START_HERE.md).

## Status
🟡 Indicators are working. Research is ongoing.

> ⚠️ Research and educational code only. Not financial advice. Backtests are not a promise of future results.
