# Backtest results

110 symbols, 5-minute bars 09:30-12:30 ET, 2021-01-01 to latest. Costs 5.0 bps per side. Up to 5 trades/day, equal size. Parameters chosen on 2021-2023 ONLY; 2024-2026 is untouched out-of-sample.

## Summary

| strategy                           | period                |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|:-----------------------------------|:----------------------|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
| orb_in_play                        | in-sample 2021-23     |      215 |         0.28 |   25.6 |        0.144 | 1.28 |   0.085 |     2   |     -3.5 |     0.55 |
| orb_in_play                        | OUT-OF-SAMPLE 2024-26 |      272 |         0.38 |   30.1 |        0.043 | 1.09 |   0.096 |     0.8 |     -4.2 |     0.31 |
| gap_and_go                         | in-sample 2021-23     |      356 |         0.46 |   44.4 |        0.165 | 1.19 |   0.062 |     3.7 |     -5.6 |     0.71 |
| gap_and_go                         | OUT-OF-SAMPLE 2024-26 |      441 |         0.6  |   40.4 |       -0.067 | 0.93 |  -0.051 |    -2.2 |    -11.2 |    -0.29 |
| gap_down_reversal                  | in-sample 2021-23     |      185 |         0.24 |   46.5 |       -0.08  | 0.92 |  -0.074 |    -1   |     -8   |    -0.24 |
| gap_down_reversal                  | OUT-OF-SAMPLE 2024-26 |      260 |         0.35 |   45.8 |       -0.186 | 0.81 |  -0.079 |    -3.3 |    -13.4 |    -0.58 |
| vwap_pullback                      | in-sample 2021-23     |      177 |         0.23 |   42.9 |        0.019 | 1.03 |  -0.001 |     0.2 |     -4.2 |     0.07 |
| vwap_pullback                      | OUT-OF-SAMPLE 2024-26 |      179 |         0.24 |   43   |        0.012 | 1.02 |   0.012 |     0.1 |     -4.9 |     0.05 |
| baseline: random entries           | in-sample 2021-23     |     2218 |         2.84 |   42.2 |       -0.12  | 0.74 |  -0.099 |   -16.1 |    -42.5 |    -2.13 |
| baseline: random entries           | OUT-OF-SAMPLE 2024-26 |     2164 |         2.87 |   42.3 |       -0.111 | 0.73 |  -0.095 |   -15   |    -39.5 |    -2.45 |
| baseline: buy SPY 9:35, sell 12:30 | in-sample 2021-23     |      753 |         0.97 |   44   |       -0.088 | 0.68 |  -0     |    -4.2 |    -12.5 |    -2.23 |
| baseline: buy SPY 9:35, sell 12:30 | OUT-OF-SAMPLE 2024-26 |      726 |         0.96 |   44.6 |       -0.098 | 0.59 |  -0     |    -4.7 |    -13.3 |    -2.82 |

## Chosen settings (picked on 2021-2023 only)

- **orb_in_play** (324 settings tried): `{'or_bars': 1, 'min_rvol': 4.0, 'stop_atr': 0.2, 'target_r': None, 'vwap_filter': False, 'use_regime': True}`
- **gap_and_go** (24 settings tried): `{'min_gap': 0.02, 'min_rvol': 2.0, 'target_r': 2.0, 'use_regime': True}`
- **gap_down_reversal** (8 settings tried): `{'max_gap': -0.04, 'fill_target': True, 'use_regime': False}`
- **vwap_pullback** (24 settings tried): `{'min_move': 0.02, 'min_rvol': 2.5, 'target_r': 3.0, 'use_regime': False}`

## orb_in_play: by year

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2021 |       80 |         0.32 |   22.5 |        0.055 | 1.1  |  -0.076 |     0.8 |     -3   |     0.19 |
|   2022 |       34 |         0.14 |   32.4 |        0.483 | 1.8  |   0.397 |     3.4 |     -1.4 |     0.99 |
|   2023 |      101 |         0.42 |   25.7 |        0.101 | 1.21 |   0.106 |     2.1 |     -1.8 |     0.71 |
|   2024 |      111 |         0.47 |   30.6 |       -0.027 | 0.94 |   0.061 |    -0.7 |     -2.8 |    -0.26 |
|   2025 |      104 |         0.44 |   23.1 |       -0.054 | 0.9  |  -0.061 |    -1.2 |     -3   |    -0.43 |
|   2026 |       57 |         0.28 |   42.1 |        0.359 | 1.82 |   0.45  |     5.1 |     -1.4 |     1.76 |

