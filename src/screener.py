"""Universe screener for the emerging growth strategy.

Applies market cap, exchange, dollar volume, and price filters to raw
ticker data and returns qualifying tickers.

Strategy filter thresholds:
    - Market cap: $50M <= cap <= $10B  (Bloomberg reports in millions: 50-10000)
    - Exchange: NAS, NYS, or ASE
    - Dollar volume: >= $500,000 avg daily
    - Price: >= $2.00
"""

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Filter constants
# ---------------------------------------------------------------------------
MIN_MARKET_CAP = 50        # $50M in Bloomberg millions
MAX_MARKET_CAP = 10_000    # $10B in Bloomberg millions
VALID_EXCHANGES = {"NAS", "NYS", "ASE"}
MIN_DOLLAR_VOLUME = 500_000  # $500K daily
MIN_PRICE = 2.00             # $2.00 per share


def screen_universe(universe_df: pd.DataFrame) -> pd.DataFrame:
    """Apply all universe filters and return qualifying tickers.

    Filters are applied sequentially (cascading) so that each stage
    operates on the survivors of the previous stage.  The running count
    is logged at every step for diagnostics.

    Args:
        universe_df: DataFrame from ``data_loader.load_universe()`` with
            columns: ticker, market_cap, exchange, avg_volume, price,
            dollar_volume.

    Returns:
        Filtered DataFrame containing only qualifying tickers, with a
        fresh 0-based index.

    Raises:
        KeyError: If a required column is missing from *universe_df*.
    """
    total = len(universe_df)
    logger.info(f"Starting universe screening with {total} tickers")

    # Filter 1: Market cap $50M-$10B (in millions: 50-10000)
    df = universe_df[
        (universe_df["market_cap"] >= MIN_MARKET_CAP)
        & (universe_df["market_cap"] <= MAX_MARKET_CAP)
    ].copy()
    logger.info(f"After market cap filter ($50M-$10B): {len(df)}/{total} pass")

    # Filter 2: Exchange (NAS, NYS, ASE)
    df = df[df["exchange"].isin(VALID_EXCHANGES)]
    logger.info(f"After exchange filter: {len(df)}/{total} pass")

    # Filter 3: Dollar volume >= $500K
    df = df[df["dollar_volume"] >= MIN_DOLLAR_VOLUME]
    logger.info(f"After dollar volume filter (>=$500K): {len(df)}/{total} pass")

    # Filter 4: Price >= $2.00
    df = df[df["price"] >= MIN_PRICE]
    logger.info(f"After price filter (>=$2.00): {len(df)}/{total} pass")

    logger.info(f"Universe screening complete: {len(df)}/{total} tickers qualify")

    return df.reset_index(drop=True)


def screening_summary(
    original_df: pd.DataFrame,
    screened_df: pd.DataFrame,
) -> dict[str, Any]:
    """Return a summary dict of screening results for reporting.

    Each ``filtered_*`` value counts how many tickers from *original_df*
    fail that **individual** gate (independent, not cascading).  This is
    useful for understanding which filters are the most restrictive.

    Args:
        original_df: The raw universe DataFrame before screening.
        screened_df: The DataFrame returned by :func:`screen_universe`.

    Returns:
        Dictionary with keys:
            - ``total_input``: number of tickers before screening
            - ``total_passed``: number of tickers after screening
            - ``filtered_market_cap``: count failing the market-cap gate
            - ``filtered_exchange``: count failing the exchange gate
            - ``filtered_volume``: count failing the dollar-volume gate
            - ``filtered_price``: count failing the price gate
            - ``pass_rate``: fraction of input tickers that passed (0.0-1.0)
    """
    total_input = len(original_df)
    total_passed = len(screened_df)

    # Independent filter failure counts
    filtered_market_cap = int(
        (
            (original_df["market_cap"] < MIN_MARKET_CAP)
            | (original_df["market_cap"] > MAX_MARKET_CAP)
        ).sum()
    )
    filtered_exchange = int(
        (~original_df["exchange"].isin(VALID_EXCHANGES)).sum()
    )
    filtered_volume = int(
        (original_df["dollar_volume"] < MIN_DOLLAR_VOLUME).sum()
    )
    filtered_price = int(
        (original_df["price"] < MIN_PRICE).sum()
    )

    pass_rate = total_passed / total_input if total_input > 0 else 0.0

    return {
        "total_input": total_input,
        "total_passed": total_passed,
        "filtered_market_cap": filtered_market_cap,
        "filtered_exchange": filtered_exchange,
        "filtered_volume": filtered_volume,
        "filtered_price": filtered_price,
        "pass_rate": round(pass_rate, 4),
    }
