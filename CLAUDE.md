# Project notes: day-trader

Automated short-term trading bot for the owner's **Trading 212 Invest** account (USD), run from an
**Android phone** (Termux). Demo/practice account first; real money only after the demo matches backtests.

## Owner's requirements
- Based in **Dubai (UTC+4, no DST)**. Trades **US stocks**.
- Prefers same-day trades; holding **1-3 days** is acceptable.
- Session window agreed so far: US open to ~3h later = 18:30-21:30 Dubai (17:30-20:30 when the US is on summer time).
  Owner is open to later exits (US close = 01:00 Dubai in winter) and to multi-day holds.
- **$20 per trade** on demo. Bot picks the markets itself (scanner), long-only.
- Wants a system that makes money passively. Be candid about the odds; never overstate an edge.

## Hard constraints
- Trading 212 public API: **Invest/ISA only, no CFD** -> no shorting. No market-data endpoints (use Alpaca/Finnhub).
  Demo base URL `https://demo.trading212.com/api/v0`. Strict per-account rate limits. API is beta.
- Market data: Alpaca (free, SIP history since 2016). Earnings dates: Finnhub (free tier has no historical calendar).
- Credentials are injected by the cloud environment's network proxy (hosts data.alpaca.markets, finnhub.io).
  Never ask the owner to paste keys into chat, never commit keys.

## Repository layout
- `intraday/` - live engine (strategy, risk, tracker/journal, paper + Alpaca brokers, CLI). Trading 212 broker: TODO.
- `research/` - `download.py` (Alpaca -> data/), `lab.py` + `strategies.py` (intraday 5-min backtests),
  `run_research.py`, `deep_dive.py`, `swing.py` (multi-day). Results in `research/RESULTS*.md`.
- `data/` - downloaded bars (gitignored; re-create with `python research/download.py [--full|--daily]`).

## Research findings so far (Nov 2026)
- Intraday 09:30-12:30 ET, 110 symbols, tuned 2021-23, judged 2024-26, 5 bps/side costs:
  only "ORB on stocks in play" (5-min opening range, RVOL>=4, stop 0.2 ATR, SPY>SMA20 filter) survived: +0.04%/trade OOS,
  weak and year-dependent (lost 2024, 2025). Breakeven cost ~7 bps/side. Others failed. Random entries -0.11%/trade.
- ML (gradient boosting, 13 features at 09:35, walk-forward): no predictive power (corr 0.01).
- Conclusion: costs dominate short holds. Next: multi-day (swing) strategies on daily data 2016-2026, and
  ORB held to the US close using 5-min full-day data.

## Plan
1. Research (multi-day + hold-to-close) -> pick a strategy.
2. Build Trading 212 demo broker + scanner + scheduler (Termux on Android) + notifications.
3. Demo for 4-6 weeks, compare live vs backtest. 4. Real money only if it matches, small size.

## Conventions
- Conservative backtests: entries at bar close, stop-first when ambiguous, costs always on, in-sample/out-of-sample split.
- Report failures honestly; compare every strategy against random-entry and buy-and-hold baselines.