## gap_and_go: by year

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2021 |      130 |         0.53 |   43.1 |       -0.132 | 0.87 |   0.008 |    -3.6 |     -5.4 |    -0.63 |
|   2022 |       68 |         0.28 |   44.1 |        0.484 | 1.53 |   0.062 |     6.9 |     -2   |     1.5  |
|   2023 |      158 |         0.63 |   45.6 |        0.272 | 1.35 |   0.106 |     8.9 |     -3.6 |     1.38 |
|   2024 |      166 |         0.66 |   43.4 |       -0.002 | 1    |   0.004 |    -0.3 |    -11.2 |    -0.01 |
|   2025 |      145 |         0.59 |   42.8 |       -0.005 | 0.99 |  -0.038 |    -0.3 |     -4.9 |    -0.02 |
|   2026 |      130 |         0.61 |   33.8 |       -0.218 | 0.82 |  -0.135 |    -6.8 |     -9.7 |    -0.85 |

## gap_down_reversal: by year

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2021 |       73 |         0.3  |   50.7 |        0.223 | 1.26 |   0.002 |     3.3 |     -2.2 |     0.75 |
|   2022 |       57 |         0.25 |   47.4 |       -0.165 | 0.85 |  -0.091 |    -2.1 |     -4.5 |    -0.49 |
|   2023 |       55 |         0.22 |   40   |       -0.394 | 0.64 |  -0.159 |    -4.4 |     -5.3 |    -1.14 |
|   2024 |       60 |         0.24 |   45   |       -0.282 | 0.75 |  -0.081 |    -3.5 |     -4.8 |    -0.57 |
|   2025 |       81 |         0.33 |   43.2 |       -0.248 | 0.76 |  -0.131 |    -4.2 |     -7.2 |    -0.76 |
|   2026 |      119 |         0.54 |   47.9 |       -0.095 | 0.89 |  -0.042 |    -2.7 |     -7.1 |    -0.44 |

## vwap_pullback: by year

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2021 |       57 |         0.23 |   42.1 |        0.149 | 1.21 |   0.045 |     1.7 |     -1.6 |     0.56 |
|   2022 |       50 |         0.21 |   52   |       -0.082 | 0.9  |   0.083 |    -0.9 |     -3   |    -0.24 |
|   2023 |       70 |         0.31 |   37.1 |       -0.016 | 0.98 |  -0.099 |    -0.3 |     -4.2 |    -0.09 |
|   2024 |       48 |         0.2  |   47.9 |        0.437 | 1.89 |   0.252 |     4.4 |     -1.1 |     1.39 |
|   2025 |       62 |         0.25 |   50   |       -0.057 | 0.91 |   0.003 |    -0.7 |     -2.2 |    -0.32 |
|   2026 |       69 |         0.3  |   33.3 |       -0.222 | 0.71 |  -0.146 |    -3.4 |     -4.1 |    -1.24 |

## baseline: random entries: by year

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2021 |      804 |         3.09 |   39.8 |       -0.133 | 0.68 |  -0.128 |   -18.9 |    -19.6 |    -3.02 |
|   2022 |      694 |         2.67 |   39.9 |       -0.193 | 0.68 |  -0.121 |   -23.2 |    -27.8 |    -2.62 |
|   2023 |      720 |         2.78 |   46.9 |       -0.036 | 0.9  |  -0.046 |    -5.2 |    -10.8 |    -0.71 |
|   2024 |      732 |         2.8  |   41.3 |       -0.09  | 0.75 |  -0.095 |   -12.2 |    -14   |    -2.15 |
|   2025 |      749 |         2.88 |   42.6 |       -0.156 | 0.63 |  -0.106 |   -20.5 |    -21.2 |    -3.48 |
|   2026 |      683 |         2.96 |   43   |       -0.084 | 0.81 |  -0.082 |   -12   |    -12.8 |    -1.71 |

## baseline: buy SPY 9:35, sell 12:30: by year

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2021 |      252 |         0.97 |   44   |       -0.056 | 0.73 |      -0 |    -2.7 |     -2.9 |    -1.78 |
|   2022 |      251 |         0.97 |   44.2 |       -0.144 | 0.63 |      -0 |    -6.8 |     -7.1 |    -2.76 |
|   2023 |      250 |         0.97 |   43.6 |       -0.065 | 0.71 |      -0 |    -3.1 |     -3.6 |    -2.08 |
|   2024 |      252 |         0.97 |   39.7 |       -0.099 | 0.54 |      -0 |    -4.7 |     -5.2 |    -3.32 |
|   2025 |      250 |         0.96 |   49.2 |       -0.1   | 0.62 |      -0 |    -4.8 |     -4.9 |    -2.52 |
|   2026 |      224 |         0.97 |   45.1 |       -0.095 | 0.6  |      -0 |    -4.6 |     -4.3 |    -2.8  |

---
# Stress tests

## Stress test 1: is the ORB edge robust?

- Settings with enough trades: 324
- Share with positive OUT-OF-SAMPLE avg trade (after costs): 7%
- Among the 20 best in-sample settings, positive out-of-sample: 12/20, median OOS avg trade +0.018%
- Rank correlation in-sample vs out-of-sample Sharpe: 0.80 (1 = in-sample perfectly predicts OOS, 0 = no relation)

Average out-of-sample result by setting (each row averages over all other settings):

