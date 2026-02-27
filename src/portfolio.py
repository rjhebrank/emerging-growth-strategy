"""Portfolio construction and rebalancing calculations.

Assigns equal 4% weights to top 25 stocks and computes the trade list
needed to transition from the current portfolio to the target allocation.

Rebalancing rules:
    - SELL signals: liquidate entire position
    - BUY signals: open new position at target weight
    - HOLD signals with drift:
        - Weight > 6%: trim back to 4%
        - Weight < 2%: add to reach 4%
        - 2% <= weight <= 6%: no trade needed
    - Transaction cost estimate: 10 bps per trade
"""

import logging
import math

import pandas as pd

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_PORTFOLIO_VALUE = 100_000.0
TARGET_WEIGHT = 0.04          # 1/25 = 4%
TRIM_THRESHOLD = 0.06         # Trim if weight exceeds 6%
ADD_THRESHOLD = 0.02          # Add if weight falls below 2%
COST_BPS = 10.0               # 10 basis points per trade


# ---------------------------------------------------------------------------
# Portfolio construction
# ---------------------------------------------------------------------------

def build_portfolio(
    top25: pd.DataFrame,
    portfolio_value: float = DEFAULT_PORTFOLIO_VALUE,
) -> pd.DataFrame:
    """Assign equal 4% weights to top 25 stocks.

    Args:
        top25: DataFrame with columns including 'ticker' and 'price'.
        portfolio_value: Total portfolio value in dollars.

    Returns:
        DataFrame with columns:
            ticker, target_weight (0.04), target_dollars, price,
            target_shares (floor to int), actual_dollars, actual_weight
    """
    if top25.empty:
        logger.warning("build_portfolio called with empty DataFrame")
        return pd.DataFrame(columns=[
            "ticker", "target_weight", "target_dollars", "price",
            "target_shares", "actual_dollars", "actual_weight",
        ])

    n = len(top25)
    weight = 1.0 / n  # 0.04 for 25 stocks

    result = pd.DataFrame({
        "ticker": top25["ticker"].values,
        "target_weight": weight,
        "target_dollars": weight * portfolio_value,
        "price": top25["price"].values,
    })

    # Floor to whole shares (no fractional shares)
    result["target_shares"] = result.apply(
        lambda row: math.floor(row["target_dollars"] / row["price"])
        if row["price"] > 0 and pd.notna(row["price"])
        else 0,
        axis=1,
    )

    result["actual_dollars"] = result["target_shares"] * result["price"]
    result["actual_weight"] = result["actual_dollars"] / portfolio_value

    total_invested = result["actual_dollars"].sum()
    cash_remainder = portfolio_value - total_invested

    logger.info(
        f"Portfolio built: {n} positions, "
        f"${total_invested:,.0f} invested, "
        f"${cash_remainder:,.0f} cash remainder"
    )

    return result


# ---------------------------------------------------------------------------
# Rebalancing
# ---------------------------------------------------------------------------

