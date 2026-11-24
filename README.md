# Intraday Trader

A day-trading bot that opens and closes all its positions within a single session.
It tracks every position and trade in a SQLite journal. Pure Python 3.10+ standard library; nothing to install.

> ⚠️ Educational software, not financial advice. Use paper trading first. Most intraday strategies lose money after costs.

## Quick start

```bash
python -m intraday backtest --days 20                        # synthetic data, runs offline
python -m intraday report --trades                           # view journaled runs
python -m unittest discover -s tests -t .                    # tests
```

Backtesting on real data and paper trading both need a free Alpaca account (https://alpaca.markets):

```bash
export APCA_API_KEY_ID=...  APCA_API_SECRET_KEY=...          # paper keys
python -m intraday fetch --symbols AAPL,MSFT,NVDA --start 2026-09-01 --end 2026-11-20 --out bars.csv
python -m intraday backtest --csv bars.csv
python -m intraday live --config config.example.json          # paper trades one session, then exits
```

## How it works

| Module | Role |
|---|---|
| `strategy.py` | Opening Range Breakout + VWAP filter. Stop at range midpoint, target = 2R. Max 1 trade/symbol/day. |
| `risk.py` | Sizes positions to risk 0.5% of equity, caps each at 20%, max 3 open, halts at -2% for the day. |
| `engine.py` | Per-bar loop: checks stops/targets, takes entries, enforces risk, **flattens everything at 15:55**. |
| `tracker.py` | Open positions, realized/unrealized P&L, trade journal (SQLite), stats (win rate, PF, R, drawdown). |
| `broker.py` / `alpaca.py` | Simulated fills with slippage, or real Alpaca orders (paper by default). |

The same engine runs backtests and live trading, so what you test is what trades.

## Safety notes
- Live mode refuses a real-money endpoint unless you pass `--i-understand-this-is-real-money`.
- It refuses to start if the account already has open positions.
- Stops are enforced by the bot on each 1-minute bar ("software stops"), so the process must keep running.
  If it dies, positions stay open. Check your broker. Native bracket orders would be a good next step.
- Synthetic data only tests the plumbing. It says nothing about whether the strategy has an edge.
