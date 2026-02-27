# 04 - Backtesting Framework: Implementation Guide

## 1. Overview

### Purpose

Validate the Emerging Growth Strategy with rigorous historical backtesting across 11 years of market data. The backtest must answer one question definitively: **does this strategy produce risk-adjusted returns superior to passive small-cap indexing, net of transaction costs, without data snooping or look-ahead bias?**

### Backtest Parameters

| Parameter | Value |
|---|---|
| Period | January 2014 - December 2024 (11 years) |
| Rebalance Frequency | Monthly (first trading day of each month) |
| Rebalances | 132 total |
| Starting Capital | $100,000 (arbitrary, results scale linearly) |
| Positions | 25 equal-weighted at 4% each |
| Transaction Cost | 10 bps (0.10%) per trade |
| Data Source | Sharadar (point-in-time fundamentals + daily prices) |
| Benchmark 1 | S&P 500 (SPY) |
| Benchmark 2 | iShares Core S&P Small-Cap ETF (IJR) |

### Key Results (Target to Reproduce)

| Metric | Value |
|---|---|
| Total Return | 428% |
| CAGR | 16.66% |
| Sharpe Ratio | 1.054 |
| Max Drawdown | -22.68% |
| Total Trades | 1,535 |
| Win Rate | 50.36% |
| Profit Factor | 1.80 |

### Core Principle: Point-in-Time Data Integrity

Every data point used in the backtest must have been available to a real trader on the rebalance date. No exceptions. No shortcuts. This is the single most important requirement in the entire framework. Violating it produces meaningless results that overstate performance, sometimes dramatically.

---

## 2. Monthly Rebalancing Mechanics

### Rebalance Day Procedure

On the **first trading day of each calendar month**, execute the following steps in order:

#### Step 1: Reconstruct the Universe

Apply all universe filters using only data available on the rebalance date:

- Market cap between $50M and $10B (using prior close price x shares outstanding)
- Average daily dollar volume >= $1M over trailing 20 trading days
- Stock price >= $2.00
- Listed on NYSE, NASDAQ, or AMEX
- Exclude ADRs, REITs, SPACs, and financials (SIC/NAICS codes)
- Include stocks that were later delisted (survivorship bias prevention)

#### Step 2: Compute the 4-Factor Composite Score

Using ONLY data available on the rebalance date (see Section 4 for point-in-time rules):

| Factor | Weight | Calculation |
|---|---|---|
| RS Percentile | 40% | 6-month price return ranked vs. universe, percentile 0-100 |
| EPS Growth | 20% | YoY quarterly EPS growth from most recent AVAILABLE quarter |
| Revenue Growth | 20% | YoY quarterly revenue growth from most recent AVAILABLE quarter |
| Price vs 52-Week High | 20% | Current price / 52-week high, scaled 0-100 |

```
composite_score = (rs_percentile * 0.40) +
                  (eps_growth_score * 0.20) +
                  (rev_growth_score * 0.20) +
                  (price_vs_high_score * 0.20)
```

#### Step 3: Apply Quality Filters

Remove stocks that fail minimum thresholds:

- EPS Growth < 5% (YoY) -- eliminated
- Revenue Growth < 5% (YoY) -- eliminated
- Price / 52-Week High < 75% -- eliminated (too far from highs)

#### Step 4: Rank and Select Top 25

Sort remaining stocks by composite score descending. Select the top 25.

#### Step 5: Generate Trade Signals

Compare the new top-25 list against the current portfolio:

- **SELL**: Positions in the current portfolio that are NOT in the new top 25
- **BUY**: Stocks in the new top 25 that are NOT in the current portfolio
- **HOLD**: Stocks in both the current portfolio and the new top 25

#### Step 6: Execute Trades

Execute in this exact order to manage cash correctly:

1. **Sell all SELL positions** -- liquidate at the rebalance day's closing price, deduct 10 bps
2. **Rebalance HOLD positions** -- calculate current weight, trim or add to reach 4% target
3. **Buy all BUY positions** -- allocate remaining cash equally among new buys, deduct 10 bps
4. **Cash residual** -- any leftover cash (from rounding) stays as uninvested cash

### Equal Weighting Math

```python
target_value_per_position = total_portfolio_value * 0.04  # 4% each
shares_to_buy = int(target_value_per_position / stock_price)  # round down to whole shares
actual_cost = shares_to_buy * stock_price * (1 + 0.001)       # add 10 bps transaction cost
```

### Edge Cases at Period Boundaries

- **First month (Jan 2014):** No prior portfolio exists. Buy all 25 positions from cash.
- **Last month (Dec 2024):** Run the final rebalance, then mark-to-market through Dec 31.
- **Partial first/last month:** If the backtest starts mid-month, run the first rebalance at the next month boundary. Track daily portfolio value from day one regardless.

---

## 3. Transaction Cost Modeling

### Base Model: 10 Basis Points Per Trade

Every trade (buy or sell) incurs a 10 bps (0.10%) cost deducted from the trade value.

**Implementation:**

```python
TRANSACTION_COST_BPS = 10  # basis points
TRANSACTION_COST_PCT = TRANSACTION_COST_BPS / 10_000  # 0.001

def execute_buy(price: float, shares: int) -> float:
    """Returns total cost of purchase including transaction fees."""
    gross_cost = price * shares
    fee = gross_cost * TRANSACTION_COST_PCT
    return gross_cost + fee

def execute_sell(price: float, shares: int) -> float:
    """Returns net proceeds from sale after transaction fees."""
    gross_proceeds = price * shares
    fee = gross_proceeds * TRANSACTION_COST_PCT
    return gross_proceeds - fee
```

### What the 10 bps Covers

- **Bid-ask spread impact:** Small-cap stocks typically have 5-20 bps effective spreads. The 10 bps assumption is moderate.
- **Market impact:** For $4,000 position sizes ($100K / 25), market impact on stocks with >$1M daily volume is negligible.
- **ECN/exchange fees:** Typically 0.3 bps or less -- included in the 10 bps.

### What Is NOT Modeled (and Why)

| Factor | Why Not Modeled | Risk |
|---|---|---|
| Commissions | $0 at all major brokers since 2019 | None |
| Explicit slippage | Covered by 10 bps estimate | Low for $4K positions |
| Short-sale costs | Strategy is long-only | N/A |
| Tax drag | Varies by account type; see note | Medium |
| Margin interest | Strategy uses no leverage | N/A |

**Tax note:** In a taxable account, monthly rebalancing generates short-term capital gains taxed at ordinary income rates. In a tax-advantaged account (IRA/401k), this is irrelevant. The backtest reports pre-tax returns. For a rough post-tax estimate in a taxable account, reduce CAGR by 2-4 percentage points depending on tax bracket and turnover.

### Sensitivity Analysis

Run the full backtest at multiple cost levels to confirm robustness:

| Cost (bps) | Expected Impact on CAGR |
|---|---|
| 0 (frictionless) | ~+0.5-1.0% |
| 5 | ~+0.3% |
| 10 (base case) | baseline |
| 20 | ~-0.5% |
| 50 (stress test) | ~-1.5% |

If the strategy is profitable only at 0 bps, it is not tradeable. It should remain profitable at 20+ bps.

---

## 4. Point-in-Time Data Requirements (CRITICAL)

This section is the most important in the entire document. Look-ahead bias is the number one cause of backtests that look great on paper and fail in live trading.

### The Golden Rule

> **At rebalance date T, you may only use data that a real trader could have accessed on date T.**

### Fundamental Data: Sharadar `datekey` Field

Sharadar provides a `datekey` field on every fundamental data row. This is the date the data became publicly available (i.e., the filing/reporting date). This is NOT the fiscal period end date.

**Correct usage:**

```python
def get_latest_fundamentals(ticker: str, rebalance_date: date) -> dict:
    """
    Get the most recent fundamental data available on the rebalance date.
    Uses Sharadar's datekey (public availability date), NOT the fiscal period end.
    """
    query = """
        SELECT *
        FROM sf1
        WHERE ticker = ?
          AND dimension = 'ARQ'          -- As-Reported Quarterly
          AND datekey <= ?               -- CRITICAL: only data available by this date
        ORDER BY datekey DESC
        LIMIT 1
    """
    return db.execute(query, [ticker, rebalance_date]).fetchone()
```

**Filing lag reality:**

| Quarter End | Typical Filing Date | Available For Rebalance |
|---|---|---|
| March 31 (Q1) | May 1 - May 15 | June 1 rebalance |
| June 30 (Q2) | Aug 1 - Aug 15 | September 1 rebalance |
| Sep 30 (Q3) | Nov 1 - Nov 15 | December 1 rebalance |
| Dec 31 (Q4) | Feb 15 - March 15 | March 1 or April 1 rebalance |

**Example:** For a January 1, 2024 rebalance:
- Q3 2023 (ending Sep 30) data filed ~Nov 15: **Available -- use it**
- Q4 2023 (ending Dec 31) data filed ~Feb 15: **NOT available -- do NOT use**
- You must use Q3 2023 as the "most recent" quarter

### YoY Growth Calculations

EPS Growth and Revenue Growth require comparing to the same quarter one year prior. Both quarters must pass the `datekey` test:

```python
def calc_yoy_eps_growth(ticker: str, rebalance_date: date) -> float:
    """
    Calculate YoY EPS growth using only point-in-time available data.
    Returns growth as a percentage (e.g., 25.0 for 25% growth).
    """
    # Most recent quarter with data available by rebalance_date
    current_q = get_latest_fundamentals(ticker, rebalance_date)
    if current_q is None:
        return None

    # Same fiscal quarter one year prior
    # calendardate is the fiscal period end (e.g., 2023-09-30)
    prior_year_end = current_q['calendardate'] - timedelta(days=365)

    prior_q = db.execute("""
        SELECT epsdil
        FROM sf1
        WHERE ticker = ?
          AND dimension = 'ARQ'
          AND calendardate BETWEEN ? AND ?  -- allow +/- 45 days for fiscal year alignment
          AND datekey <= ?                   -- must also have been available
        ORDER BY ABS(julianday(calendardate) - julianday(?))
        LIMIT 1
    """, [
        ticker,
        prior_year_end - timedelta(days=45),
        prior_year_end + timedelta(days=45),
        rebalance_date,
        prior_year_end
    ]).fetchone()

    if prior_q is None or prior_q['epsdil'] == 0:
        return None

    return ((current_q['epsdil'] - prior_q['epsdil']) / abs(prior_q['epsdil'])) * 100
```