**or_bars**

|   or_bars |   is_trade% |   oos_trade% |   oos_sharpe |
|----------:|------------:|-------------:|-------------:|
|         1 |      -0.037 |       -0.033 |       -0.925 |
|         3 |      -0.091 |       -0.088 |       -1.657 |
|         6 |      -0.104 |       -0.115 |       -1.965 |

**min_rvol**

|   min_rvol |   is_trade% |   oos_trade% |   oos_sharpe |
|-----------:|------------:|-------------:|-------------:|
|        1.5 |      -0.078 |       -0.093 |       -2.384 |
|        2.5 |      -0.072 |       -0.081 |       -1.382 |
|        4   |      -0.081 |       -0.062 |       -0.78  |

**stop_atr**

|   stop_atr |   is_trade% |   oos_trade% |   oos_sharpe |
|-----------:|------------:|-------------:|-------------:|
|       0.1  |      -0.106 |       -0.102 |       -2.647 |
|       0.2  |      -0.072 |       -0.07  |       -1.147 |
|       0.35 |      -0.053 |       -0.064 |       -0.753 |

**target_r**

|   target_r |   is_trade% |   oos_trade% |   oos_sharpe |
|-----------:|------------:|-------------:|-------------:|
|          2 |      -0.09  |       -0.085 |       -1.998 |
|          4 |      -0.073 |       -0.076 |       -1.398 |
|        nan |      -0.068 |       -0.075 |       -1.152 |

**vwap_filter**

| vwap_filter   |   is_trade% |   oos_trade% |   oos_sharpe |
|:--------------|------------:|-------------:|-------------:|
| False         |      -0.077 |       -0.079 |       -1.516 |
| True          |      -0.077 |       -0.079 |       -1.516 |

**use_regime**

| use_regime   |   is_trade% |   oos_trade% |   oos_sharpe |
|:-------------|------------:|-------------:|-------------:|
| False        |      -0.099 |       -0.08  |       -1.573 |
| True         |      -0.055 |       -0.077 |       -1.459 |

## Stress test 2: trading-cost sensitivity (chosen ORB settings)

| cost per side | OOS avg trade % | OOS profit factor | OOS Sharpe |
|---|---|---|---|
| 0 bps | +0.143 | 1.36 | 1.04 |
| 2 bps | +0.103 | 1.25 | 0.75 |
| 5 bps | +0.043 | 1.09 | 0.31 |
| 10 bps | -0.057 | 0.89 | -0.4 |
| 15 bps | -0.157 | 0.74 | -1.1 |

## Stress test 3: machine-learning prediction engine

Gradient-boosted trees on 13 features known at 09:35 (gap, relative volume, first-bar move, trend, volatility, market direction...). Predicts each stock's 09:35 -> 12:30 return. Retrained every year on all prior years; scored only on the following year (never seen).

- Stock-days scored out-of-sample: 76,523
- Correlation of prediction with actual return: 0.011 (rank: 0.012)

Actual average return (after costs) by prediction bucket, out-of-sample:

| prediction decile | avg return % (hold to 12:30) | avg return % (with 0.5 ATR stop) | win % |
|---|---|---|---|
| 1 (most bearish) | -0.037 | -0.036 | 49.3 |
| 2  | -0.078 | -0.055 | 47.4 |
| 3  | -0.175 | -0.151 | 43.4 |
| 4  | -0.150 | -0.136 | 45.4 |
| 5  | -0.073 | -0.057 | 47.6 |
| 6  | -0.081 | -0.069 | 45.9 |
| 7  | -0.092 | -0.087 | 46.4 |
| 8  | -0.064 | -0.074 | 47.0 |
| 9  | -0.033 | -0.048 | 49.0 |
| 10 (most bullish) | -0.021 | -0.034 | 48.9 |

**Trading rule** (each day buy the top 5 predictions if > 0, 0.5 ATR stop, sell 12:30), 2024-2026 out-of-sample: {'trades': 2463, 'trades/day': 3.27, 'win%': 46.4, 'avg_trade%': np.float64(-0.005), 'pf': np.float64(0.99), 'avg_R': nan, 'CAGR%': np.float64(-2.9), 'maxDD%': np.float64(-23.4), 'sharpe': np.float64(-0.04)}

|   year |   trades |   trades/day |   win% |   avg_trade% |   pf |   avg_R |   CAGR% |   maxDD% |   sharpe |
|-------:|---------:|-------------:|-------:|-------------:|-----:|--------:|--------:|---------:|---------:|
|   2024 |      928 |         3.58 |   47.6 |        0.021 | 1.02 |     nan |     1.4 |    -18.1 |     0.17 |
|   2025 |      838 |         3.22 |   46.2 |       -0.066 | 0.93 |     nan |   -11.8 |    -18.3 |    -0.55 |
|   2026 |      697 |         3.02 |   45.1 |        0.034 | 1.03 |     nan |     3.1 |    -13.1 |     0.25 |
