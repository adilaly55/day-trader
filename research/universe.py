"""Research universe: liquid US stocks and ETFs available on Trading 212.

Caveat (survivorship bias): this list is chosen with today's knowledge. Names that
crashed or were delisted since 2021 are missing, which flatters long-only results.
"""
ETFS = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLI", "SMH", "ARKK", "GLD", "TLT"]

STOCKS = [
    # tech / growth
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "AMD", "NFLX", "ADBE", "CRM", "ORCL",
    "INTC", "QCOM", "TXN", "MU", "AMAT", "LRCX", "KLAC", "MRVL", "CSCO", "IBM", "NOW", "SHOP", "UBER",
    "ABNB", "SNOW", "PLTR", "COIN", "PYPL", "ROKU", "DKNG", "RBLX", "ZM", "DOCU", "NET", "CRWD", "PANW",
    "DDOG", "MDB", "TEAM", "SNAP", "PINS", "SMCI", "MSTR", "HOOD", "AFRM", "SOFI", "U",
    # financials
    "JPM", "BAC", "WFC", "GS", "MS", "C", "V", "MA", "AXP", "SCHW",
    # energy
    "XOM", "CVX", "COP", "OXY", "SLB",
    # health
    "UNH", "JNJ", "PFE", "MRK", "LLY", "ABBV", "MRNA", "BMY", "AMGN", "GILD",
    # consumer
    "WMT", "COST", "HD", "LOW", "TGT", "NKE", "SBUX", "MCD", "DIS", "KO", "PEP", "PG",
    # industrial / autos
    "BA", "CAT", "DE", "GE", "F", "GM", "RIVN", "LCID", "NIO",
]

ALL = ETFS + STOCKS

# S&P 100 members as of early 2016 (point-in-time, so later losers are included).
# Omitted: names acquired/delisted since (AGN, CELG, MON, TWX, old DOW/DD, FOX) and
# messy ticker histories (RTN/UTX -> RTX). Ticker renames mapped: FB->META, PCLN->BKNG.
SP100_2016 = [
    "AAPL", "ABBV", "ABT", "ACN", "AIG", "ALL", "AMGN", "AMZN", "AXP", "BA", "BAC", "BIIB", "BK", "BLK",
    "BMY", "BRK.B", "C", "CAT", "CL", "CMCSA", "COF", "COP", "COST", "CSCO", "CVS", "CVX", "DHR", "DIS",
    "DUK", "EMR", "EXC", "F", "META", "FDX", "GD", "GE", "GILD", "GM", "GOOGL", "GS", "HAL", "HD", "HON",
    "IBM", "INTC", "JNJ", "JPM", "KHC", "KMI", "KO", "LLY", "LMT", "LOW", "MA", "MCD", "MDLZ", "MDT", "MET",
    "MMM", "MO", "MRK", "MS", "MSFT", "NEE", "NKE", "ORCL", "OXY", "BKNG", "PEP", "PFE", "PG", "PM", "PYPL",
    "QCOM", "SBUX", "SLB", "SO", "SPG", "T", "TGT", "TXN", "UNH", "UNP", "UPS", "USB", "V", "VZ", "WBA",
    "WFC", "WMT", "XOM",
]