### Price Data

- Use **adjusted close prices** (split-adjusted and dividend-adjusted) from Sharadar SEP table
- At rebalance date T, you may use closing prices through T (inclusive)
- 52-week high: maximum adjusted close from T-252 trading days through T
- 6-month return (RS): price at T / price at T-126 trading days

```python
def get_rs_percentile(ticker: str, rebalance_date: date, universe_tickers: list) -> float:
    """
    Calculate relative strength percentile within the universe.
    6-month price return ranked against all other universe members.
    """
    returns_126d = {}
    for t in universe_tickers:
        prices = get_prices(t, rebalance_date - timedelta(days=200), rebalance_date)
        if len(prices) < 100:  # need ~126 trading days, allow some gaps
            continue
        ret = (prices[-1] / prices[0]) - 1
        returns_126d[t] = ret

    if ticker not in returns_126d:
        return None

    rank = sum(1 for r in returns_126d.values() if r < returns_126d[ticker])
    percentile = (rank / len(returns_126d)) * 100
    return percentile
```

### Survivorship Bias Prevention

This is the second most critical data integrity issue after look-ahead bias.

**The problem:** Most stock databases only contain currently listed stocks. Stocks that were delisted, acquired, or went bankrupt are removed. This creates an upward bias because you only backtest on "survivors."

**The solution:**

1. Use Sharadar's full historical universe, which includes delisted securities
2. At each rebalance date, reconstruct the universe by including ALL tickers that were actively trading on that date
3. Check the `isdelisted` and `lastpricedate` fields

```python
def get_active_universe(rebalance_date: date) -> list:
    """
    Get all tickers that were actively trading on the rebalance date.
    Includes stocks that were later delisted.
    """
    return db.execute("""
        SELECT DISTINCT ticker
        FROM tickers
        WHERE firstpricedate <= ?
          AND (lastpricedate >= ? OR isdelisted = 'N')
          AND exchange IN ('NYSE', 'NASDAQ', 'NYSEMKT')
          AND category = 'Domestic Common Stock'
    """, [rebalance_date, rebalance_date]).fetchall()
```

### Common Look-Ahead Bias Traps

| Trap | Description | Prevention |
|---|---|---|
| Using `calendardate` instead of `datekey` | Fiscal period end != when data is public | Always filter on `datekey <= rebalance_date` |
| Adjusted prices from the future | Price adjustments for future splits applied retroactively | Use point-in-time adjusted prices or raw prices with manual split adjustment |
| Universe based on current listings | Excludes delisted stocks | Reconstruct universe at each date |
| Annual data availability | Annual reports (10-K) take 60-90 days after year-end | Use quarterly (10-Q) data with `datekey` check |
| Index membership hindsight | "Was in the S&P 600 on this date" based on current knowledge | Reconstruct index membership historically if used |

---

## 5. Portfolio Simulation Engine

### Data Structures

```python
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


@dataclass
class Position:
    """Represents a single stock holding in the portfolio."""
    ticker: str
    shares: int
    entry_price: float
    entry_date: date
    current_price: float = 0.0

    @property
    def market_value(self) -> float:
        return self.shares * self.current_price

    @property
    def cost_basis(self) -> float:
        return self.shares * self.entry_price

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def return_pct(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.market_value / self.cost_basis) - 1


@dataclass
class Trade:
    """Records a single buy or sell transaction."""
    date: date
    ticker: str
    action: str               # 'BUY' or 'SELL'
    shares: int
    price: float
    transaction_cost: float
    net_amount: float          # positive = cash inflow, negative = cash outflow
    entry_price: float = 0.0  # for SELL trades, the original entry price
    holding_days: int = 0     # for SELL trades, days held


@dataclass
class Portfolio:
    """
    Full portfolio state with positions, cash, and history tracking.
    """
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    trade_log: List[Trade] = field(default_factory=list)
    daily_values: List[dict] = field(default_factory=list)  # [{date, value}]

    @property
    def total_value(self) -> float:
        positions_value = sum(p.market_value for p in self.positions.values())
        return self.cash + positions_value

    def mark_to_market(self, prices: dict, as_of_date: date):
        """Update all position prices and record daily value."""
        for ticker, pos in self.positions.items():
            if ticker in prices:
                pos.current_price = prices[ticker]
        self.daily_values.append({
            'date': as_of_date,
            'value': self.total_value,
            'cash': self.cash,
            'num_positions': len(self.positions),
        })

    def execute_sell(self, ticker: str, price: float, sell_date: date,
                     cost_pct: float = 0.001) -> Optional[Trade]:
        """Sell entire position in a ticker."""
        if ticker not in self.positions:
            return None
        pos = self.positions[ticker]
        gross_proceeds = pos.shares * price
        fee = gross_proceeds * cost_pct
        net_proceeds = gross_proceeds - fee

        trade = Trade(
            date=sell_date,
            ticker=ticker,
            action='SELL',
            shares=pos.shares,
            price=price,
            transaction_cost=fee,
            net_amount=net_proceeds,
            entry_price=pos.entry_price,
            holding_days=(sell_date - pos.entry_date).days,
        )
        self.trade_log.append(trade)
        self.cash += net_proceeds
        del self.positions[ticker]
        return trade

    def execute_buy(self, ticker: str, price: float, target_value: float,
                    buy_date: date, cost_pct: float = 0.001) -> Optional[Trade]:
        """Buy shares of a ticker targeting a specific dollar value."""
        effective_price = price * (1 + cost_pct)
        shares = int(target_value / effective_price)
        if shares <= 0:
            return None
        gross_cost = shares * price
        fee = gross_cost * cost_pct
        total_cost = gross_cost + fee

        if total_cost > self.cash:
            # Reduce shares to fit available cash
            shares = int(self.cash / effective_price)
            if shares <= 0:
                return None
            gross_cost = shares * price
            fee = gross_cost * cost_pct
            total_cost = gross_cost + fee

        trade = Trade(
            date=buy_date,
            ticker=ticker,
            action='BUY',
            shares=shares,
            price=price,
            transaction_cost=fee,
            net_amount=-total_cost,
        )
        self.trade_log.append(trade)
        self.cash -= total_cost

        if ticker in self.positions:
            # Average into existing position
            existing = self.positions[ticker]
            total_shares = existing.shares + shares
            avg_price = ((existing.shares * existing.entry_price) +
                         (shares * price)) / total_shares
            existing.shares = total_shares
            existing.entry_price = avg_price
        else:
            self.positions[ticker] = Position(
                ticker=ticker,
                shares=shares,
                entry_price=price,
                entry_date=buy_date,
                current_price=price,
            )
        return trade

    def rebalance_position(self, ticker: str, price: float, target_value: float,
                           rebal_date: date, cost_pct: float = 0.001):
        """Rebalance an existing position to a target dollar value."""
        if ticker not in self.positions:
            return
        pos = self.positions[ticker]
        pos.current_price = price
        current_value = pos.market_value
        diff = target_value - current_value

        if abs(diff) < target_value * 0.02:
            # Within 2% of target -- skip to avoid unnecessary trading
            return

        if diff < 0:
            # Need to trim: sell some shares
            shares_to_sell = int(abs(diff) / price)
            if shares_to_sell > 0:
                gross_proceeds = shares_to_sell * price
                fee = gross_proceeds * cost_pct
                net_proceeds = gross_proceeds - fee
                trade = Trade(
                    date=rebal_date,
                    ticker=ticker,
                    action='SELL',
                    shares=shares_to_sell,
                    price=price,
                    transaction_cost=fee,
                    net_amount=net_proceeds,
                    entry_price=pos.entry_price,
                    holding_days=(rebal_date - pos.entry_date).days,
                )
                self.trade_log.append(trade)
                self.cash += net_proceeds
                pos.shares -= shares_to_sell
        else:
            # Need to add: buy more shares
            self.execute_buy(ticker, price, diff, rebal_date, cost_pct)
```

### Main Simulation Loop

