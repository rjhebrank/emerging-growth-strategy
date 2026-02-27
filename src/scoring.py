"""Scoring, ranking, and signal generation for the Emerging Growth Strategy.

Applies quality filters, computes composite scores, enforces sector caps,
ranks stocks, and generates BUY/SELL/HOLD signals for monthly rebalancing.

Pipeline:
    factors_df -> apply_quality_filters -> calc_composite_score
               -> select_top_n -> enforce_sector_cap -> generate_signals
               -> format_report
"""

import logging
from datetime import date

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REQUIRED_FACTOR_COLS = [
    "ticker",
    "rs_percentile",
    "eps_growth",
    "revenue_growth",
    "price_vs_high",
]

# Quality gate thresholds
_MIN_EPS_GROWTH = 5.0        # percent
_MIN_REVENUE_GROWTH = 5.0    # percent
_MIN_PRICE_VS_HIGH = 75.0    # percent of 52-week high

# Composite score weights (must sum to 1.0)
_W_RS = 0.40
_W_EPS = 0.20
_W_REV = 0.20
_W_PRICE = 0.20

# Growth cap for composite calculation (prevents outlier domination)
_GROWTH_CAP = 100.0

# Default portfolio size and sector cap
_DEFAULT_N = 25
_DEFAULT_SECTOR_CAP = 0.40

# Signal ordering for sort
_SIGNAL_ORDER = {"BUY": 0, "HOLD": 1, "SELL": 2}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_columns(df: pd.DataFrame, required: list[str], context: str) -> None:
    """Raise KeyError if required columns are missing from df."""
    missing = set(required) - set(df.columns)
    if missing:
        raise KeyError(f"{context}: missing required columns {sorted(missing)}")


# ---------------------------------------------------------------------------
# Function 1: Quality Filters
# ---------------------------------------------------------------------------

def apply_quality_filters(factors_df: pd.DataFrame) -> pd.DataFrame:
    """Apply all three quality gates simultaneously.

    Gates (ALL must pass):
        1. EPS growth >= 5%
        2. Revenue growth >= 5%
        3. Price vs 52-week high >= 75%

    Args:
        factors_df: DataFrame with columns: ticker, rs_percentile,
            eps_growth, revenue_growth, price_vs_high

    Returns:
        Filtered DataFrame with only qualifying tickers, fresh 0-based index.

    Raises:
        KeyError: If a required column is missing.
    """
    _validate_columns(factors_df, _REQUIRED_FACTOR_COLS, "apply_quality_filters")

    total = len(factors_df)
    if total == 0:
        logger.warning("apply_quality_filters: received empty DataFrame")
        return factors_df.copy()

    # Evaluate each gate independently for logging
    eps_mask = factors_df["eps_growth"] >= _MIN_EPS_GROWTH
    rev_mask = factors_df["revenue_growth"] >= _MIN_REVENUE_GROWTH
    price_mask = factors_df["price_vs_high"] >= _MIN_PRICE_VS_HIGH

    n_eps = int(eps_mask.sum())
    n_rev = int(rev_mask.sum())
    n_price = int(price_mask.sum())

    logger.info(f"Quality gate — EPS growth >= {_MIN_EPS_GROWTH}%: {n_eps}/{total} pass")
    logger.info(f"Quality gate — Revenue growth >= {_MIN_REVENUE_GROWTH}%: {n_rev}/{total} pass")
    logger.info(f"Quality gate — Price vs 52wk high >= {_MIN_PRICE_VS_HIGH}%: {n_price}/{total} pass")

    # All three gates must pass
    combined_mask = eps_mask & rev_mask & price_mask
    n_all = int(combined_mask.sum())
    logger.info(f"Quality gate — ALL gates combined: {n_all}/{total} pass")

    filtered = factors_df[combined_mask].copy()
    return filtered.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Function 2: Composite Score
# ---------------------------------------------------------------------------

