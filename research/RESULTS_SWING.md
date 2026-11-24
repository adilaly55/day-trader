# Multi-day (swing) research

110 symbols, daily bars (dividend-adjusted) 2016-2026. Costs 5.0 bps per side, 5 equal slots. Tuned on 2016-2021 only; 2022-2026 untouched.

| strategy | universe | period | trades | trades/yr | win% | avg_trade% | avg_days | pf | CAGR% | maxDD% | sharpe | exposure% |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rsi2_pullback | all | 2016-21 | 2838 | 524.3 | 72.5 | 0.668 | 1.9 | 1.89 | 94.3 | -19.9 | 2.37 | 94.0 |
| rsi2_pullback | all | **2022-26 OOS** | 2652 | 524.2 | 71.3 | 0.615 | 1.9 | 1.62 | 80.4 | -22.9 | 1.91 | 94.0 |
| rsi2_pullback | ETFs only | 2016-21 | 1093 | 202.7 | 72.6 | 0.273 | 1.9 | 1.56 | 11.1 | -13.8 | 0.91 | 70.0 |
| rsi2_pullback | ETFs only | **2022-26 OOS** | 1018 | 201.2 | 71.0 | 0.305 | 1.9 | 1.55 | 12.4 | -12.7 | 1.0 | 66.0 |
| ibs_reversion | all | 2016-21 | 7465 | 1383.2 | 73.2 | 0.627 | 0.7 | 2.34 | 414.9 | -16.4 | 3.73 | 95.0 |
| ibs_reversion | all | **2022-26 OOS** | 5932 | 1172.4 | 69.4 | 0.474 | 0.8 | 1.63 | 175.4 | -25.6 | 2.47 | 93.0 |
| ibs_reversion | ETFs only | 2016-21 | 2353 | 436.0 | 69.3 | 0.238 | 0.7 | 1.78 | 22.3 | -7.5 | 1.7 | 73.0 |
| ibs_reversion | ETFs only | **2022-26 OOS** | 1951 | 385.6 | 65.6 | 0.147 | 0.8 | 1.34 | 11.3 | -8.8 | 0.99 | 70.0 |
| n_day_low | all | 2016-21 | 2980 | 550.2 | 74.2 | 0.616 | 1.9 | 2.04 | 91.9 | -16.0 | 2.47 | 95.0 |
| n_day_low | all | **2022-26 OOS** | 2543 | 502.6 | 70.5 | 0.449 | 2.1 | 1.51 | 50.8 | -30.6 | 1.48 | 95.0 |
| n_day_low | ETFs only | 2016-21 | 1236 | 229.2 | 73.5 | 0.291 | 1.9 | 1.69 | 13.7 | -17.8 | 0.99 | 75.0 |
| n_day_low | ETFs only | **2022-26 OOS** | 1122 | 221.8 | 72.4 | 0.323 | 2.0 | 1.64 | 14.9 | -11.0 | 1.15 | 72.0 |
| breakout_momentum | all | 2016-21 | 679 | 125.7 | 53.9 | 1.169 | 8.3 | 1.56 | 31.1 | -19.8 | 1.39 | 95.0 |
| breakout_momentum | all | **2022-26 OOS** | 640 | 126.6 | 48.9 | 0.708 | 8.1 | 1.23 | 15.0 | -35.4 | 0.67 | 95.0 |
| breakout_momentum | ETFs only | 2016-21 | 205 | 38.9 | 58.0 | 0.734 | 8.3 | 1.88 | 5.7 | -5.5 | 1.08 | 61.0 |
| breakout_momentum | ETFs only | **2022-26 OOS** | 153 | 30.4 | 52.9 | 0.609 | 8.3 | 1.52 | 3.7 | -7.5 | 0.64 | 55.0 |
| earnings_drift | all | 2016-21 | 237 | 43.9 | 52.7 | 1.18 | 8.3 | 1.39 | 10.6 | -20.2 | 0.74 | 71.0 |
| earnings_drift | all | **2022-26 OOS** | 313 | 62.0 | 48.6 | 0.807 | 8.3 | 1.21 | 8.5 | -36.2 | 0.47 | 79.0 |
| earnings_drift | ETFs only | 2016-21 | 4 | 1.0 | 75.0 | 5.816 | 9.8 | 8.12 | 1.1 | -0.9 | 0.79 | 4.0 |
| earnings_drift | ETFs only | **2022-26 OOS** | 8 | 2.9 | 37.5 | 0.989 | 7.5 | 1.53 | 0.5 | -3.2 | 0.24 | 5.0 |
| baseline: random 3-day holds | all | IS | 1708 | 316.5 | 55.6 | 0.355 | 3.0 | 1.35 | 23.3 | -25.3 | 1.21 | 96.0 |
| baseline: random 3-day holds | all | OOS | 1747 | 345.8 | 50.6 | -0.027 | 3.0 | 0.98 | -5.7 | -45.1 | -0.1 | 96.0 |
| reference: buy & hold SPY | SPY | IS | | | | | | | 17.4 | -33.8 | | 100 |
| reference: buy & hold SPY | SPY | OOS | | | | | | | 9.3 | -24.5 | | 100 |