```python
import pandas as pd
import numpy as np
from datetime import date, timedelta
from typing import List, Tuple


STARTING_CAPITAL = 100_000.0
NUM_POSITIONS = 25
TARGET_WEIGHT = 1.0 / NUM_POSITIONS  # 0.04 = 4%
TRANSACTION_COST = 0.001  # 10 bps
BACKTEST_START = date(2014, 1, 2)
BACKTEST_END = date(2024, 12, 31)


def get_rebalance_dates(start: date, end: date) -> List[date]:
    """
    Generate the first trading day of each month in the backtest period.
    Uses the NYSE trading calendar.
    """
    import exchange_calendars as xcals
    nyse = xcals.get_calendar('XNYS')

    rebalance_dates = []
    current = date(start.year, start.month, 1)
    while current <= end:
        # Get first trading day of this month
        month_start = pd.Timestamp(current)
        if nyse.is_session(month_start):
            rebalance_dates.append(current)
        else:
            next_session = nyse.date_to_session(month_start, direction='next')
            rebalance_dates.append(next_session.date())

        # Advance to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return rebalance_dates


def get_trading_days(start: date, end: date) -> List[date]:
    """Get all NYSE trading days in a range."""
    import exchange_calendars as xcals
    nyse = xcals.get_calendar('XNYS')
    sessions = nyse.sessions_in_range(
        pd.Timestamp(start), pd.Timestamp(end)
    )
    return [s.date() for s in sessions]


def run_screening_pipeline(rebalance_date: date, db) -> List[str]:
    """
    Run the full screening pipeline and return top 25 tickers.
    This is a high-level function -- implementation depends on your data layer.
    """
    # Step 1: Get active universe
    universe = get_active_universe(rebalance_date)

    # Step 2: Apply market cap, volume, price filters
    filtered = apply_universe_filters(universe, rebalance_date, db)

    # Step 3: Compute all 4 factors
    scored = []
    for ticker in filtered:
        eps_growth = calc_yoy_eps_growth(ticker, rebalance_date)
        rev_growth = calc_yoy_rev_growth(ticker, rebalance_date)
        price_vs_high = calc_price_vs_52wk_high(ticker, rebalance_date, db)
        rs_pctl = get_rs_percentile(ticker, rebalance_date, filtered)

        # Step 3b: Quality filters
        if eps_growth is None or eps_growth < 5.0:
            continue
        if rev_growth is None or rev_growth < 5.0:
            continue
        if price_vs_high is None or price_vs_high < 75.0:
            continue

        # Step 3c: Normalize growth scores to 0-100 scale for composite
        eps_score = min(100, max(0, eps_growth))      # cap at 100
        rev_score = min(100, max(0, rev_growth))       # cap at 100

        composite = (
            rs_pctl * 0.40 +
            eps_score * 0.20 +
            rev_score * 0.20 +
            price_vs_high * 0.20
        )
        scored.append((ticker, composite))

    # Step 4: Rank and select top 25
    scored.sort(key=lambda x: x[1], reverse=True)
    return [ticker for ticker, score in scored[:NUM_POSITIONS]]


def run_backtest(db) -> Portfolio:
    """
    Main backtest loop. Returns the final portfolio with full history.
    """
    portfolio = Portfolio(cash=STARTING_CAPITAL)
    rebalance_dates = get_rebalance_dates(BACKTEST_START, BACKTEST_END)
    all_trading_days = get_trading_days(BACKTEST_START, BACKTEST_END)

    rebalance_set = set(rebalance_dates)
    rebalance_idx = 0

    for trading_day in all_trading_days:
        # Get all prices for today
        prices = get_all_prices(trading_day, db)  # returns {ticker: close_price}

        # Mark-to-market daily
        portfolio.mark_to_market(prices, trading_day)

        # Handle delistings: if a held stock has no price, treat as delisted
        handle_delistings(portfolio, prices, trading_day)

        # Check if today is a rebalance day
        if trading_day in rebalance_set and rebalance_idx < len(rebalance_dates):
            print(f"Rebalancing on {trading_day} | "
                  f"Portfolio value: ${portfolio.total_value:,.2f} | "
                  f"Positions: {len(portfolio.positions)}")

            # Run screening to get new target portfolio
            new_targets = run_screening_pipeline(trading_day, db)

            if len(new_targets) == 0:
                print(f"  WARNING: No stocks passed screening on {trading_day}")
                rebalance_idx += 1
                continue

            current_tickers = set(portfolio.positions.keys())
            target_tickers = set(new_targets)

            to_sell = current_tickers - target_tickers
            to_buy = target_tickers - current_tickers
            to_hold = current_tickers & target_tickers

            # Step 1: Execute all SELLS first (frees up cash)
            for ticker in to_sell:
                if ticker in prices:
                    portfolio.execute_sell(ticker, prices[ticker], trading_day,
                                          TRANSACTION_COST)
                else:
                    # No price available -- delisted or halted
                    # Treat as zero (worst case) or use last known price
                    print(f"  WARNING: No price for {ticker} on sell date, "
                          f"using last known price")
                    last_price = portfolio.positions[ticker].current_price
                    portfolio.execute_sell(ticker, last_price, trading_day,
                                          TRANSACTION_COST)

            # Step 2: Calculate target value per position
            target_per_position = portfolio.total_value * TARGET_WEIGHT

            # Step 3: Rebalance HOLD positions
            for ticker in to_hold:
                if ticker in prices:
                    portfolio.rebalance_position(
                        ticker, prices[ticker], target_per_position,
                        trading_day, TRANSACTION_COST
                    )

            # Step 4: Execute all BUYS
            num_buys = len(to_buy)
            if num_buys > 0:
                # Recalculate available cash after sells and rebalances
                cash_for_buys = portfolio.cash
                buy_amount_each = cash_for_buys / num_buys

                # Cap at target weight to avoid overweighting new positions
                buy_amount_each = min(buy_amount_each, target_per_position)

                for ticker in to_buy:
                    if ticker in prices:
                        portfolio.execute_buy(
                            ticker, prices[ticker], buy_amount_each,
                            trading_day, TRANSACTION_COST
                        )

            rebalance_idx += 1

    return portfolio


def handle_delistings(portfolio: Portfolio, prices: dict, current_date: date):
    """
    Handle stocks that have been delisted mid-holding-period.
    If a stock has no price for 5+ consecutive trading days, treat as delisted.

    Delisting treatment options:
    1. Conservative: Assume 100% loss (price = 0)
    2. Moderate: Use last known price minus 50%
    3. Research-based: Use CRSP delisting returns if available

    We use option 2 (moderate) as the default.
    """
    DELISTING_GRACE_DAYS = 5
    delisted = []

    for ticker, pos in portfolio.positions.items():
        if ticker not in prices:
            # Check how many days since last price
            days_missing = (current_date - pos.entry_date).days
            # In practice, you'd track consecutive missing days
            # Simplified: if not in today's prices and position exists > 5 days
            if days_missing > DELISTING_GRACE_DAYS:
                delisted.append(ticker)

    for ticker in delisted:
        pos = portfolio.positions[ticker]
        delisting_price = pos.current_price * 0.50  # 50% haircut
        portfolio.execute_sell(ticker, delisting_price, current_date,
                               TRANSACTION_COST)
        print(f"  DELISTED: {ticker} sold at ${delisting_price:.2f} "
              f"(50% of last price ${pos.current_price:.2f})")
```

### Helper Functions (Data Layer)

```python
def get_all_prices(as_of_date: date, db) -> dict:
    """
    Get closing prices for all stocks on a given date.
    Returns {ticker: adjusted_close_price}.
    Uses Sharadar SEP (daily prices) table.
    """
    rows = db.execute("""
        SELECT ticker, close
        FROM sep
        WHERE date = ?
    """, [as_of_date]).fetchall()
    return {row['ticker']: row['close'] for row in rows}


def get_prices(ticker: str, start: date, end: date, db=None) -> list:
    """
    Get adjusted closing prices for a ticker between start and end dates.
    Returns list of floats in chronological order.
    """
    rows = db.execute("""
        SELECT close
        FROM sep
        WHERE ticker = ?
          AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """, [ticker, start, end]).fetchall()
    return [row['close'] for row in rows]


def calc_yoy_rev_growth(ticker: str, rebalance_date: date) -> float:
    """Calculate YoY revenue growth. Same logic as EPS growth."""
    current_q = get_latest_fundamentals(ticker, rebalance_date)
    if current_q is None:
        return None

    prior_year_end = current_q['calendardate'] - timedelta(days=365)
    prior_q = db.execute("""
        SELECT revenue
        FROM sf1
        WHERE ticker = ?
          AND dimension = 'ARQ'
          AND calendardate BETWEEN ? AND ?
          AND datekey <= ?
        ORDER BY ABS(julianday(calendardate) - julianday(?))
        LIMIT 1
    """, [
        ticker,
        prior_year_end - timedelta(days=45),
        prior_year_end + timedelta(days=45),
        rebalance_date,
        prior_year_end
    ]).fetchone()

    if prior_q is None or prior_q['revenue'] == 0:
        return None

    return ((current_q['revenue'] - prior_q['revenue']) /
            abs(prior_q['revenue'])) * 100


def calc_price_vs_52wk_high(ticker: str, rebalance_date: date, db) -> float:
    """
    Calculate current price as % of 52-week high.
    Returns value 0-100 (e.g., 92.5 means price is 92.5% of 52-week high).
    """
    prices = get_prices(
        ticker,
        rebalance_date - timedelta(days=370),  # extra days for weekends/holidays
        rebalance_date,
        db
    )
    if len(prices) < 200:
        return None

    current_price = prices[-1]
    high_52wk = max(prices[-252:])  # last 252 trading days

    if high_52wk == 0:
        return None

    return (current_price / high_52wk) * 100
```

---

## 6. Performance Metric Calculations

All metrics include both the mathematical formula and production-ready Python implementation.

### Prerequisite: Daily Returns

```python
def compute_daily_returns(portfolio: Portfolio) -> pd.Series:
    """
    Convert daily portfolio values to a return series.
    Returns a pandas Series indexed by date with daily percentage returns.
    """
    df = pd.DataFrame(portfolio.daily_values)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    df['return'] = df['value'].pct_change()
    return df['return'].dropna()


def compute_trade_returns(portfolio: Portfolio) -> pd.DataFrame:
    """
    Compute per-trade returns from the trade log.
    Each 'round trip' (BUY then SELL of same ticker) is one trade.
    """
    trades = []
    for trade in portfolio.trade_log:
        if trade.action == 'SELL' and trade.entry_price > 0:
            pnl = (trade.price - trade.entry_price) / trade.entry_price
            pnl_dollar = (trade.price - trade.entry_price) * trade.shares
            # Deduct transaction costs from both legs
            pnl_net = pnl - 2 * TRANSACTION_COST  # cost on buy + cost on sell
            trades.append({
                'date': trade.date,
                'ticker': trade.ticker,
                'entry_price': trade.entry_price,
                'exit_price': trade.price,
                'shares': trade.shares,
                'gross_return': pnl,
                'net_return': pnl_net,
                'pnl_dollar': pnl_dollar - trade.transaction_cost,
                'holding_days': trade.holding_days,
            })
    return pd.DataFrame(trades)
```

### CAGR (Compound Annual Growth Rate)

**Formula:**

```
CAGR = (V_final / V_initial) ^ (1 / years) - 1
```

Where `years` is the exact number of years (can be fractional).

```python
def calc_cagr(portfolio: Portfolio) -> float:
    """
    Compound Annual Growth Rate.

    Example:
        Starting value: $100,000
        Ending value:   $528,000
        Period:         11 years
        CAGR = (528000 / 100000)^(1/11) - 1 = 0.1666 = 16.66%
    """
    values = portfolio.daily_values
    if len(values) < 2:
        return 0.0

    start_value = values[0]['value']
    end_value = values[-1]['value']
    start_date = values[0]['date']
    end_date = values[-1]['date']

    years = (end_date - start_date).days / 365.25

    if years <= 0 or start_value <= 0:
        return 0.0

    cagr = (end_value / start_value) ** (1 / years) - 1
    return cagr
```

### Sharpe Ratio

**Formula:**

```
Sharpe = (R_p - R_f) / sigma_p

Where:
  R_p     = annualized portfolio return = mean(daily_returns) * 252
  R_f     = annualized risk-free rate (default 2%)
  sigma_p = annualized portfolio volatility = std(daily_returns) * sqrt(252)
```