def calc_rebalance_trades(
    current_holdings: pd.DataFrame | None,
    target_portfolio: pd.DataFrame,
    signals: pd.DataFrame,
) -> pd.DataFrame:
    """Compute trade list with dollar amounts and share counts.

    For SELL signals: sell entire position
    For BUY signals: buy target_shares at current price
    For HOLD signals: calculate drift from 4% target
        - If weight > 6%: trim to 4% (sell excess shares)
        - If weight < 2%: add to reach 4% (buy additional shares)
        - If 2% <= weight <= 6%: no rebalance trade needed

    Args:
        current_holdings: Prior month holdings DataFrame with columns:
            ticker, shares, price, actual_dollars, actual_weight.
            None if this is the first month.
        target_portfolio: From build_portfolio(). Must contain:
            ticker, target_shares, price.
        signals: DataFrame with at least 'ticker' and 'action' columns,
            where action is one of 'BUY', 'SELL', 'HOLD'.

    Returns:
        DataFrame with columns:
            ticker, action (BUY/SELL/TRIM/ADD), shares, price,
            dollar_amount, estimated_cost_bps (10 bps per trade)
    """
    trades: list[dict] = []

    # Build lookup dicts for fast access
    target_lookup = {}
    if not target_portfolio.empty:
        for _, row in target_portfolio.iterrows():
            target_lookup[row["ticker"]] = row

    holdings_lookup = {}
    if current_holdings is not None and not current_holdings.empty:
        for _, row in current_holdings.iterrows():
            holdings_lookup[row["ticker"]] = row

    for _, sig in signals.iterrows():
        ticker = sig["ticker"]
        action = sig["action"]

        if action == "SELL":
            # Sell entire position
            held = holdings_lookup.get(ticker)
            if held is not None:
                shares = int(held.get("shares", held.get("target_shares", 0)))
                price = float(held.get("price", 0.0))
            else:
                # No current holding data available -- nothing to sell
                logger.debug(f"SELL signal for {ticker} but no current holding found")
                shares = 0
                price = 0.0

            dollar_amount = shares * price
            trades.append({
                "ticker": ticker,
                "action": "SELL",
                "shares": -shares,
                "price": price,
                "dollar_amount": -dollar_amount,
                "estimated_cost_bps": dollar_amount * COST_BPS / 10_000,
            })

        elif action == "BUY":
            # Buy new position at target shares
            target = target_lookup.get(ticker)
            if target is not None:
                shares = int(target.get("target_shares", 0))
                price = float(target.get("price", 0.0))
            else:
                logger.warning(f"BUY signal for {ticker} but not found in target portfolio")
                shares = 0
                price = 0.0

            dollar_amount = shares * price
            trades.append({
                "ticker": ticker,
                "action": "BUY",
                "shares": shares,
                "price": price,
                "dollar_amount": dollar_amount,
                "estimated_cost_bps": dollar_amount * COST_BPS / 10_000,
            })

        elif action == "HOLD":
            # Check for drift and rebalance if needed
            held = holdings_lookup.get(ticker)
            target = target_lookup.get(ticker)

            if held is None or target is None:
                # If no prior holding, treat as a BUY
                if target is not None and held is None:
                    shares = int(target.get("target_shares", 0))
                    price = float(target.get("price", 0.0))
                    dollar_amount = shares * price
                    trades.append({
                        "ticker": ticker,
                        "action": "BUY",
                        "shares": shares,
                        "price": price,
                        "dollar_amount": dollar_amount,
                        "estimated_cost_bps": dollar_amount * COST_BPS / 10_000,
                    })
                continue

            current_weight = float(held.get("actual_weight", TARGET_WEIGHT))
            price = float(target.get("price", held.get("price", 0.0)))
            current_shares = int(held.get("shares", held.get("target_shares", 0)))
            target_shares = int(target.get("target_shares", 0))

            if current_weight > TRIM_THRESHOLD:
                # Trim: sell excess shares to bring back to target
                excess_shares = current_shares - target_shares
                if excess_shares > 0:
                    dollar_amount = excess_shares * price
                    trades.append({
                        "ticker": ticker,
                        "action": "TRIM",
                        "shares": -excess_shares,
                        "price": price,
                        "dollar_amount": -dollar_amount,
                        "estimated_cost_bps": dollar_amount * COST_BPS / 10_000,
                    })

            elif current_weight < ADD_THRESHOLD:
                # Add: buy additional shares to bring back to target
                needed_shares = target_shares - current_shares
                if needed_shares > 0:
                    dollar_amount = needed_shares * price
                    trades.append({
                        "ticker": ticker,
                        "action": "ADD",
                        "shares": needed_shares,
                        "price": price,
                        "dollar_amount": dollar_amount,
                        "estimated_cost_bps": dollar_amount * COST_BPS / 10_000,
                    })
            # else: within 2%-6% tolerance band, no trade needed

    trade_df = pd.DataFrame(trades, columns=[
        "ticker", "action", "shares", "price",
        "dollar_amount", "estimated_cost_bps",
    ])

    if trade_df.empty:
        logger.info("Rebalance: no trades needed")
    else:
        total_cost = trade_df["estimated_cost_bps"].sum()
        buy_count = (trade_df["action"] == "BUY").sum()
        sell_count = (trade_df["action"] == "SELL").sum()
        trim_count = (trade_df["action"] == "TRIM").sum()
        add_count = (trade_df["action"] == "ADD").sum()
        logger.info(
            f"Rebalance: {len(trade_df)} trades "
            f"({buy_count} BUY, {sell_count} SELL, {trim_count} TRIM, {add_count} ADD), "
            f"estimated cost ${total_cost:,.2f}"
        )

    return trade_df
