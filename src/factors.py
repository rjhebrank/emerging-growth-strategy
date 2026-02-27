"""Factor calculator for the emerging growth strategy.

Computes all 4 ranking factors from raw price and fundamental data:

    1. RS Percentile (40% weight) -- 6-month relative strength ranked cross-sectionally
    2. EPS Growth YoY (20% weight) -- year-over-year quarterly earnings growth
    3. Revenue Growth YoY (20% weight) -- year-over-year quarterly revenue growth
    4. Price vs 52-Week High (20% weight) -- current price as % of trailing high

Each function is independently testable and returns a pd.Series indexed by ticker.
"""

import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
RS_LOOKBACK_DAYS = 126       # ~6 months of trading days
HIGH_LOOKBACK_DAYS = 252     # ~52 weeks of trading days
MIN_QUARTERS_EPS = 5         # Need 5 quarters to compute YoY (current + 4 back)
MIN_QUARTERS_REV = 5         # Same for revenue
TURNAROUND_GROWTH = 999.0    # Sentinel for negative-to-positive turnarounds


# ---------------------------------------------------------------------------
# Factor 1: Relative Strength Percentile
# ---------------------------------------------------------------------------

def calc_rs_percentile(
    price_data: dict[str, pd.DataFrame],
    tickers: list[str],
) -> pd.Series:
    """Calculate Relative Strength percentile for each ticker.

    For each ticker, computes the 126-trading-day (roughly 6-month) return
    and then ranks all tickers cross-sectionally.  The highest return maps
    to ~100, the lowest to ~0.

    Args:
        price_data: dict mapping ticker -> DataFrame with 'close' and 'date'
            columns.  The DataFrame should be sorted by date ascending (oldest
            first), though this function will sort defensively.
        tickers: list of tickers to calculate for.

    Returns:
        pd.Series indexed by ticker, values are RS percentile (0-100).
        Tickers with insufficient data receive NaN.
    """
    returns: dict[str, float] = {}

    for ticker in tickers:
        df = price_data.get(ticker)
        if df is None or df.empty:
            logger.debug(f"RS: {ticker} -- no price data, skipping")
            returns[ticker] = np.nan
            continue

        df = df.sort_values("date").reset_index(drop=True)
        closes = df["close"].values

        if len(closes) < RS_LOOKBACK_DAYS:
            logger.debug(
                f"RS: {ticker} -- only {len(closes)} days "
                f"(need {RS_LOOKBACK_DAYS}), skipping"
            )
            returns[ticker] = np.nan
            continue

        latest_close = closes[-1]
        prior_close = closes[-RS_LOOKBACK_DAYS]

        if prior_close <= 0 or np.isnan(prior_close):
            logger.warning(f"RS: {ticker} -- invalid prior close {prior_close}")
            returns[ticker] = np.nan
            continue

        ret = (latest_close / prior_close) - 1.0
        returns[ticker] = ret

    returns_series = pd.Series(returns, dtype=float)

    # Cross-sectional percentile rank (only among valid tickers)
    valid_mask = returns_series.notna()
    valid_count = valid_mask.sum()

    if valid_count == 0:
        logger.warning("RS: no tickers had sufficient data for RS calculation")
        return returns_series  # all NaN

    # rank(pct=True) gives values in (0, 1]; multiply by 100 for percentile
    percentiles = returns_series[valid_mask].rank(pct=True) * 100.0

    result = pd.Series(np.nan, index=returns_series.index, dtype=float)
    result[valid_mask] = percentiles

    logger.info(
        f"RS percentile: {int(valid_count)}/{len(tickers)} tickers computed, "
        f"median return={returns_series[valid_mask].median():.2%}"
    )

    return result


# ---------------------------------------------------------------------------
# Factor 2: EPS Growth Year-over-Year
# ---------------------------------------------------------------------------