```python
def calc_sharpe_ratio(daily_returns: pd.Series,
                      risk_free_rate: float = 0.02) -> float:
    """
    Annualized Sharpe Ratio using daily returns.

    Parameters:
        daily_returns: Series of daily percentage returns
        risk_free_rate: Annual risk-free rate (default 2%)

    Returns:
        Annualized Sharpe Ratio

    Example:
        mean daily return = 0.065%
        daily std = 1.1%
        Sharpe = (0.065% * 252 - 2%) / (1.1% * sqrt(252))
              = (16.38% - 2%) / 17.46%
              = 0.823

    Note:
        Uses 252 trading days per year for annualization.
        The risk-free rate is converted to a daily rate for excess return calc.
    """
    if len(daily_returns) < 30:
        return 0.0

    daily_rf = risk_free_rate / 252
    excess_returns = daily_returns - daily_rf

    annualized_excess_return = excess_returns.mean() * 252
    annualized_volatility = daily_returns.std() * np.sqrt(252)

    if annualized_volatility == 0:
        return 0.0

    return annualized_excess_return / annualized_volatility
```

### Sortino Ratio

**Formula:**

```
Sortino = (R_p - R_f) / DD

Where:
  DD = sqrt(mean(min(R_i - target, 0)^2)) * sqrt(252)
  target = 0 (or the risk-free daily rate)
```

The key difference from Sharpe: the denominator only penalizes *downside* volatility, not all volatility. A strategy with large up-days and small down-days will have a Sortino much higher than its Sharpe.

```python
def calc_sortino_ratio(daily_returns: pd.Series,
                       risk_free_rate: float = 0.02,
                       target_return: float = 0.0) -> float:
    """
    Annualized Sortino Ratio using daily returns.

    Parameters:
        daily_returns: Series of daily percentage returns
        risk_free_rate: Annual risk-free rate
        target_return: Daily target return (default 0)

    Returns:
        Annualized Sortino Ratio
    """
    if len(daily_returns) < 30:
        return 0.0

    daily_rf = risk_free_rate / 252

    # Downside returns: only negative deviations from target
    downside = daily_returns[daily_returns < target_return] - target_return
    downside_std = np.sqrt(np.mean(downside ** 2)) if len(downside) > 0 else 0

    if downside_std == 0:
        return 0.0

    annualized_return = daily_returns.mean() * 252
    annualized_downside = downside_std * np.sqrt(252)

    return (annualized_return - risk_free_rate) / annualized_downside
```

### Maximum Drawdown

**Formula:**

```
Drawdown_t = (Peak_t - Value_t) / Peak_t
Max Drawdown = max(Drawdown_t) for all t
```

Where `Peak_t` is the highest portfolio value up to time `t`.

```python
def calc_max_drawdown(portfolio: Portfolio) -> Tuple[float, date, date, date]:
    """
    Calculate maximum drawdown and the dates of peak, trough, and recovery.

    Returns:
        Tuple of (max_drawdown, peak_date, trough_date, recovery_date)
        max_drawdown is negative (e.g., -0.2268 for 22.68% drawdown)
        recovery_date is None if drawdown never recovered

    Example:
        Portfolio peaks at $200K on 2020-01-15
        Falls to $155K on 2020-03-23
        Max Drawdown = (155000 - 200000) / 200000 = -22.5%
    """
    values = pd.DataFrame(portfolio.daily_values)
    values['date'] = pd.to_datetime(values['date'])
    values = values.set_index('date').sort_index()

    equity = values['value']
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max

    max_dd = drawdown.min()
    trough_date = drawdown.idxmin().date()

    # Find the peak date (most recent peak before the trough)
    peak_value = running_max.loc[:trough_date].max()
    peak_date = equity.loc[:trough_date][
        equity.loc[:trough_date] == peak_value
    ].index[-1].date()

    # Find recovery date (first date after trough where value >= peak value)
    post_trough = equity.loc[trough_date:]
    recovery_mask = post_trough >= peak_value
    if recovery_mask.any():
        recovery_date = post_trough[recovery_mask].index[0].date()
    else:
        recovery_date = None  # Never recovered

    return max_dd, peak_date, trough_date, recovery_date


def calc_drawdown_series(portfolio: Portfolio) -> pd.Series:
    """
    Calculate the full drawdown time series for plotting.
    Returns a Series of drawdown values (all <= 0).
    """
    values = pd.DataFrame(portfolio.daily_values)
    values['date'] = pd.to_datetime(values['date'])
    values = values.set_index('date').sort_index()

    equity = values['value']
    running_max = equity.cummax()
    drawdown = (equity - running_max) / running_max
    return drawdown
```

### Calmar Ratio

**Formula:**

```
Calmar = CAGR / |Max Drawdown|
```

Higher is better. A Calmar of 1.0 means CAGR equals the worst drawdown. Above 1.0 is considered good.

```python
def calc_calmar_ratio(portfolio: Portfolio) -> float:
    """
    Calmar Ratio: CAGR divided by the absolute value of max drawdown.

    Example:
        CAGR = 16.66%
        Max Drawdown = -22.68%
        Calmar = 16.66 / 22.68 = 0.734
    """
    cagr = calc_cagr(portfolio)
    max_dd, _, _, _ = calc_max_drawdown(portfolio)

    if max_dd == 0:
        return 0.0

    return cagr / abs(max_dd)
```

### Profit Factor

**Formula:**

```
Profit Factor = Sum of Gross Profits / Sum of Gross Losses

Where:
  Gross Profits = sum of all positive trade P&Ls (dollar amounts)
  Gross Losses  = sum of all negative trade P&Ls (absolute value)
```

A profit factor of 1.80 means the strategy makes $1.80 for every $1.00 it loses.

```python
def calc_profit_factor(trade_df: pd.DataFrame) -> float:
    """
    Profit Factor from per-trade returns.

    Parameters:
        trade_df: DataFrame from compute_trade_returns() with 'pnl_dollar' column

    Returns:
        Profit factor (gross profits / gross losses)

    Example:
        Total winning trades P&L: $180,000
        Total losing trades P&L:  -$100,000
        Profit Factor = 180000 / 100000 = 1.80
    """
    if trade_df.empty:
        return 0.0

    gross_profits = trade_df.loc[trade_df['pnl_dollar'] > 0, 'pnl_dollar'].sum()
    gross_losses = abs(trade_df.loc[trade_df['pnl_dollar'] < 0, 'pnl_dollar'].sum())

    if gross_losses == 0:
        return float('inf')  # No losing trades

    return gross_profits / gross_losses
```

### Win Rate

**Formula:**

```
Win Rate = # Profitable Trades / Total Trades
```

A trade is a complete round trip: buy followed by sell of the same ticker.

```python
def calc_win_rate(trade_df: pd.DataFrame) -> Tuple[float, int, int]:
    """
    Win rate and trade counts.

    Returns:
        Tuple of (win_rate, num_winners, num_losers)

    Example:
        773 winning trades, 762 losing trades
        Win Rate = 773 / 1535 = 50.36%
    """
    if trade_df.empty:
        return 0.0, 0, 0

    winners = (trade_df['net_return'] > 0).sum()
    losers = (trade_df['net_return'] <= 0).sum()
    total = len(trade_df)

    return winners / total, winners, losers
```

### Average Win / Average Loss / Expectancy

```python
def calc_win_loss_stats(trade_df: pd.DataFrame) -> dict:
    """
    Detailed win/loss statistics including expectancy.

    Returns dict with:
        avg_win: mean return of winning trades (%)
        avg_loss: mean return of losing trades (%)
        win_loss_ratio: avg_win / |avg_loss|
        expectancy: expected return per trade (%)
        expectancy_dollar: expected dollar P&L per trade

    Example:
        Win rate: 50.36%
        Avg win: +8.5%
        Avg loss: -4.7%
        Win/Loss ratio: 1.81
        Expectancy = 0.5036 * 8.5 - 0.4964 * 4.7 = +1.95% per trade
    """
    if trade_df.empty:
        return {}

    winners = trade_df[trade_df['net_return'] > 0]
    losers = trade_df[trade_df['net_return'] <= 0]

    avg_win = winners['net_return'].mean() * 100 if len(winners) > 0 else 0
    avg_loss = losers['net_return'].mean() * 100 if len(losers) > 0 else 0
    win_rate = len(winners) / len(trade_df)

    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float('inf')
    expectancy = win_rate * avg_win - (1 - win_rate) * abs(avg_loss)

    avg_win_dollar = winners['pnl_dollar'].mean() if len(winners) > 0 else 0
    avg_loss_dollar = losers['pnl_dollar'].mean() if len(losers) > 0 else 0
    expectancy_dollar = (win_rate * avg_win_dollar +
                         (1 - win_rate) * avg_loss_dollar)

    return {
        'avg_win_pct': avg_win,
        'avg_loss_pct': avg_loss,
        'win_loss_ratio': win_loss_ratio,
        'expectancy_pct': expectancy,
        'avg_win_dollar': avg_win_dollar,
        'avg_loss_dollar': avg_loss_dollar,
        'expectancy_dollar': expectancy_dollar,
        'avg_holding_days': trade_df['holding_days'].mean(),
        'median_holding_days': trade_df['holding_days'].median(),
    }
```

### Full Metrics Summary Function