## Chosen settings (picked on 2016-2021 only)

- **rsi2_pullback**: `{'rsi_max': 20, 'trend': 'sma200', 'max_hold': 5, 'stop_atr': None, 'next_open': True}`
- **ibs_reversion**: `{'ibs_max': 0.3, 'max_hold': 5, 'stop_atr': None, 'next_open': True}`
- **n_day_low**: `{'n': 5, 'max_hold': 10, 'stop_atr': None, 'next_open': True}`
- **breakout_momentum**: `{'vol_mult': 1.5, 'max_hold': 10, 'stop_atr': 2.0, 'next_open': False}`
- **earnings_drift**: `{'min_gap': 0.03, 'vol_mult': 2.0, 'max_hold': 10, 'stop_atr': 2.0, 'next_open': False}`

---
# Swing robustness checks (ETFs only)

## rsi2_pullback

| variant | period | trades | win% | avg_trade% | pf | CAGR% | maxDD% | sharpe |
|---|---|---|---|---|---|---|---|---|
| baseline (5 bps, exit at close) | IS | 1093 | 72.6 | 0.273 | 1.56 | 11.1 | -13.8 | 0.91 |
| baseline (5 bps, exit at close) | OOS | 1018 | 71.0 | 0.305 | 1.55 | 12.4 | -12.7 | 1.0 |
| exit at NEXT OPEN (no close peeking) | IS | 798 | 63.9 | 0.171 | 1.26 | 4.8 | -21.8 | 0.48 |
| exit at NEXT OPEN (no close peeking) | OOS | 737 | 60.7 | 0.133 | 1.17 | 3.5 | -15.0 | 0.37 |
| costs 10 bps/side | IS | 1093 | 68.8 | 0.173 | 1.33 | 6.7 | -18.1 | 0.59 |
| costs 10 bps/side | OOS | 1018 | 68.2 | 0.205 | 1.35 | 8.0 | -13.7 | 0.69 |
| costs 10 bps + next-open exit | IS | 798 | 60.5 | 0.071 | 1.1 | 1.7 | -24.5 | 0.21 |
| costs 10 bps + next-open exit | OOS | 737 | 57.4 | 0.033 | 1.04 | 0.5 | -17.3 | 0.1 |
| with 3 ATR protective stop | IS | 1188 | 69.7 | 0.179 | 1.3 | 7.4 | -24.4 | 0.6 |
| with 3 ATR protective stop | OOS | 1055 | 69.8 | 0.203 | 1.31 | 8.2 | -14.5 | 0.69 |

By year (baseline variant):

|   year |   trades |   win% |   avg_trade% |   CAGR% |   maxDD% |
|-------:|---------:|-------:|-------------:|--------:|---------:|
|   2016 |       44 |   68.2 |        0.206 |     4.7 |     -3.3 |
|   2017 |      255 |   74.9 |        0.3   |    16.1 |     -2.3 |
|   2018 |      161 |   60.2 |       -0.337 |   -10.2 |    -11.9 |
|   2019 |      193 |   73.6 |        0.22  |     7.7 |     -6.5 |
|   2020 |      176 |   74.4 |        0.391 |    13.4 |    -11   |
|   2021 |      264 |   76.9 |        0.592 |    34.9 |     -5.3 |
|   2022 |       78 |   73.1 |        0.094 |     1.3 |     -6   |
|   2023 |      235 |   72.8 |        0.319 |    14.7 |     -9.5 |
|   2024 |      251 |   68.9 |        0.336 |    15.5 |     -9.1 |
|   2025 |      217 |   79.3 |        0.604 |    28   |     -7   |
|   2026 |      237 |   63.3 |        0.053 |     3.7 |    -12.7 |

## n_day_low

