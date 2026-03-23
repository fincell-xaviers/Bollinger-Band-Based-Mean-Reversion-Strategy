# Bollinger Bands Strategy Backtester

A Python-based backtesting framework for a **Bollinger Bands** mean-reversion trading strategy applied to Indian equities. Tests signal generation, executes trades with realistic costs, benchmarks against Buy & Hold, and runs a grid search over band parameters to identify optimal configurations.

---

## Overview

Bollinger Bands are a volatility envelope built around a Simple Moving Average (SMA), with upper and lower bands set at a multiple of the rolling standard deviation. This project exploits the mean-reversion tendency of prices that breach the bands:

- **Buy Signal:** Price closes *below* the lower band — treated as oversold; expect a snap-back upward.
- **Sell Signal:** Price closes *above* the upper band — treated as overbought; expect a reversion downward.

A second, enhanced backtest adds **momentum-confirmed entries** (crossback logic) and a **trailing stop-loss** to limit downside.

---

## Features

- Downloads historical OHLCV data via `yfinance`
- Builds Bollinger Bands (SMA ± k × rolling standard deviation)
- Generates and visualises buy/sell signals on an interactive Plotly price chart
- Backtests the strategy with transaction fees and slippage, benchmarked against Buy & Hold
- Computes full performance metrics: Total Return, Sharpe, Max Drawdown
- Grid searches over band parameters `n` and `k` with a trailing stop-loss
- Outputs heatmaps, equity curves, and risk–reward scatter plots

---

## Requirements

```
pandas
numpy
yfinance
plotly
matplotlib
seaborn
```

Install with:

```bash
pip install pandas numpy yfinance plotly matplotlib seaborn
```

---

## Configuration

All key parameters are set at the top of the script:

| Parameter         | Default       | Description                                 |
|-------------------|---------------|---------------------------------------------|
| `ticker`          | `RELIANCE.NS` | Yahoo Finance ticker (NSE-listed equity)    |
| `start_date`      | `2020-01-01`  | Backtest start date                         |
| `initial_capital` | `100,000`     | Starting portfolio value (₹)               |
| `fee_bps`         | `5.0`         | Transaction fee in basis points             |
| `slip_bps`        | `5.0`         | Slippage in basis points                    |
| `stop_loss_pct`   | `0.05`        | Trailing stop-loss threshold (5%)           |

---

## How It Works

### 1. Bollinger Band Construction

```
SMA  = Simple Moving Average of Close (window = n)
SD   = Rolling Standard Deviation of Close (window = n)
UB   = SMA + k × SD    ← Upper Band
LB   = SMA − k × SD    ← Lower Band
```

### 2. Signal Logic

**Basic Strategy**

| Signal | Condition                    |
|--------|------------------------------|
| Buy    | Current close < lower band   |
| Sell   | Current close > upper band   |

**Optimised Strategy (with crossback confirmation)**

| Signal | Condition                                                       |
|--------|-----------------------------------------------------------------|
| Buy    | Previous close ≥ lower band **AND** current close < lower band  |
| Sell   | Previous close ≤ SMA **AND** current close > SMA                |
| Exit   | Trailing stop triggered (price falls >5% from in-position peak) |

### 3. Backtest Engine

The engine loops bar-by-bar over the data in long-only, all-in/all-out mode:

- Signals are **shifted by 1 bar** to execute at the next open (no look-ahead bias)
- Each fill price adjusts for combined fee + slippage: `fill = price × (1 ± (fee_bps + slip_bps) / 10,000)`
- Equity is tracked as `cash + shares × close` at every bar
- A **Buy & Hold** benchmark is computed in parallel from the same starting capital

### 4. Performance Metrics

Each backtest reports:

| Metric          | Description                                                |
|-----------------|------------------------------------------------------------|
| Final Equity    | Ending portfolio value (₹)                                |
| Total Return %  | Overall percentage gain/loss                               |
| Sharpe Ratio    | Annualised risk-adjusted return (252 trading days)         |
| Max Drawdown %  | Worst peak-to-trough decline                               |
| Trades          | Number of completed round-trip trades                      |
| Win/Loss Ratio  | Ratio of winning to losing trades (optimised variant)      |
| Avg Win %       | Average return on winning trades (optimised variant)       |

### 5. Parameter Optimisation

A grid search tests all combinations of:

| Parameter | Values Tested | Description               |
|-----------|---------------|---------------------------|
| `n`       | 20, 50, 100   | Rolling window (lookback) |
| `k`       | 1.5, 2.0, 2.5 | Band width multiplier     |

Results are ranked by Sharpe Ratio and visualised as heatmaps across the `n × k` grid.

---

## Output

Running the script produces the following outputs in sequence:

1. **Interactive Plotly Chart** — Close price with Bollinger Bands and buy/sell signal markers
2. **Performance Summary Table** — Strategy vs Buy & Hold metrics (styled DataFrame)
3. **Equity Curve** — Strategy vs Buy & Hold portfolio value over time
4. **Bollinger Bands Chart** — Price with entry/exit points (matplotlib)
5. **Parameter Heatmaps** — Total Return % and Sharpe Ratio across `n × k` grid
6. **Bar + Line Chart** — Return % and Sharpe per parameter combination
7. **Risk–Reward Scatter** — Max Drawdown vs Total Return, coloured by Sharpe Ratio

Console output includes the full optimisation results table sorted by Sharpe Ratio.

---

## Project Structure

```
bollinger_backtest.py   # Main script - all logic in a single file
README.md
```

---

## Notes & Limitations

- **Long-only** — the strategy never short-sells; it is either invested or in cash.
- **All-in sizing** — 100% of capital is deployed on each buy signal. No fractional or risk-based position sizing.
- **Single asset** — tested on `RELIANCE.NS` over a fixed date range; performance on other tickers or periods may differ significantly.
- **Stop-loss approximation** — the trailing stop tracks the running price peak from entry; it does not account for intraday gaps through the stop level.
- **No dividend adjustment** — `yfinance` returns adjusted close prices but dividends are not separately modelled in the P&L.