```python
def generate_metrics_report(portfolio: Portfolio) -> dict:
    """
    Generate a complete performance metrics report.
    """
    daily_returns = compute_daily_returns(portfolio)
    trade_df = compute_trade_returns(portfolio)

    cagr = calc_cagr(portfolio)
    total_return = (portfolio.daily_values[-1]['value'] /
                    portfolio.daily_values[0]['value']) - 1
    max_dd, peak_date, trough_date, recovery_date = calc_max_drawdown(portfolio)
    sharpe = calc_sharpe_ratio(daily_returns)
    sortino = calc_sortino_ratio(daily_returns)
    calmar = calc_calmar_ratio(portfolio)
    profit_factor = calc_profit_factor(trade_df)
    win_rate, num_winners, num_losers = calc_win_rate(trade_df)
    wl_stats = calc_win_loss_stats(trade_df)

    report = {
        # Return metrics
        'total_return_pct': total_return * 100,
        'cagr_pct': cagr * 100,
        'annualized_volatility': daily_returns.std() * np.sqrt(252) * 100,

        # Risk-adjusted metrics
        'sharpe_ratio': sharpe,
        'sortino_ratio': sortino,
        'calmar_ratio': calmar,

        # Drawdown
        'max_drawdown_pct': max_dd * 100,
        'max_dd_peak_date': peak_date,
        'max_dd_trough_date': trough_date,
        'max_dd_recovery_date': recovery_date,

        # Trade statistics
        'total_trades': len(trade_df),
        'profit_factor': profit_factor,
        'win_rate_pct': win_rate * 100,
        'num_winners': num_winners,
        'num_losers': num_losers,

        # Win/loss detail
        **wl_stats,

        # Portfolio
        'starting_value': portfolio.daily_values[0]['value'],
        'ending_value': portfolio.daily_values[-1]['value'],
        'total_transaction_costs': sum(
            t.transaction_cost for t in portfolio.trade_log
        ),
    }

    return report


def print_metrics_report(report: dict):
    """Pretty-print the metrics report."""
    print("=" * 60)
    print("BACKTEST PERFORMANCE REPORT")
    print("=" * 60)

    print(f"\n--- Return Metrics ---")
    print(f"Total Return:          {report['total_return_pct']:.2f}%")
    print(f"CAGR:                  {report['cagr_pct']:.2f}%")
    print(f"Annualized Volatility: {report['annualized_volatility']:.2f}%")

    print(f"\n--- Risk-Adjusted Metrics ---")
    print(f"Sharpe Ratio:          {report['sharpe_ratio']:.3f}")
    print(f"Sortino Ratio:         {report['sortino_ratio']:.3f}")
    print(f"Calmar Ratio:          {report['calmar_ratio']:.3f}")

    print(f"\n--- Drawdown ---")
    print(f"Max Drawdown:          {report['max_drawdown_pct']:.2f}%")
    print(f"  Peak Date:           {report['max_dd_peak_date']}")
    print(f"  Trough Date:         {report['max_dd_trough_date']}")
    print(f"  Recovery Date:       {report['max_dd_recovery_date']}")

    print(f"\n--- Trade Statistics ---")
    print(f"Total Trades:          {report['total_trades']}")
    print(f"Profit Factor:         {report['profit_factor']:.2f}")
    print(f"Win Rate:              {report['win_rate_pct']:.2f}%")
    print(f"Winners / Losers:      {report['num_winners']} / {report['num_losers']}")
    print(f"Avg Win:               {report['avg_win_pct']:.2f}%")
    print(f"Avg Loss:              {report['avg_loss_pct']:.2f}%")
    print(f"Win/Loss Ratio:        {report['win_loss_ratio']:.2f}")
    print(f"Expectancy (per trade):{report['expectancy_pct']:.2f}%")
    print(f"Avg Holding Period:    {report['avg_holding_days']:.0f} days")

    print(f"\n--- Portfolio ---")
    print(f"Starting Value:        ${report['starting_value']:,.2f}")
    print(f"Ending Value:          ${report['ending_value']:,.2f}")
    print(f"Total Transaction Cost:${report['total_transaction_costs']:,.2f}")
    print("=" * 60)
```

---

## 7. Subperiod Analysis

### Purpose

A strategy that works in one market regime but fails in another is not robust. By splitting the backtest into two independent subperiods, we test for consistency. Both halves should produce positive risk-adjusted returns.

### Implementation

```python
def run_subperiod_analysis(portfolio: Portfolio) -> dict:
    """
    Split the backtest into two halves and compute metrics for each.

    Period 1: 2014-01-01 to 2019-06-30 (pre-COVID, bull market + 2018 correction)
    Period 2: 2019-07-01 to 2024-12-31 (COVID crash, recovery, 2022 bear, recovery)
    """
    split_date = date(2019, 7, 1)

    values = pd.DataFrame(portfolio.daily_values)
    values['date'] = pd.to_datetime(values['date'])

    # Split daily values
    period1_values = values[values['date'] < pd.Timestamp(split_date)]
    period2_values = values[values['date'] >= pd.Timestamp(split_date)]

    # Create sub-portfolios for metric calculation
    p1 = Portfolio(cash=0)
    p1.daily_values = period1_values.to_dict('records')

    p2 = Portfolio(cash=0)
    p2.daily_values = period2_values.to_dict('records')

    # Split trade log
    trades = pd.DataFrame([{
        'date': t.date,
        'pnl_dollar': (t.price - t.entry_price) * t.shares - t.transaction_cost
            if t.action == 'SELL' else 0,
        'net_return': ((t.price - t.entry_price) / t.entry_price - 2 * TRANSACTION_COST)
            if t.action == 'SELL' and t.entry_price > 0 else 0,
        'action': t.action,
        'holding_days': t.holding_days,
    } for t in portfolio.trade_log])

    sell_trades = trades[trades['action'] == 'SELL'].copy()
    t1 = sell_trades[sell_trades['date'] < split_date]
    t2 = sell_trades[sell_trades['date'] >= split_date]

    # Compute returns for each period
    r1 = compute_daily_returns(p1)
    r2 = compute_daily_returns(p2)

    results = {
        'period_1': {
            'dates': f"2014-01 to 2019-06",
            'sharpe': calc_sharpe_ratio(r1),
            'sortino': calc_sortino_ratio(r1),
            'cagr': calc_cagr(p1) * 100,
            'max_dd': calc_max_drawdown(p1)[0] * 100,
            'num_trades': len(t1),
            'win_rate': (t1['net_return'] > 0).mean() * 100 if len(t1) > 0 else 0,
            'profit_factor': (
                t1.loc[t1['pnl_dollar'] > 0, 'pnl_dollar'].sum() /
                abs(t1.loc[t1['pnl_dollar'] < 0, 'pnl_dollar'].sum())
                if (t1['pnl_dollar'] < 0).any() else float('inf')
            ),
        },
        'period_2': {
            'dates': f"2019-07 to 2024-12",
            'sharpe': calc_sharpe_ratio(r2),
            'sortino': calc_sortino_ratio(r2),
            'cagr': calc_cagr(p2) * 100,
            'max_dd': calc_max_drawdown(p2)[0] * 100,
            'num_trades': len(t2),
            'win_rate': (t2['net_return'] > 0).mean() * 100 if len(t2) > 0 else 0,
            'profit_factor': (
                t2.loc[t2['pnl_dollar'] > 0, 'pnl_dollar'].sum() /
                abs(t2.loc[t2['pnl_dollar'] < 0, 'pnl_dollar'].sum())
                if (t2['pnl_dollar'] < 0).any() else float('inf')
            ),
        },
    }

    return results


def print_subperiod_report(results: dict):
    """Print subperiod comparison table."""
    print("\n" + "=" * 70)
    print("SUBPERIOD ANALYSIS")
    print("=" * 70)
    print(f"{'Metric':<25} {'Period 1':>20} {'Period 2':>20}")
    print("-" * 70)

    for metric in ['dates', 'sharpe', 'sortino', 'cagr', 'max_dd',
                    'num_trades', 'win_rate', 'profit_factor']:
        v1 = results['period_1'][metric]
        v2 = results['period_2'][metric]

        if isinstance(v1, str):
            print(f"{metric:<25} {v1:>20} {v2:>20}")
        elif metric in ('sharpe', 'sortino', 'profit_factor'):
            print(f"{metric:<25} {v1:>20.3f} {v2:>20.3f}")
        elif metric in ('cagr', 'max_dd', 'win_rate'):
            print(f"{metric:<25} {v1:>19.2f}% {v2:>19.2f}%")
        else:
            print(f"{metric:<25} {v1:>20} {v2:>20}")

    print("-" * 70)

    # Consistency check
    s1 = results['period_1']['sharpe']
    s2 = results['period_2']['sharpe']

    if s1 > 0.9 and s2 > 0.9:
        print("PASS: Both periods show Sharpe > 0.9. Strategy is consistent.")
    elif s1 > 0 and s2 > 0:
        print("CAUTION: Both periods positive, but one has Sharpe < 0.9.")
        print("         May indicate regime dependency.")
    else:
        print("FAIL: One or both periods have negative Sharpe.")
        print("      Strategy may not be robust across market regimes.")
```

### Interpretation Guide

| Scenario | Diagnosis |
|---|---|
| Both halves Sharpe > 0.9 | Strong evidence of robust strategy |
| One half Sharpe > 1.5, other < 0.5 | Regime-dependent -- proceed with caution |
| Both halves Sharpe 0.5-0.9 | Moderate evidence, may need parameter tuning |
| Either half Sharpe < 0 | Strategy fails in that regime -- investigate why |

If Period 2 (2019-2024) dramatically outperforms Period 1 (2014-2019), the strategy may be overfitting to recent small-cap momentum. If Period 1 outperforms, it may be overfitting to the long bull market. Neither is disqualifying, but it demands investigation.

---

## 8. Bootstrap Validation

### Purpose

Bootstrap resampling provides confidence intervals for performance metrics. Instead of relying on a single point estimate ("Sharpe is 1.054"), we get a range ("Sharpe is between 0.72 and 1.39 with 95% confidence"). If the 95% confidence interval excludes zero, the strategy's outperformance is statistically significant.

### Method

1. Take the actual daily returns series (N days)
2. Resample N returns WITH replacement (some days repeated, some omitted)
3. Construct a synthetic equity curve from the resampled returns
4. Calculate metrics on this synthetic curve
5. Repeat 10,000 times
6. Build distributions of each metric
7. Report 2.5th and 97.5th percentiles as the 95% CI

### Implementation