| variant | period | trades | win% | avg_trade% | pf | CAGR% | maxDD% | sharpe |
|---|---|---|---|---|---|---|---|---|
| baseline (5 bps, exit at close) | IS | 1236 | 73.5 | 0.291 | 1.69 | 13.7 | -17.8 | 0.99 |
| baseline (5 bps, exit at close) | OOS | 1122 | 72.4 | 0.323 | 1.64 | 14.9 | -11.0 | 1.15 |
| exit at NEXT OPEN (no close peeking) | IS | 879 | 64.4 | 0.16 | 1.27 | 5.0 | -23.7 | 0.44 |
| exit at NEXT OPEN (no close peeking) | OOS | 786 | 62.8 | 0.196 | 1.28 | 5.9 | -11.9 | 0.57 |
| costs 10 bps/side | IS | 1236 | 69.7 | 0.191 | 1.42 | 8.6 | -18.3 | 0.67 |
| costs 10 bps/side | OOS | 1122 | 69.7 | 0.223 | 1.42 | 9.9 | -11.8 | 0.82 |
| costs 10 bps + next-open exit | IS | 879 | 59.8 | 0.06 | 1.1 | 1.6 | -28.6 | 0.19 |
| costs 10 bps + next-open exit | OOS | 786 | 59.5 | 0.096 | 1.13 | 2.7 | -12.7 | 0.29 |
| with 3 ATR protective stop | IS | 1401 | 69.7 | 0.179 | 1.33 | 8.9 | -24.1 | 0.69 |
| with 3 ATR protective stop | OOS | 1212 | 71.3 | 0.202 | 1.32 | 9.4 | -15.3 | 0.77 |

By year (baseline variant):

|   year |   trades |   win% |   avg_trade% |   CAGR% |   maxDD% |
|-------:|---------:|-------:|-------------:|--------:|---------:|
|   2016 |       48 |   68.8 |        0.253 |     6   |     -3   |
|   2017 |      279 |   72.4 |        0.299 |    18.2 |     -2.3 |
|   2018 |      186 |   67.7 |       -0.125 |    -4.4 |     -9.6 |
|   2019 |      226 |   73.9 |        0.337 |    15   |     -6.4 |
|   2020 |      198 |   75.3 |        0.204 |     7.7 |    -17.8 |
|   2021 |      299 |   77.3 |        0.571 |    38.7 |     -5.2 |
|   2022 |       96 |   69.8 |        0.211 |     3.8 |     -8.4 |
|   2023 |      250 |   72   |        0.309 |    15.4 |     -9.2 |
|   2024 |      276 |   71.4 |        0.265 |    13.2 |     -8.6 |
|   2025 |      250 |   79.6 |        0.593 |    32.1 |     -9.9 |
|   2026 |      250 |   67.6 |        0.175 |    11.4 |    -11   |

## ibs_reversion

| variant | period | trades | win% | avg_trade% | pf | CAGR% | maxDD% | sharpe |
|---|---|---|---|---|---|---|---|---|
| baseline (5 bps, exit at close) | IS | 2353 | 69.3 | 0.238 | 1.78 | 22.3 | -7.5 | 1.7 |
| baseline (5 bps, exit at close) | OOS | 1951 | 65.6 | 0.147 | 1.34 | 11.3 | -8.8 | 0.99 |
| exit at NEXT OPEN (no close peeking) | IS | 1590 | 61.8 | 0.192 | 1.44 | 11.6 | -16.7 | 1.12 |
| exit at NEXT OPEN (no close peeking) | OOS | 1324 | 58.6 | 0.033 | 1.05 | 1.3 | -13.3 | 0.17 |
| costs 10 bps/side | IS | 2353 | 63.9 | 0.138 | 1.41 | 12.1 | -9.8 | 1.02 |
| costs 10 bps/side | OOS | 1951 | 61.1 | 0.047 | 1.1 | 3.1 | -11.0 | 0.33 |
| costs 10 bps + next-open exit | IS | 1590 | 57.4 | 0.092 | 1.19 | 5.2 | -22.4 | 0.54 |
| costs 10 bps + next-open exit | OOS | 1324 | 55.6 | -0.067 | 0.9 | -3.9 | -25.7 | -0.33 |
| with 3 ATR protective stop | IS | 2415 | 68.0 | 0.18 | 1.51 | 16.7 | -10.1 | 1.3 |
| with 3 ATR protective stop | OOS | 1987 | 65.4 | 0.122 | 1.27 | 9.4 | -9.0 | 0.84 |

By year (baseline variant):

|   year |   trades |   win% |   avg_trade% |   CAGR% |   maxDD% |
|-------:|---------:|-------:|-------------:|--------:|---------:|
|   2016 |       82 |   63.4 |        0.143 |     7.3 |     -3   |
|   2017 |      444 |   63.3 |        0.131 |    12.7 |     -3   |
|   2018 |      401 |   66.8 |        0.113 |     8   |     -7.2 |
|   2019 |      396 |   66.4 |        0.094 |     7   |     -5.5 |
|   2020 |      470 |   78.3 |        0.494 |    56   |     -7.5 |
|   2021 |      560 |   71.1 |        0.313 |    37.1 |     -5.8 |
|   2022 |      160 |   66.2 |       -0.011 |     0.7 |     -6   |
|   2023 |      443 |   68.4 |        0.205 |    19.8 |     -6.9 |
|   2024 |      493 |   65.1 |        0.068 |     5.1 |     -8.8 |
|   2025 |      427 |   65.8 |        0.179 |    14.3 |     -6.9 |
|   2026 |      428 |   62.9 |        0.206 |    21.5 |     -7.1 |