def calc_eps_growth(
    fundamentals: dict[str, dict],
    tickers: list[str],
) -> pd.Series:
    """Calculate year-over-year EPS growth for each ticker.

    Compares the most recent quarterly EPS to the same quarter one year
    ago (4 quarters back).  Handles turnaround scenarios (negative -> positive)
    with a capped growth value.

    Args:
        fundamentals: dict mapping ticker -> dict containing key 'eps' with a
            DataFrame that has 'date' and 'eps' columns (one row per quarter).
        tickers: list of tickers to calculate for.

    Returns:
        pd.Series indexed by ticker, values are EPS growth percentage.
        Tickers with insufficient data receive NaN.
    """
    growth_values: dict[str, float] = {}

    for ticker in tickers:
        fund = fundamentals.get(ticker)
        if fund is None:
            logger.debug(f"EPS: {ticker} -- no fundamental data")
            growth_values[ticker] = np.nan
            continue

        eps_df = fund.get("eps")
        if eps_df is None or eps_df.empty:
            logger.debug(f"EPS: {ticker} -- no EPS data")
            growth_values[ticker] = np.nan
            continue

        eps_df = eps_df.sort_values("date").reset_index(drop=True)

        if len(eps_df) < MIN_QUARTERS_EPS:
            logger.debug(
                f"EPS: {ticker} -- only {len(eps_df)} quarters "
                f"(need {MIN_QUARTERS_EPS})"
            )
            growth_values[ticker] = np.nan
            continue

        current_eps = eps_df["eps"].iloc[-1]
        prior_eps = eps_df["eps"].iloc[-5]

        growth = _compute_earnings_growth(current_eps, prior_eps)
        growth_values[ticker] = growth

    result = pd.Series(growth_values, dtype=float)

    valid_count = result.notna().sum()
    logger.info(
        f"EPS growth: {int(valid_count)}/{len(tickers)} tickers computed"
    )

    return result


def _compute_earnings_growth(current: float, prior: float) -> float:
    """Compute EPS growth handling edge cases around zero and negative values.

    Rules:
        - prior <= 0 and current > 0: turnaround -> 999.0
        - both <= 0: 0.0 (no meaningful growth)
        - prior == 0 and current == 0: 0.0
        - prior > 0 and current <= 0: normal negative growth
        - Normal: (current - prior) / abs(prior) * 100
    """
    # Handle NaN inputs
    if np.isnan(current) or np.isnan(prior):
        return np.nan

    # Both zero
    if prior == 0.0 and current == 0.0:
        return 0.0

    # Turnaround: negative/zero prior, positive current
    if prior <= 0.0 and current > 0.0:
        return TURNAROUND_GROWTH

    # Both negative or current negative from zero base
    if prior <= 0.0 and current <= 0.0:
        return 0.0

    # Normal case (prior > 0)
    return (current - prior) / abs(prior) * 100.0


# ---------------------------------------------------------------------------
# Factor 3: Revenue Growth Year-over-Year
# ---------------------------------------------------------------------------

def calc_revenue_growth(
    fundamentals: dict[str, dict],
    tickers: list[str],
) -> pd.Series:
    """Calculate year-over-year revenue growth for each ticker.

    Compares the most recent quarterly revenue to the same quarter one year
    ago (4 quarters back).

    Args:
        fundamentals: dict mapping ticker -> dict containing key 'revenue' with
            a DataFrame that has 'date' and 'revenue' columns (one row per
            quarter).
        tickers: list of tickers to calculate for.

    Returns:
        pd.Series indexed by ticker, values are revenue growth percentage.
        Tickers with insufficient data or non-positive prior revenue receive
        NaN.
    """
    growth_values: dict[str, float] = {}

    for ticker in tickers:
        fund = fundamentals.get(ticker)
        if fund is None:
            logger.debug(f"Revenue: {ticker} -- no fundamental data")
            growth_values[ticker] = np.nan
            continue

        rev_df = fund.get("revenue")
        if rev_df is None or rev_df.empty:
            logger.debug(f"Revenue: {ticker} -- no revenue data")
            growth_values[ticker] = np.nan
            continue

        rev_df = rev_df.sort_values("date").reset_index(drop=True)

        if len(rev_df) < MIN_QUARTERS_REV:
            logger.debug(
                f"Revenue: {ticker} -- only {len(rev_df)} quarters "
                f"(need {MIN_QUARTERS_REV})"
            )
            growth_values[ticker] = np.nan
            continue

        current_rev = rev_df["revenue"].iloc[-1]
        prior_rev = rev_df["revenue"].iloc[-5]

        growth = _compute_revenue_growth(current_rev, prior_rev)
        growth_values[ticker] = growth

    result = pd.Series(growth_values, dtype=float)

    valid_count = result.notna().sum()
    logger.info(
        f"Revenue growth: {int(valid_count)}/{len(tickers)} tickers computed"
    )

    return result