```python
def bootstrap_validation(daily_returns: pd.Series,
                         n_iterations: int = 10_000,
                         confidence_level: float = 0.95,
                         seed: int = 42) -> dict:
    """
    Bootstrap resampling of daily returns to generate confidence intervals
    for key performance metrics.

    Parameters:
        daily_returns: Series of daily returns from the backtest
        n_iterations: Number of bootstrap samples (default 10,000)
        confidence_level: CI level (default 0.95 for 95% CI)
        seed: Random seed for reproducibility

    Returns:
        Dict with point estimates and confidence intervals for each metric
    """
    np.random.seed(seed)
    n_days = len(daily_returns)
    returns_array = daily_returns.values

    # Pre-allocate arrays for speed
    sharpe_samples = np.zeros(n_iterations)
    total_return_samples = np.zeros(n_iterations)
    sortino_samples = np.zeros(n_iterations)
    cagr_samples = np.zeros(n_iterations)
    max_dd_samples = np.zeros(n_iterations)

    for i in range(n_iterations):
        # Resample with replacement
        resampled = np.random.choice(returns_array, size=n_days, replace=True)

        # Sharpe
        excess = resampled - 0.02 / 252  # subtract daily risk-free
        ann_excess = excess.mean() * 252
        ann_vol = resampled.std() * np.sqrt(252)
        sharpe_samples[i] = ann_excess / ann_vol if ann_vol > 0 else 0

        # Total return (compound the daily returns)
        cumulative = np.cumprod(1 + resampled)
        total_return_samples[i] = cumulative[-1] - 1

        # Sortino
        downside = resampled[resampled < 0]
        downside_std = np.sqrt(np.mean(downside ** 2)) if len(downside) > 0 else 0
        ann_downside = downside_std * np.sqrt(252)
        ann_return = resampled.mean() * 252
        sortino_samples[i] = ((ann_return - 0.02) / ann_downside
                              if ann_downside > 0 else 0)

        # CAGR
        years = n_days / 252
        end_value = cumulative[-1]
        cagr_samples[i] = end_value ** (1 / years) - 1 if years > 0 else 0

        # Max Drawdown
        running_max = np.maximum.accumulate(cumulative)
        drawdowns = (cumulative - running_max) / running_max
        max_dd_samples[i] = drawdowns.min()

    # Calculate confidence intervals
    alpha = 1 - confidence_level
    lower_pctl = alpha / 2 * 100        # 2.5 for 95% CI
    upper_pctl = (1 - alpha / 2) * 100  # 97.5 for 95% CI

    def ci(samples):
        return {
            'mean': np.mean(samples),
            'median': np.median(samples),
            'std': np.std(samples),
            'ci_lower': np.percentile(samples, lower_pctl),
            'ci_upper': np.percentile(samples, upper_pctl),
        }

    results = {
        'n_iterations': n_iterations,
        'confidence_level': confidence_level,
        'n_days': n_days,
        'sharpe': ci(sharpe_samples),
        'total_return': ci(total_return_samples),
        'sortino': ci(sortino_samples),
        'cagr': ci(cagr_samples),
        'max_drawdown': ci(max_dd_samples),
    }

    return results


def print_bootstrap_report(results: dict):
    """Print bootstrap confidence interval report."""
    cl = results['confidence_level'] * 100
    print(f"\n{'=' * 70}")
    print(f"BOOTSTRAP VALIDATION ({results['n_iterations']:,} iterations, "
          f"{cl:.0f}% CI)")
    print(f"{'=' * 70}")
    print(f"Based on {results['n_days']:,} daily returns resampled "
          f"with replacement\n")
    print(f"{'Metric':<20} {'Point Est':>12} {'CI Lower':>12} {'CI Upper':>12}")
    print("-" * 60)

    for metric, label, fmt, mult in [
        ('sharpe', 'Sharpe Ratio', '.3f', 1),
        ('sortino', 'Sortino Ratio', '.3f', 1),
        ('cagr', 'CAGR', '.2f', 100),
        ('total_return', 'Total Return', '.1f', 100),
        ('max_drawdown', 'Max Drawdown', '.2f', 100),
    ]:
        d = results[metric]
        suffix = '%' if mult == 100 else ''
        print(f"{label:<20} "
              f"{d['mean'] * mult:>11{fmt}}{suffix} "
              f"{d['ci_lower'] * mult:>11{fmt}}{suffix} "
              f"{d['ci_upper'] * mult:>11{fmt}}{suffix}")

    print("-" * 60)

    # Statistical significance test
    sharpe_ci = results['sharpe']
    if sharpe_ci['ci_lower'] > 0:
        print(f"\nSharpe {cl:.0f}% CI: [{sharpe_ci['ci_lower']:.3f}, "
              f"{sharpe_ci['ci_upper']:.3f}]")
        print("PASS: CI excludes zero. Strategy outperformance is "
              "statistically significant.")
    else:
        print(f"\nSharpe {cl:.0f}% CI: [{sharpe_ci['ci_lower']:.3f}, "
              f"{sharpe_ci['ci_upper']:.3f}]")
        print("FAIL: CI includes zero. Cannot reject null hypothesis "
              "of no outperformance.")
```

### Important Caveats

1. **Autocorrelation:** Bootstrap resampling assumes daily returns are IID (independent and identically distributed). Stock returns exhibit modest autocorrelation and volatility clustering. This means the bootstrap CI may be slightly too narrow. For a more rigorous approach, use block bootstrap (resample blocks of 5-20 consecutive days instead of individual days).

2. **Path dependency:** Drawdown is path-dependent -- the order of returns matters. Standard bootstrap destroys the time ordering, so drawdown CIs from bootstrap are approximate. The Sharpe and total return CIs are more reliable.

3. **Block Bootstrap Alternative:**

```python
def block_bootstrap(daily_returns: pd.Series,
                    block_size: int = 10,
                    n_iterations: int = 10_000,
                    seed: int = 42) -> dict:
    """
    Block bootstrap preserving autocorrelation structure.
    Resamples blocks of consecutive days instead of individual days.
    More appropriate for financial time series.
    """
    np.random.seed(seed)
    returns_array = daily_returns.values
    n_days = len(returns_array)
    n_blocks = n_days // block_size

    sharpe_samples = np.zeros(n_iterations)

    for i in range(n_iterations):
        # Sample random block start indices
        starts = np.random.randint(0, n_days - block_size, size=n_blocks)
        # Concatenate blocks
        resampled = np.concatenate([
            returns_array[s:s + block_size] for s in starts
        ])[:n_days]  # trim to original length

        excess = resampled - 0.02 / 252
        ann_excess = excess.mean() * 252
        ann_vol = resampled.std() * np.sqrt(252)
        sharpe_samples[i] = ann_excess / ann_vol if ann_vol > 0 else 0

    return {
        'sharpe_mean': np.mean(sharpe_samples),
        'sharpe_ci_lower': np.percentile(sharpe_samples, 2.5),
        'sharpe_ci_upper': np.percentile(sharpe_samples, 97.5),
    }
```

---

## 9. Benchmark Comparison

### Benchmark Selection

| Benchmark | Ticker | Purpose |
|---|---|---|
| S&P 500 | SPY | Large-cap market benchmark. Strategy should beat this to justify small-cap risk. |
| iShares Core S&P Small-Cap ETF | IJR | Direct small-cap peer benchmark. Strategy must beat this to prove stock selection adds value beyond the small-cap factor. |

### Implementation

```python
def load_benchmark(ticker: str, start: date, end: date, db) -> pd.Series:
    """
    Load benchmark daily prices and compute returns.
    Uses the same date range and starting capital as the strategy.
    """
    prices = db.execute("""
        SELECT date, close
        FROM sep
        WHERE ticker = ?
          AND date BETWEEN ? AND ?
        ORDER BY date ASC
    """, [ticker, start, end]).fetchall()

    df = pd.DataFrame(prices, columns=['date', 'close'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    df['return'] = df['close'].pct_change()

    return df


def compare_to_benchmarks(portfolio: Portfolio,
                          benchmarks: dict,
                          starting_capital: float = 100_000) -> pd.DataFrame:
    """
    Compare strategy to benchmarks over the same period.

    Parameters:
        portfolio: Completed backtest portfolio
        benchmarks: Dict of {name: benchmark_df} from load_benchmark()
        starting_capital: Starting capital for normalization

    Returns:
        DataFrame with columns for strategy and each benchmark equity curves
    """
    # Strategy equity curve
    strategy_values = pd.DataFrame(portfolio.daily_values)
    strategy_values['date'] = pd.to_datetime(strategy_values['date'])
    strategy_values = strategy_values.set_index('date')

    combined = pd.DataFrame(index=strategy_values.index)
    combined['Strategy'] = strategy_values['value']

    for name, bench_df in benchmarks.items():
        # Align benchmark to strategy dates
        bench_aligned = bench_df.reindex(combined.index, method='ffill')
        # Normalize to starting capital
        bench_equity = (1 + bench_aligned['return'].fillna(0)).cumprod()
        combined[name] = bench_equity * starting_capital

    return combined


def compute_benchmark_metrics(combined: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all metrics for strategy and benchmarks side by side.
    """
    results = {}

    for col in combined.columns:
        equity = combined[col]
        daily_returns = equity.pct_change().dropna()

        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        years = (equity.index[-1] - equity.index[0]).days / 365.25
        cagr = (equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1

        ann_vol = daily_returns.std() * np.sqrt(252)

        excess = daily_returns - 0.02 / 252
        sharpe = excess.mean() * 252 / ann_vol if ann_vol > 0 else 0

        downside = daily_returns[daily_returns < 0]
        downside_std = np.sqrt(np.mean(downside ** 2)) * np.sqrt(252)
        sortino = ((daily_returns.mean() * 252 - 0.02) / downside_std
                   if downside_std > 0 else 0)

        running_max = equity.cummax()
        drawdowns = (equity - running_max) / running_max
        max_dd = drawdowns.min()

        calmar = cagr / abs(max_dd) if max_dd != 0 else 0

        results[col] = {
            'Total Return': f"{total_return * 100:.1f}%",
            'CAGR': f"{cagr * 100:.2f}%",
            'Volatility': f"{ann_vol * 100:.2f}%",
            'Sharpe': f"{sharpe:.3f}",
            'Sortino': f"{sortino:.3f}",
            'Calmar': f"{calmar:.3f}",
            'Max Drawdown': f"{max_dd * 100:.2f}%",
        }

    return pd.DataFrame(results)


def compute_alpha(strategy_returns: pd.Series,
                  benchmark_returns: pd.Series) -> dict:
    """
    Compute alpha (excess return) and information ratio vs a benchmark.

    Alpha = annualized(strategy_return - benchmark_return)
    Information Ratio = Alpha / Tracking Error
    Tracking Error = std(strategy_return - benchmark_return) * sqrt(252)
    """
    # Align dates
    aligned = pd.DataFrame({
        'strategy': strategy_returns,
        'benchmark': benchmark_returns,
    }).dropna()

    active_returns = aligned['strategy'] - aligned['benchmark']

    alpha = active_returns.mean() * 252  # annualized
    tracking_error = active_returns.std() * np.sqrt(252)
    info_ratio = alpha / tracking_error if tracking_error > 0 else 0

    return {
        'alpha_annualized': alpha,
        'tracking_error': tracking_error,
        'information_ratio': info_ratio,
    }
```

