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