def _compute_revenue_growth(current: float, prior: float) -> float:
    """Compute revenue growth handling edge cases around zero and negative.

    Rules:
        - prior <= 0 and current > 0: turnaround -> 999.0
        - prior <= 0 (any other case): NaN (can't compute meaningful growth)
        - Normal: (current - prior) / prior * 100
    """
    # Handle NaN inputs
    if np.isnan(current) or np.isnan(prior):
        return np.nan

    # Turnaround: non-positive prior, positive current
    if prior <= 0.0 and current > 0.0:
        return TURNAROUND_GROWTH

    # Non-positive prior with non-positive current -- meaningless
    if prior <= 0.0:
        return np.nan

    # Normal case (prior > 0)
    return (current - prior) / prior * 100.0


# ---------------------------------------------------------------------------
# Factor 4: Price vs 52-Week High
# ---------------------------------------------------------------------------

def calc_price_vs_high(
    price_data: dict[str, pd.DataFrame],
    tickers: list[str],
) -> pd.Series:
    """Calculate current price as percentage of 52-week high.

    Uses trailing 252 trading days (or all available data if less) to
    determine the high-water mark, then expresses the latest close as a
    percentage of that high.

    Args:
        price_data: dict mapping ticker -> DataFrame with 'close' and 'date'
            columns.
        tickers: list of tickers to calculate for.

    Returns:
        pd.Series indexed by ticker, values are percentage (0-100).
        Tickers with no price data receive NaN.
    """
    pct_values: dict[str, float] = {}

    for ticker in tickers:
        df = price_data.get(ticker)
        if df is None or df.empty:
            logger.debug(f"PriceHigh: {ticker} -- no price data")
            pct_values[ticker] = np.nan
            continue

        df = df.sort_values("date").reset_index(drop=True)
        closes = df["close"].values

        # Use trailing 252 days, or all available if fewer
        trailing = closes[-HIGH_LOOKBACK_DAYS:] if len(closes) >= HIGH_LOOKBACK_DAYS else closes

        max_close = np.nanmax(trailing)
        current_close = closes[-1]

        if max_close <= 0 or np.isnan(max_close):
            logger.warning(f"PriceHigh: {ticker} -- invalid max close {max_close}")
            pct_values[ticker] = np.nan
            continue

        if np.isnan(current_close):
            logger.warning(f"PriceHigh: {ticker} -- current close is NaN")
            pct_values[ticker] = np.nan
            continue

        pct_values[ticker] = (current_close / max_close) * 100.0

    result = pd.Series(pct_values, dtype=float)

    valid_count = result.notna().sum()
    logger.info(
        f"Price vs high: {int(valid_count)}/{len(tickers)} tickers computed"
    )

    return result


# ---------------------------------------------------------------------------
# Combined: Calculate All Factors
# ---------------------------------------------------------------------------

def calculate_all_factors(
    price_data: dict[str, pd.DataFrame],
    fundamentals: dict[str, dict],
    tickers: list[str],
) -> pd.DataFrame:
    """Calculate all 4 factors and return combined DataFrame.

    Calls each individual factor function and merges results into a single
    DataFrame.  Tickers with NaN in any factor are included but can be
    identified via the ``has_all_factors`` column.

    Args:
        price_data: dict mapping ticker -> DataFrame with 'close' and 'date'
            columns.
        fundamentals: dict mapping ticker -> dict with 'eps' and 'revenue'
            DataFrames.
        tickers: list of tickers to calculate for.

    Returns:
        pd.DataFrame with columns:
            - ticker
            - rs_percentile (0-100)
            - eps_growth (%)
            - revenue_growth (%)
            - price_vs_high (0-100)
            - has_all_factors (bool)
    """
    logger.info(f"Calculating all factors for {len(tickers)} tickers")

    rs = calc_rs_percentile(price_data, tickers)
    eps = calc_eps_growth(fundamentals, tickers)
    rev = calc_revenue_growth(fundamentals, tickers)
    pvh = calc_price_vs_high(price_data, tickers)

    result = pd.DataFrame({
        "ticker": tickers,
        "rs_percentile": rs.reindex(tickers).values,
        "eps_growth": eps.reindex(tickers).values,
        "revenue_growth": rev.reindex(tickers).values,
        "price_vs_high": pvh.reindex(tickers).values,
    })

    result["has_all_factors"] = result[
        ["rs_percentile", "eps_growth", "revenue_growth", "price_vs_high"]
    ].notna().all(axis=1)

    complete = result["has_all_factors"].sum()
    logger.info(
        f"Factor calculation complete: {int(complete)}/{len(tickers)} tickers "
        f"have all 4 factors"
    )

    return result