---

## 10. Tools and Implementation

### Option A: VectorBT Pro

VectorBT Pro is a professional-grade backtesting framework optimized for vectorized operations. It handles portfolio simulation, metric calculation, and visualization out of the box.

```python
import vectorbtpro as vbt
import pandas as pd
import numpy as np


def run_backtest_vectorbt(signals_df: pd.DataFrame,
                          prices_df: pd.DataFrame,
                          starting_cash: float = 100_000) -> vbt.Portfolio:
    """
    Run the backtest using VectorBT Pro.

    Parameters:
        signals_df: DataFrame indexed by date, columns = tickers.
                    Values: 1 = buy/hold, 0 = no position.
                    Generated by running the screening pipeline for each month
                    and forward-filling until next rebalance.
        prices_df: DataFrame of adjusted close prices, same shape as signals_df.
        starting_cash: Starting portfolio value.

    Returns:
        VectorBT Portfolio object with full analytics.
    """

    # Generate entry/exit signals from the position matrix
    # Entry: signal goes from 0 to 1
    # Exit: signal goes from 1 to 0
    entries = signals_df.diff().fillna(signals_df) > 0
    exits = signals_df.diff().fillna(0) < 0

    # Run portfolio simulation
    pf = vbt.Portfolio.from_signals(
        close=prices_df,
        entries=entries,
        exits=exits,
        size=0.04,             # 4% per position
        size_type='targetpercent',
        init_cash=starting_cash,
        fees=0.001,            # 10 bps
        freq='1D',
        cash_sharing=True,     # shared cash across all assets
        call_seq='auto',       # sell before buy
        group_by=True,         # group all assets into one portfolio
    )

    return pf


def generate_signals_matrix(rebalance_dates: list,
                            all_dates: pd.DatetimeIndex,
                            all_tickers: list,
                            db) -> pd.DataFrame:
    """
    Build the full signals matrix for VectorBT.

    Returns DataFrame where each cell is 1 (hold this stock) or 0 (don't).
    Signals are set at each rebalance date and forward-filled to the next.
    """
    signals = pd.DataFrame(0, index=all_dates, columns=all_tickers)

    for rebal_date in rebalance_dates:
        top_25 = run_screening_pipeline(rebal_date, db)
        for ticker in top_25:
            if ticker in signals.columns:
                signals.loc[rebal_date, ticker] = 1

    # Forward-fill signals between rebalance dates
    for i in range(len(rebalance_dates) - 1):
        current = rebalance_dates[i]
        next_rebal = rebalance_dates[i + 1]
        mask = (signals.index >= current) & (signals.index < next_rebal)
        signals.loc[mask] = signals.loc[current].values

    # Fill last period
    last_rebal = rebalance_dates[-1]
    signals.loc[signals.index >= last_rebal] = signals.loc[last_rebal].values

    return signals


def vectorbt_report(pf: vbt.Portfolio):
    """Print VectorBT's built-in metrics."""
    print(pf.stats())

    # Additional custom metrics
    print(f"\nSharpe Ratio:  {pf.sharpe_ratio():.3f}")
    print(f"Sortino Ratio: {pf.sortino_ratio():.3f}")
    print(f"Calmar Ratio:  {pf.calmar_ratio():.3f}")
    print(f"Max Drawdown:  {pf.max_drawdown() * 100:.2f}%")
    print(f"Total Return:  {pf.total_return() * 100:.2f}%")
    print(f"Total Trades:  {pf.trades.count()}")
    print(f"Win Rate:      {pf.trades.win_rate() * 100:.2f}%")
    print(f"Profit Factor: {pf.trades.profit_factor():.2f}")
```

### Option B: Custom Python (Full Implementation)

For maximum control and transparency, use the custom engine defined in Sections 5-6 above. Here is the complete orchestration script.

```python
"""
backtest_runner.py
Full backtest orchestration script for the Emerging Growth Strategy.

Usage:
    python backtest_runner.py --db sharadar.db --start 2014-01-02 --end 2024-12-31

Dependencies:
    pip install pandas numpy matplotlib exchange-calendars duckdb
"""

import argparse
import duckdb
import pandas as pd
import numpy as np
from datetime import date
from pathlib import Path

# Import all functions from Sections 4-9
# (In production, these would be in separate modules)


def main():
    parser = argparse.ArgumentParser(description='Emerging Growth Strategy Backtest')
    parser.add_argument('--db', type=str, required=True,
                        help='Path to Sharadar DuckDB database')
    parser.add_argument('--start', type=str, default='2014-01-02',
                        help='Backtest start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, default='2024-12-31',
                        help='Backtest end date (YYYY-MM-DD)')
    parser.add_argument('--capital', type=float, default=100_000,
                        help='Starting capital')
    parser.add_argument('--cost-bps', type=int, default=10,
                        help='Transaction cost in basis points')
    parser.add_argument('--output-dir', type=str, default='./backtest_results',
                        help='Output directory for reports and charts')
    args = parser.parse_args()

    # Connect to database
    db = duckdb.connect(args.db, read_only=True)
    db.execute("SET threads = 8")
    db.execute("SET memory_limit = '8GB'")

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    print(f"Running backtest: {start_date} to {end_date}")
    print(f"Starting capital: ${args.capital:,.2f}")
    print(f"Transaction cost: {args.cost_bps} bps")
    print()

    # --- Run main backtest ---
    global TRANSACTION_COST
    TRANSACTION_COST = args.cost_bps / 10_000

    portfolio = run_backtest(db)

    # --- Generate metrics report ---
    report = generate_metrics_report(portfolio)
    print_metrics_report(report)

    # --- Subperiod analysis ---
    subperiod_results = run_subperiod_analysis(portfolio)
    print_subperiod_report(subperiod_results)

    # --- Bootstrap validation ---
    daily_returns = compute_daily_returns(portfolio)
    bootstrap_results = bootstrap_validation(daily_returns, n_iterations=10_000)
    print_bootstrap_report(bootstrap_results)

    # --- Benchmark comparison ---
    spy_df = load_benchmark('SPY', start_date, end_date, db)
    ijr_df = load_benchmark('IJR', start_date, end_date, db)

    combined = compare_to_benchmarks(portfolio, {
        'S&P 500 (SPY)': spy_df,
        'Small-Cap (IJR)': ijr_df,
    })

    comparison = compute_benchmark_metrics(combined)
    print(f"\n{'=' * 70}")
    print("BENCHMARK COMPARISON")
    print(f"{'=' * 70}")
    print(comparison.to_string())

    # Alpha vs each benchmark
    strategy_returns = daily_returns
    for name, bench in [('SPY', spy_df), ('IJR', ijr_df)]:
        alpha_stats = compute_alpha(strategy_returns, bench['return'].dropna())
        print(f"\nAlpha vs {name}: "
              f"{alpha_stats['alpha_annualized'] * 100:.2f}% annualized")
        print(f"Information Ratio vs {name}: "
              f"{alpha_stats['information_ratio']:.3f}")

    # --- Generate charts ---
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generate_all_charts(portfolio, combined, output_dir)

    # --- Save trade log ---
    trade_df = compute_trade_returns(portfolio)
    trade_df.to_csv(output_dir / 'trade_log.csv', index=False)
    print(f"\nTrade log saved to {output_dir / 'trade_log.csv'}")

    # --- Save daily values ---
    values_df = pd.DataFrame(portfolio.daily_values)
    values_df.to_csv(output_dir / 'daily_values.csv', index=False)
    print(f"Daily values saved to {output_dir / 'daily_values.csv'}")

    db.close()
    print("\nBacktest complete.")


if __name__ == '__main__':
    main()
```

---

## 11. Output Reports

### Equity Curve Chart

```python
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker


def plot_equity_curve(combined: pd.DataFrame, output_path: str):
    """
    Plot strategy equity curve vs benchmarks.
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    colors = {
        'Strategy': '#1a5276',
        'S&P 500 (SPY)': '#aab7b8',
        'Small-Cap (IJR)': '#d4ac0d',
    }

    for col in combined.columns:
        ax.plot(combined.index, combined[col] / 1000,
                label=col, color=colors.get(col, 'gray'),
                linewidth=2 if col == 'Strategy' else 1.2)

    ax.set_title('Emerging Growth Strategy vs Benchmarks (2014-2024)',
                 fontsize=14, fontweight='bold')
    ax.set_ylabel('Portfolio Value ($000s)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.legend(loc='upper left', fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, p: f'${x:,.0f}K'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.grid(True, alpha=0.3)
    ax.set_xlim(combined.index[0], combined.index[-1])

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Equity curve saved to {output_path}")
```

### Monthly Returns Heatmap

```python
def plot_monthly_returns_heatmap(portfolio: Portfolio, output_path: str):
    """
    Plot a heatmap of monthly returns with years on Y-axis and months on X-axis.
    """
    values = pd.DataFrame(portfolio.daily_values)
    values['date'] = pd.to_datetime(values['date'])
    values = values.set_index('date')

    # Resample to monthly and compute returns
    monthly = values['value'].resample('ME').last()
    monthly_returns = monthly.pct_change().dropna()

    # Pivot into year x month matrix
    returns_matrix = pd.DataFrame({
        'year': monthly_returns.index.year,
        'month': monthly_returns.index.month,
        'return': monthly_returns.values * 100,
    })
    pivot = returns_matrix.pivot(index='year', columns='month', values='return')
    pivot.columns = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

    fig, ax = plt.subplots(figsize=(14, 8))

    # Color map: red for negative, green for positive
    cmap = plt.cm.RdYlGn
    norm = plt.Normalize(vmin=-15, vmax=15)

    im = ax.imshow(pivot.values, cmap=cmap, norm=norm, aspect='auto')

    # Add text annotations
    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.iloc[i, j]
            if not np.isnan(val):
                color = 'white' if abs(val) > 10 else 'black'
                ax.text(j, i, f'{val:.1f}%', ha='center', va='center',
                        fontsize=9, color=color)

    ax.set_xticks(range(12))
    ax.set_xticklabels(pivot.columns, fontsize=10)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, fontsize=10)

    ax.set_title('Monthly Returns Heatmap (%)', fontsize=14, fontweight='bold')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label('Monthly Return (%)', fontsize=10)

    # Add annual returns on the right
    annual_returns = values['value'].resample('YE').last().pct_change().dropna()
    for i, (yr, ret) in enumerate(
        zip(pivot.index, annual_returns.values * 100)
    ):
        if i < len(pivot.index):
            ax.text(12.5, i, f'{ret:.1f}%', ha='center', va='center',
                    fontsize=10, fontweight='bold')
    ax.text(12.5, -0.7, 'Annual', ha='center', va='center',
            fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Monthly returns heatmap saved to {output_path}")
```