def calc_composite_score(factors_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate composite score for all tickers in the DataFrame.

    Formula:
        score = 0.40 * rs_percentile
              + 0.20 * min(eps_growth, 100)
              + 0.20 * min(revenue_growth, 100)
              + 0.20 * price_vs_high

    The min() capping prevents outliers (e.g., 999% turnaround earnings)
    from dominating the score.  All components are on a 0-100 scale, so
    the composite is also 0-100.

    Args:
        factors_df: DataFrame with columns: rs_percentile, eps_growth,
            revenue_growth, price_vs_high

    Returns:
        DataFrame with added columns ``composite_score`` and ``rank``,
        sorted by composite_score descending.  Rank 1 = highest score.
    """
    required = ["rs_percentile", "eps_growth", "revenue_growth", "price_vs_high"]
    _validate_columns(factors_df, required, "calc_composite_score")

    df = factors_df.copy()

    if df.empty:
        df["composite_score"] = pd.Series(dtype=float)
        df["rank"] = pd.Series(dtype=int)
        return df

    # Cap growth values to prevent outlier domination
    capped_eps = np.minimum(df["eps_growth"].values, _GROWTH_CAP)
    capped_rev = np.minimum(df["revenue_growth"].values, _GROWTH_CAP)

    df["composite_score"] = (
        _W_RS * df["rs_percentile"]
        + _W_EPS * capped_eps
        + _W_REV * capped_rev
        + _W_PRICE * df["price_vs_high"]
    ).round(2)

    # Sort descending by composite score, then by rs_percentile (tiebreak),
    # then alphabetical by ticker (second tiebreak)
    df = df.sort_values(
        by=["composite_score", "rs_percentile", "ticker"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    df["rank"] = np.arange(1, len(df) + 1)

    logger.info(
        f"Composite scores: min={df['composite_score'].min():.1f}, "
        f"max={df['composite_score'].max():.1f}, "
        f"median={df['composite_score'].median():.1f}"
    )

    return df


# ---------------------------------------------------------------------------
# Function 3: Select Top N
# ---------------------------------------------------------------------------

def select_top_n(scored_df: pd.DataFrame, n: int = _DEFAULT_N) -> pd.DataFrame:
    """Select top N stocks by composite score.

    Tiebreaking: if two stocks have the same composite score, the one with
    a higher rs_percentile wins.  If still tied, alphabetical by ticker.

    Args:
        scored_df: DataFrame with composite_score column, sorted descending.
        n: Number of stocks to select (default 25).

    Returns:
        Top N rows with ``target_weight`` column added (1/n for each).
    """
    if scored_df.empty:
        logger.warning("select_top_n: received empty DataFrame")
        result = scored_df.copy()
        result["target_weight"] = pd.Series(dtype=float)
        return result

    # Re-sort with full tiebreaking to be safe
    df = scored_df.sort_values(
        by=["composite_score", "rs_percentile", "ticker"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    actual_n = min(n, len(df))
    if actual_n < n:
        logger.warning(
            f"select_top_n: only {actual_n} qualified stocks available "
            f"(requested {n})"
        )

    top = df.head(actual_n).copy()
    top["target_weight"] = round(1.0 / n, 4)

    # Re-rank after selection (in case input rank was stale)
    top["rank"] = np.arange(1, len(top) + 1)

    logger.info(
        f"Selected top {actual_n} stocks, "
        f"target weight = {top['target_weight'].iloc[0]:.2%} each"
    )

    return top.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Function 4: Sector Cap Enforcement
# ---------------------------------------------------------------------------

def enforce_sector_cap(
    selected_df: pd.DataFrame,
    remaining_df: pd.DataFrame,
    sector_col: str = "sector",
    max_pct: float = _DEFAULT_SECTOR_CAP,
    n: int = _DEFAULT_N,
) -> pd.DataFrame:
    """Enforce maximum sector concentration.

    If any sector has more than max_pct of positions (e.g., > 10 of 25),
    drop the lowest-scoring stock in that sector and replace with the
    next highest-scoring stock from a different sector in the remaining
    pool.  Repeat until no sector exceeds the cap.

    Args:
        selected_df: Current top N stocks.
        remaining_df: All other qualified stocks (replacement pool),
            sorted by composite_score descending.
        sector_col: Column name for sector data.
        max_pct: Maximum fraction of portfolio per sector (default 0.40).
        n: Total portfolio size.

    Returns:
        Adjusted DataFrame after sector cap enforcement.

    Note:
        If sector_col doesn't exist in the DataFrame, skip enforcement
        and return selected_df unchanged (sector data may not be available).
    """
    if sector_col not in selected_df.columns:
        logger.info(
            f"enforce_sector_cap: column '{sector_col}' not found, "
            f"skipping sector cap enforcement"
        )
        return selected_df.copy()

    if selected_df.empty:
        return selected_df.copy()

    max_per_sector = int(np.floor(max_pct * n))
    if max_per_sector < 1:
        max_per_sector = 1

    # Work on copies so we don't mutate the caller's data
    portfolio = selected_df.copy()
    pool = remaining_df.copy()

    # Ensure pool is sorted by score descending for replacement priority
    if "composite_score" in pool.columns:
        pool = pool.sort_values(
            by=["composite_score", "rs_percentile", "ticker"],
            ascending=[False, False, True],
        ).reset_index(drop=True)

    # Remove any pool tickers already in portfolio
    pool = pool[~pool["ticker"].isin(portfolio["ticker"])]

    iterations = 0
    max_iterations = len(selected_df) * 2  # safety valve

    while iterations < max_iterations:
        sector_counts = portfolio[sector_col].value_counts()
        violating = sector_counts[sector_counts > max_per_sector]

        if violating.empty:
            break

        # Pick the worst offending sector (most over the cap)
        worst_sector = violating.index[0]
        over_count = int(violating.iloc[0])

        logger.info(
            f"Sector cap violation: {worst_sector} has {over_count} stocks "
            f"(max {max_per_sector})"
        )

        # Drop the lowest-scoring stock in the violating sector
        sector_stocks = portfolio[portfolio[sector_col] == worst_sector]
        drop_ticker = sector_stocks.sort_values(
            "composite_score", ascending=True
        ).iloc[0]["ticker"]

        portfolio = portfolio[portfolio["ticker"] != drop_ticker].reset_index(drop=True)
        logger.info(f"Dropped {drop_ticker} from {worst_sector}")

        # Find the best replacement from a non-violating sector
        # Exclude sectors currently at their cap
        current_counts = portfolio[sector_col].value_counts()
        full_sectors = set(
            current_counts[current_counts >= max_per_sector].index
        )

        eligible_pool = pool[~pool[sector_col].isin(full_sectors)]

        if eligible_pool.empty:
            logger.warning(
                "No eligible replacement found outside capped sectors; "
                f"portfolio will have {len(portfolio)} stocks"
            )
            break

        replacement = eligible_pool.iloc[0]
        replacement_ticker = replacement["ticker"]

        # Add the replacement to portfolio
        portfolio = pd.concat(
            [portfolio, replacement.to_frame().T],
            ignore_index=True,
        )

        # Remove replacement from pool
        pool = pool[pool["ticker"] != replacement_ticker].reset_index(drop=True)

        logger.info(
            f"Replaced with {replacement_ticker} "
            f"(sector: {replacement[sector_col]}, "
            f"score: {replacement['composite_score']:.1f})"
        )

        iterations += 1

    if iterations >= max_iterations:
        logger.warning(
            f"Sector cap enforcement hit iteration limit ({max_iterations})"
        )

    # Re-sort and re-rank
    portfolio = portfolio.sort_values(
        by=["composite_score", "rs_percentile", "ticker"],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    portfolio["rank"] = np.arange(1, len(portfolio) + 1)

    # Recompute target_weight in case portfolio size changed
    actual_n = len(portfolio)
    portfolio["target_weight"] = round(1.0 / n, 4)

    logger.info(f"After sector cap enforcement: {actual_n} stocks in portfolio")

    return portfolio


# ---------------------------------------------------------------------------
# Function 5: Signal Generation
# ---------------------------------------------------------------------------

def generate_signals(
    current_top25: pd.DataFrame,
    prior_top25: list[str] | None = None,
) -> pd.DataFrame:
    """Generate BUY/SELL/HOLD signals by comparing to prior month.

    Signal logic:
        - BUY:  ticker in current top 25 but NOT in prior holdings
        - SELL: ticker in prior holdings but NOT in current top 25
        - HOLD: ticker in BOTH current and prior

    If prior_top25 is None (first month), all current are BUY signals.

    Args:
        current_top25: DataFrame with current month's top 25. Must have
            at least columns: ticker, composite_score, rank
        prior_top25: List of ticker strings from prior month, or None.

    Returns:
        DataFrame with columns: ticker, signal, composite_score, rank,
        rs_percentile, eps_growth, revenue_growth, price_vs_high.
        Sorted: BUY first, then HOLD, then SELL (each group by rank).
    """
    if current_top25.empty and not prior_top25:
        logger.warning("generate_signals: no current or prior positions")
        return pd.DataFrame(columns=[
            "ticker", "signal", "composite_score", "rank",
            "rs_percentile", "eps_growth", "revenue_growth", "price_vs_high",
        ])

    current_tickers = set(current_top25["ticker"].tolist()) if not current_top25.empty else set()
    prior_set = set(prior_top25) if prior_top25 else set()

    buy_tickers = current_tickers - prior_set
    hold_tickers = current_tickers & prior_set
    sell_tickers = prior_set - current_tickers

    logger.info(
        f"Signals: {len(buy_tickers)} BUY, "
        f"{len(hold_tickers)} HOLD, "
        f"{len(sell_tickers)} SELL"
    )

    # Build the output columns we want
    output_cols = [
        "ticker", "signal", "composite_score", "rank",
        "rs_percentile", "eps_growth", "revenue_growth", "price_vs_high",
    ]

    rows: list[dict] = []

    # BUY and HOLD signals come from the current DataFrame
    if not current_top25.empty:
        for _, row in current_top25.iterrows():
            ticker = row["ticker"]
            if ticker in buy_tickers:
                signal = "BUY"
            elif ticker in hold_tickers:
                signal = "HOLD"
            else:
                continue  # shouldn't happen, but defensive

            entry = {"ticker": ticker, "signal": signal}
            for col in output_cols[2:]:  # skip ticker, signal
                entry[col] = row.get(col, np.nan)
            rows.append(entry)

    # SELL signals: tickers no longer in current top 25
    for ticker in sorted(sell_tickers):
        entry = {
            "ticker": ticker,
            "signal": "SELL",
            "composite_score": np.nan,
            "rank": np.nan,
            "rs_percentile": np.nan,
            "eps_growth": np.nan,
            "revenue_growth": np.nan,
            "price_vs_high": np.nan,
        }
        rows.append(entry)

    signals_df = pd.DataFrame(rows, columns=output_cols)

    # Sort: BUY first, then HOLD, then SELL; within each group by rank
    signals_df["_signal_order"] = signals_df["signal"].map(_SIGNAL_ORDER)
    signals_df = signals_df.sort_values(
        by=["_signal_order", "rank", "ticker"],
        ascending=[True, True, True],
        na_position="last",
    ).reset_index(drop=True)
    signals_df = signals_df.drop(columns=["_signal_order"])

    return signals_df


# ---------------------------------------------------------------------------
# Function 6: Format Report
# ---------------------------------------------------------------------------

def format_report(
    signals_df: pd.DataFrame,
    screening_stats: dict | None = None,
) -> str:
    """Format the signals into a human-readable text report.

    Args:
        signals_df: DataFrame from generate_signals() with columns:
            ticker, signal, composite_score, rank, rs_percentile,
            eps_growth, revenue_growth, price_vs_high
        screening_stats: Optional dict with keys like 'total_input',
            'total_passed' for the screening summary section.

    Returns:
        Multi-line string formatted for terminal or file output.
    """
    today_str = date.today().strftime("%Y-%m-%d")

    lines: list[str] = []

    # Header
    lines.append("")
    lines.append("\u2550" * 47)
    lines.append("  EMERGING GROWTH STRATEGY \u2014 MONTHLY REPORT")
    lines.append(f"  Date: {today_str}")
    lines.append("\u2550" * 47)
    lines.append("")

    # Screening summary
    if screening_stats:
        lines.append("SCREENING SUMMARY")
        lines.append("\u2500" * 20)
        total_in = screening_stats.get("total_input", "N/A")
        total_pass = screening_stats.get("total_passed", "N/A")
        lines.append(f"  Universe: {total_in:,} tickers" if isinstance(total_in, int) else f"  Universe: {total_in} tickers")
        lines.append(f"  Passed quality filters: {total_pass:,}" if isinstance(total_pass, int) else f"  Passed quality filters: {total_pass}")
        lines.append("")

    # Split signals by type
    buy_df = signals_df[signals_df["signal"] == "BUY"] if not signals_df.empty else pd.DataFrame()
    hold_df = signals_df[signals_df["signal"] == "HOLD"] if not signals_df.empty else pd.DataFrame()
    sell_df = signals_df[signals_df["signal"] == "SELL"] if not signals_df.empty else pd.DataFrame()

    # Table header for signal sections
    table_header = (
        f"  {'Rank':<6}{'Ticker':<10}{'Score':>7}{'RS':>6}"
        f"{'EPS%':>8}{'Rev%':>8}{'P/High':>8}"
    )
    table_sep = "  " + "-" * 51

    # BUY signals
    lines.append(f"\u2550\u2550\u2550 BUY SIGNALS ({len(buy_df)} new positions) \u2550\u2550\u2550")
    if buy_df.empty:
        lines.append("  (none)")
    else:
        lines.append(table_header)
        lines.append(table_sep)
        for _, row in buy_df.iterrows():
            lines.append(_format_signal_row(row))
    lines.append("")

    # HOLD signals
    lines.append(f"\u2550\u2550\u2550 HOLD SIGNALS ({len(hold_df)} continuing) \u2550\u2550\u2550")
    if hold_df.empty:
        lines.append("  (none)")
    else:
        lines.append(table_header)
        lines.append(table_sep)
        for _, row in hold_df.iterrows():
            lines.append(_format_signal_row(row))
    lines.append("")

    # SELL signals
    lines.append(f"\u2550\u2550\u2550 SELL SIGNALS ({len(sell_df)} exits) \u2550\u2550\u2550")
    if sell_df.empty:
        lines.append("  (none)")
    else:
        lines.append(table_header)
        lines.append(table_sep)
        for _, row in sell_df.iterrows():
            lines.append(_format_signal_row(row))
    lines.append("")

    # Portfolio summary
    n_buy = len(buy_df)
    n_hold = len(hold_df)
    n_sell = len(sell_df)
    n_positions = n_buy + n_hold
    weight_pct = (100.0 / n_positions) if n_positions > 0 else 0.0
    prior_count = n_hold + n_sell
    turnover_pct = (n_buy / prior_count * 100) if prior_count > 0 else 100.0

    lines.append("PORTFOLIO SUMMARY")
    lines.append("\u2500" * 20)
    lines.append(f"  Positions: {n_positions} | Weight: {weight_pct:.1f}% each")
    lines.append(f"  New positions: {n_buy} | Turnover: {turnover_pct:.0f}%")
    lines.append("")

    return "\n".join(lines)


def _format_signal_row(row: pd.Series) -> str:
    """Format a single signal row for the text report table."""
    rank_str = str(int(row["rank"])) if pd.notna(row.get("rank")) else "-"
    ticker = str(row["ticker"])
    score = f"{row['composite_score']:.1f}" if pd.notna(row.get("composite_score")) else "-"
    rs = f"{row['rs_percentile']:.0f}" if pd.notna(row.get("rs_percentile")) else "-"
    eps = f"{row['eps_growth']:.1f}" if pd.notna(row.get("eps_growth")) else "-"
    rev = f"{row['revenue_growth']:.1f}" if pd.notna(row.get("revenue_growth")) else "-"
    p_high = f"{row['price_vs_high']:.1f}" if pd.notna(row.get("price_vs_high")) else "-"

    return (
        f"  {rank_str:<6}{ticker:<10}{score:>7}{rs:>6}"
        f"{eps:>8}{rev:>8}{p_high:>8}"
    )