### Drawdown Chart

```python
def plot_drawdown(portfolio: Portfolio, output_path: str):
    """
    Plot the drawdown curve over time.
    """
    dd = calc_drawdown_series(portfolio)

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.fill_between(dd.index, dd.values * 100, 0,
                    color='#c0392b', alpha=0.4)
    ax.plot(dd.index, dd.values * 100, color='#c0392b', linewidth=0.8)

    ax.set_title('Portfolio Drawdown (2014-2024)',
                 fontsize=14, fontweight='bold')
    ax.set_ylabel('Drawdown (%)', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda x, p: f'{x:.0f}%'))
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
    ax.grid(True, alpha=0.3)
    ax.set_xlim(dd.index[0], dd.index[-1])

    # Annotate max drawdown
    max_dd_idx = dd.idxmin()
    max_dd_val = dd.min() * 100
    ax.annotate(f'Max DD: {max_dd_val:.1f}%',
                xy=(max_dd_idx, max_dd_val),
                xytext=(max_dd_idx + pd.Timedelta(days=180), max_dd_val - 3),
                arrowprops=dict(arrowstyle='->', color='black'),
                fontsize=11, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Drawdown chart saved to {output_path}")
```

### Year-by-Year Performance Table

```python
def generate_yearly_table(portfolio: Portfolio,
                          benchmarks: dict = None) -> pd.DataFrame:
    """
    Generate a year-by-year performance table.
    """
    values = pd.DataFrame(portfolio.daily_values)
    values['date'] = pd.to_datetime(values['date'])
    values = values.set_index('date')

    daily_returns = values['value'].pct_change().dropna()

    years = sorted(daily_returns.index.year.unique())
    rows = []

    for year in years:
        yr_returns = daily_returns[daily_returns.index.year == year]
        yr_equity = values['value'][values.index.year == year]

        annual_return = (yr_equity.iloc[-1] / yr_equity.iloc[0]) - 1
        volatility = yr_returns.std() * np.sqrt(252)

        # Sharpe for this year
        excess = yr_returns - 0.02 / 252
        sharpe = (excess.mean() * 252 / volatility
                  if volatility > 0 else 0)

        # Max drawdown for this year
        running_max = yr_equity.cummax()
        dd = (yr_equity - running_max) / running_max
        max_dd = dd.min()

        row = {
            'Year': year,
            'Return': f'{annual_return * 100:.1f}%',
            'Volatility': f'{volatility * 100:.1f}%',
            'Sharpe': f'{sharpe:.2f}',
            'Max DD': f'{max_dd * 100:.1f}%',
        }

        rows.append(row)

    return pd.DataFrame(rows)


def print_yearly_table(yearly_df: pd.DataFrame):
    """Print the year-by-year table in a clean format."""
    print(f"\n{'=' * 60}")
    print("YEAR-BY-YEAR PERFORMANCE")
    print(f"{'=' * 60}")
    print(yearly_df.to_string(index=False))
```

### Rolling 12-Month Sharpe Chart

```python
def plot_rolling_sharpe(portfolio: Portfolio, output_path: str,
                        window: int = 252):
    """
    Plot rolling 12-month Sharpe ratio over time.
    Window = 252 trading days (approximately 12 months).
    """
    daily_returns = compute_daily_returns(portfolio)
    daily_rf = 0.02 / 252

    excess = daily_returns - daily_rf
    rolling_mean = excess.rolling(window=window).mean() * 252
    rolling_vol = daily_returns.rolling(window=window).std() * np.sqrt(252)
    rolling_sharpe = rolling_mean / rolling_vol

    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(rolling_sharpe.index, rolling_sharpe.values,
            color='#2c3e50', linewidth=1.5)
    ax.axhline(y=0, color='red', linestyle='--', alpha=0.5)
    ax.axhline(y=1.0, color='green', linestyle='--', alpha=0.3,
               label='Sharpe = 1.0')

    ax.fill_between(rolling_sharpe.index,
                    rolling_sharpe.values, 0,
                    where=rolling_sharpe.values >= 0,
                    color='#27ae60', alpha=0.2)
    ax.fill_between(rolling_sharpe.index,
                    rolling_sharpe.values, 0,
                    where=rolling_sharpe.values < 0,
                    color='#c0392b', alpha=0.2)

    ax.set_title(f'Rolling {window}-Day Sharpe Ratio',
                 fontsize=14, fontweight='bold')
    ax.set_ylabel('Sharpe Ratio', fontsize=12)
    ax.set_xlabel('Date', fontsize=12)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"Rolling Sharpe chart saved to {output_path}")
```

### Trade Statistics Summary

```python
def print_trade_summary(portfolio: Portfolio):
    """Print a comprehensive trade statistics summary."""
    trade_df = compute_trade_returns(portfolio)
    wl_stats = calc_win_loss_stats(trade_df)
    win_rate, winners, losers = calc_win_rate(trade_df)

    print(f"\n{'=' * 60}")
    print("TRADE STATISTICS")
    print(f"{'=' * 60}")
    print(f"Total Round-Trip Trades: {len(trade_df)}")
    print(f"Winners:                 {winners}")
    print(f"Losers:                  {losers}")
    print(f"Win Rate:                {win_rate * 100:.2f}%")
    print(f"")
    print(f"Avg Win:                 {wl_stats['avg_win_pct']:.2f}%")
    print(f"Avg Loss:                {wl_stats['avg_loss_pct']:.2f}%")
    print(f"Win/Loss Ratio:          {wl_stats['win_loss_ratio']:.2f}")
    print(f"Profit Factor:           {calc_profit_factor(trade_df):.2f}")
    print(f"")
    print(f"Avg Win ($):             ${wl_stats['avg_win_dollar']:,.2f}")
    print(f"Avg Loss ($):            ${wl_stats['avg_loss_dollar']:,.2f}")
    print(f"Expectancy (per trade):  {wl_stats['expectancy_pct']:.2f}%")
    print(f"Expectancy ($):          ${wl_stats['expectancy_dollar']:,.2f}")
    print(f"")
    print(f"Avg Holding Period:      {wl_stats['avg_holding_days']:.0f} days")
    print(f"Median Holding Period:   {wl_stats['median_holding_days']:.0f} days")

    # Distribution of returns
    print(f"\nReturn Distribution:")
    percentiles = [5, 10, 25, 50, 75, 90, 95]
    for p in percentiles:
        val = np.percentile(trade_df['net_return'] * 100, p)
        print(f"  {p}th percentile:       {val:.1f}%")

    # Biggest winners and losers
    top5 = trade_df.nlargest(5, 'net_return')
    bot5 = trade_df.nsmallest(5, 'net_return')

    print(f"\nTop 5 Winners:")
    for _, row in top5.iterrows():
        print(f"  {row['ticker']:8s} {row['date']}  +{row['net_return']*100:.1f}%")

    print(f"\nTop 5 Losers:")
    for _, row in bot5.iterrows():
        print(f"  {row['ticker']:8s} {row['date']}  {row['net_return']*100:.1f}%")
```

### Master Chart Generation

```python
def generate_all_charts(portfolio: Portfolio,
                        combined: pd.DataFrame,
                        output_dir: Path):
    """Generate all output charts and save to the output directory."""
    plot_equity_curve(combined, str(output_dir / 'equity_curve.png'))
    plot_monthly_returns_heatmap(portfolio,
                                str(output_dir / 'monthly_returns.png'))
    plot_drawdown(portfolio, str(output_dir / 'drawdown.png'))
    plot_rolling_sharpe(portfolio, str(output_dir / 'rolling_sharpe.png'))

    # Year-by-year table
    yearly = generate_yearly_table(portfolio)
    print_yearly_table(yearly)
    yearly.to_csv(output_dir / 'yearly_performance.csv', index=False)

    # Trade summary
    print_trade_summary(portfolio)
```

---

## Appendix A: Required Python Dependencies

```
# requirements.txt
pandas>=2.0
numpy>=1.24
matplotlib>=3.7
duckdb>=0.9
exchange-calendars>=4.2
# Optional:
# vectorbtpro  (commercial license required)
```

## Appendix B: Quick Validation Checklist

Before trusting any backtest results, verify ALL of the following:

- [ ] **No look-ahead bias**: Fundamental data filtered by `datekey <= rebalance_date`
- [ ] **Survivorship bias handled**: Delisted stocks included in historical universe
- [ ] **Transaction costs applied**: Both buy and sell sides
- [ ] **Point-in-time prices**: No future adjusted prices used
- [ ] **Correct rebalance dates**: First trading day of each month, not calendar day
- [ ] **Split handling**: Using adjusted prices OR manual split adjustment
- [ ] **Cash management**: Uninvested cash tracked, not assumed fully invested
- [ ] **Delisting handling**: Explicit treatment for stocks delisted mid-holding
- [ ] **Quality filter ordering**: Filters applied BEFORE ranking, not after
- [ ] **Benchmark alignment**: Same start date, same starting capital
- [ ] **Bootstrap CI excludes zero**: Statistical significance confirmed
- [ ] **Subperiod consistency**: Both halves show positive Sharpe

## Appendix C: Common Pitfalls and Debugging

| Symptom | Likely Cause | Fix |
|---|---|---|
| CAGR > 30% | Look-ahead bias in fundamentals | Check `datekey` filtering |
| Max drawdown < 10% | Missing 2020 COVID crash or 2022 bear | Verify price data covers March 2020 |
| Win rate > 60% | Survivorship bias (only tested on survivors) | Include delisted stocks |
| Sharpe > 2.0 | Multiple biases compounding | Re-examine every data access point |
| 0 trades in some months | Universe too restrictive or data gaps | Check filter thresholds and data coverage |
| Negative cash balance | Buy execution before sells | Enforce sell-first, buy-second order |
| Position weights > 5% | Rebalancing not working | Check rebalance threshold and math |
| Benchmark returns = 0 | Benchmark ticker not in database | Load SPY/IJR separately if needed |
