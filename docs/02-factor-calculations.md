# Factor Calculations: Implementation Guide

## 1. Overview

The emerging growth composite scoring model ranks stocks using four factors that capture complementary dimensions of growth and momentum. Each stock receives a score on a 0--100 scale.

**Composite Score Formula:**

```
Composite = 0.40 * RS_Percentile
          + 0.20 * min(EPS_Growth, 100)
          + 0.20 * min(Revenue_Growth, 100)
          + 0.20 * Price_vs_52W_High
```

| # | Factor | Weight | What It Captures | Academic Foundation |
|---|--------|--------|------------------|---------------------|
| 1 | Relative Strength Percentile | 40% | Price momentum over 6 months | Jegadeesh & Titman (1993, 2001) |
| 2 | EPS Growth YoY | 20% | Earnings acceleration | Chan, Jegadeesh & Lakonishok (1996) |
| 3 | Revenue Growth YoY | 20% | Top-line business expansion | Lakonishok, Shleifer & Vishny (1994) |
| 4 | Price vs 52-Week High | 20% | Proximity to technical ceiling | George & Hwang (2004) |

### Why These Four Work Together

- **Relative Strength (40%)** is the dominant signal. Decades of evidence show that intermediate-horizon momentum (3--12 months) is the strongest cross-sectional predictor of future returns. It receives double weight because it subsumes much of the information in the other factors while also capturing market sentiment, institutional flows, and information diffusion.

- **EPS Growth (20%)** captures earnings momentum --- the tendency for stocks with recent earnings surprises or acceleration to continue outperforming. It validates that the price momentum is backed by fundamental improvement, not pure speculation.

- **Revenue Growth (20%)** is a harder-to-manipulate confirmation signal. Revenue is less susceptible to accounting games (share buybacks, one-time charges, depreciation changes) than EPS. When both earnings *and* revenue are growing, the signal is far more reliable.

- **Price vs 52-Week High (20%)** measures how close a stock is to breaking out. George & Hwang (2004) showed that nearness to the 52-week high predicts future returns even after controlling for momentum. The mechanism: investors use the 52-week high as an anchor, creating underreaction when stocks approach it. Stocks near their highs that also have strong fundamentals are coiled springs.

The capping of EPS and Revenue growth at 100 prevents a single hyper-growth outlier (e.g., a turnaround with 2000% EPS growth) from dominating the composite score. With capping, the maximum composite score is exactly 100.

---

## 2. Factor 1: Relative Strength Percentile (Weight: 40%)

### Concept

Rank every stock in the investable universe by its 6-month (126 trading days) price return, then convert that rank to a 0--100 percentile. A score of 100 means the stock has the strongest momentum in the universe; a score of 0 means the weakest.

### Mathematical Definition

For stock *i* on date *t*:

```
Return_i = (Price_t / Price_{t-126}) - 1

Percentile_i = rank(Return_i) / N * 100
```

where *N* is the total number of stocks with valid 6-month returns and `rank()` assigns 1 to the lowest return and *N* to the highest.

### Detailed Steps

1. Pull daily adjusted close prices from Sharadar SEP for all stocks in the universe.
2. For each stock, identify the close price 126 trading days ago and the current close.
3. Compute the 6-month total return.
4. Rank all stocks by return (ascending --- lowest return gets rank 1).
5. Convert rank to percentile: `percentile = rank / total_stocks * 100`.

### Data Requirements

- **Table:** Sharadar `SEP` (daily equity prices, split-adjusted)
- **Fields:** `ticker`, `date`, `close` (adjusted close)
- **Lookback:** 126 trading days (~6 calendar months)
- **Universe:** All stocks that have a valid close on both the current date and the date 126 trading days prior

### SQL: Fetch Raw Price Data

```sql
-- Get the current close and the close 126 trading days ago for each ticker.
-- Uses a window function to avoid a self-join.

WITH trading_days AS (
    SELECT DISTINCT date
    FROM sharadar.sep
    WHERE date <= :scoring_date
    ORDER BY date DESC
    LIMIT 127  -- 126 days back + today
),
bounds AS (
    SELECT
        MAX(date) AS current_date,
        MIN(date) AS lookback_date
    FROM trading_days
),
prices AS (
    SELECT
        s.ticker,
        s.date,
        s.close
    FROM sharadar.sep s
    CROSS JOIN bounds b
    WHERE s.date IN (b.current_date, b.lookback_date)
)
SELECT
    curr.ticker,
    curr.close AS price_current,
    prev.close AS price_6mo_ago,
    (curr.close / prev.close) - 1.0 AS return_6m
FROM prices curr
JOIN prices prev
    ON curr.ticker = prev.ticker
WHERE curr.date = (SELECT current_date FROM bounds)
  AND prev.date = (SELECT lookback_date FROM bounds)
  AND prev.close > 0;
```

### Python Implementation

```python
import pandas as pd
import numpy as np
from sqlalchemy import create_engine

def calculate_relative_strength(
    engine,
    scoring_date: str,
    lookback_days: int = 126,
) -> pd.DataFrame:
    """
    Calculate 6-month relative strength percentile for all stocks.

    Parameters
    ----------
    engine : sqlalchemy.Engine
        Database connection.
    scoring_date : str
        Date to score (YYYY-MM-DD). Must be a trading day.
    lookback_days : int
        Number of trading days for the momentum window (default 126).

    Returns
    -------
    pd.DataFrame
        Columns: ticker, return_6m, rs_rank, rs_percentile
    """
    # ------------------------------------------------------------------
    # Step 1: Identify the exact trading day 126 days back
    # ------------------------------------------------------------------
    trading_days_query = """
        SELECT DISTINCT date
        FROM sharadar.sep
        WHERE date <= %(scoring_date)s
        ORDER BY date DESC
        LIMIT %(limit)s
    """
    trading_days = pd.read_sql(
        trading_days_query,
        engine,
        params={"scoring_date": scoring_date, "limit": lookback_days + 1},
    )
    if len(trading_days) < lookback_days + 1:
        raise ValueError(
            f"Only {len(trading_days)} trading days available; "
            f"need {lookback_days + 1}."
        )

    current_date = trading_days["date"].iloc[0]
    lookback_date = trading_days["date"].iloc[-1]

    # ------------------------------------------------------------------
    # Step 2: Pull close prices for both dates
    # ------------------------------------------------------------------
    price_query = """
        SELECT ticker, date, close
        FROM sharadar.sep
        WHERE date IN (%(current_date)s, %(lookback_date)s)
          AND close > 0
    """
    prices = pd.read_sql(
        price_query,
        engine,
        params={"current_date": current_date, "lookback_date": lookback_date},
    )

    current_prices = (
        prices[prices["date"] == current_date]
        .set_index("ticker")["close"]
        .rename("price_current")
    )
    prior_prices = (
        prices[prices["date"] == lookback_date]
        .set_index("ticker")["close"]
        .rename("price_6mo_ago")
    )

    # ------------------------------------------------------------------
    # Step 3: Compute 6-month return (only for stocks present on both dates)
    # ------------------------------------------------------------------
    df = pd.concat([current_prices, prior_prices], axis=1).dropna()
    df["return_6m"] = (df["price_current"] / df["price_6mo_ago"]) - 1.0

    # ------------------------------------------------------------------
    # Step 4: Rank and convert to percentile
    # ------------------------------------------------------------------
    # method="average" handles ties by assigning the mean rank to tied values.
    # ascending=True means lowest return -> lowest rank -> lowest percentile.
    df["rs_rank"] = df["return_6m"].rank(method="average", ascending=True)
    n = len(df)
    df["rs_percentile"] = (df["rs_rank"] / n) * 100.0

    # ------------------------------------------------------------------
    # Step 5: Clean up and return
    # ------------------------------------------------------------------
    result = (
        df[["return_6m", "rs_rank", "rs_percentile"]]
        .reset_index()
        .rename(columns={"index": "ticker"})
        .sort_values("rs_percentile", ascending=False)
    )

    return result
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| **Stock has < 6 months of history** | Excluded from ranking. It will not appear in the output DataFrame because the inner join on both dates drops it. |
| **Stock splits** | Sharadar SEP provides split-adjusted prices. No additional handling needed. As long as you use the `close` field (not `closeunadj`), splits are already accounted for. |
| **Dividends** | Sharadar SEP `close` is split-adjusted but *not* dividend-adjusted by default. For a pure price-momentum signal this is acceptable --- Jegadeesh & Titman's original formulation uses price returns, not total returns. If you want total returns, use `closeadj` if available or adjust manually. |
| **Delistings / survivorship bias** | Stocks that delist between the lookback date and scoring date will not have a current price and are automatically excluded. For backtesting, ensure the universe is reconstructed point-in-time (Section 7). |
| **Ties** | `rank(method="average")` assigns the mean rank to tied stocks. For a universe of 3,000+ stocks, ties are rare and this choice has negligible impact. |
| **Very low-priced stocks** | These can have extreme percentage returns. The universe filter (applied upstream) should exclude sub-$5 stocks. The percentile ranking is also inherently robust to outliers since it compresses returns to a 0--100 scale. |

### Academic Basis

Jegadeesh & Titman, "Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency" (1993) --- demonstrated that a strategy of buying past 3--12 month winners and shorting losers earned ~1% per month. Their 2001 follow-up confirmed the effect persisted out of sample. The 6-month lookback is squarely in the sweet spot of the momentum anomaly and avoids the short-term reversal effect (< 1 month) and long-term reversal (> 12 months).

---

## 3. Factor 2: EPS Growth Year-over-Year (Weight: 20%)

### Concept

Compare the most recent quarterly diluted EPS to the same fiscal quarter one year ago (4 quarters prior). This year-over-year comparison controls for seasonality. The raw growth percentage is then capped at 100 for scoring.

### Mathematical Definition

```
EPS_Growth = (EPS_Q0 - EPS_Q-4) / |EPS_Q-4| * 100

Scored = min(EPS_Growth, 100)
```

where Q0 is the most recently reported quarter and Q-4 is the same quarter one year earlier.

### Detailed Steps

1. For each stock, pull the most recent 8 quarters of fundamental data from Sharadar SF1 (using ARQ --- As Reported Quarterly dimension).
2. Identify the most recent quarter (Q0) and the year-ago quarter (Q-4).
3. Extract diluted EPS (`epsdil`) for both quarters.
4. Calculate year-over-year EPS growth with special handling for negative denominators.
5. Cap the result at 100 for the composite score.

### Data Requirements

- **Table:** Sharadar `SF1` (fundamentals)
- **Dimension:** `ARQ` (As Reported Quarterly)
- **Fields:** `ticker`, `datekey` (filing/knowledge date), `reportperiod` (fiscal quarter end), `calendardate`, `epsdil` (diluted EPS per share, USD)
- **Lookback:** 8 quarters of data to find Q0 and Q-4 reliably

**Critical field distinction:**
- `reportperiod`: The fiscal quarter-end date (e.g., 2025-03-31 for Q1 FY2025).
- `datekey`: The date when Sharadar recorded the data as known --- this is the point-in-time availability date. For backtesting, you must filter on `datekey <= scoring_date` to avoid look-ahead bias.

### SQL: Fetch Quarterly EPS

```sql
-- Pull the 8 most recent quarterly EPS filings for each ticker,
-- using only data known as of the scoring date.

WITH ranked_quarters AS (
    SELECT
        ticker,
        reportperiod,
        datekey,
        calendardate,
        epsdil,
        ROW_NUMBER() OVER (
            PARTITION BY ticker
            ORDER BY reportperiod DESC
        ) AS quarter_rank
    FROM sharadar.sf1
    WHERE dimension = 'ARQ'
      AND datekey <= :scoring_date       -- point-in-time: only use known data
      AND epsdil IS NOT NULL
)
SELECT
    ticker,
    reportperiod,
    datekey,
    calendardate,
    epsdil,
    quarter_rank
FROM ranked_quarters
WHERE quarter_rank <= 8
ORDER BY ticker, quarter_rank;
```

### Python Implementation

```python
import pandas as pd
import numpy as np


def calculate_eps_growth(
    engine,
    scoring_date: str,
) -> pd.DataFrame:
    """
    Calculate year-over-year quarterly EPS growth for all stocks.

    Uses point-in-time data: only fundamentals with datekey <= scoring_date.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    scoring_date : str
        YYYY-MM-DD

    Returns
    -------
    pd.DataFrame
        Columns: ticker, eps_current, eps_prior, eps_growth_raw,
                 eps_growth_capped, eps_growth_flag
    """
    query = """
        WITH ranked AS (
            SELECT
                ticker,
                reportperiod,
                datekey,
                epsdil,
                ROW_NUMBER() OVER (
                    PARTITION BY ticker
                    ORDER BY reportperiod DESC
                ) AS qrank
            FROM sharadar.sf1
            WHERE dimension = 'ARQ'
              AND datekey <= %(scoring_date)s
              AND epsdil IS NOT NULL
        )
        SELECT ticker, reportperiod, epsdil, qrank
        FROM ranked
        WHERE qrank <= 8
        ORDER BY ticker, qrank
    """
    raw = pd.read_sql(query, engine, params={"scoring_date": scoring_date})

    results = []

    for ticker, group in raw.groupby("ticker"):
        group = group.sort_values("qrank")

        if len(group) < 5:
            # Need at least Q0 (rank 1) and Q-4 (rank 5)
            continue

        q0_row = group[group["qrank"] == 1].iloc[0]
        q4_row = group[group["qrank"] == 5].iloc[0]

        eps_current = q0_row["epsdil"]
        eps_prior = q4_row["epsdil"]

        # --- Edge case handling ---
        growth_raw, flag = _compute_eps_growth(eps_current, eps_prior)

        results.append({
            "ticker": ticker,
            "reportperiod_current": q0_row["reportperiod"],
            "reportperiod_prior": q4_row["reportperiod"],
            "eps_current": eps_current,
            "eps_prior": eps_prior,
            "eps_growth_raw": growth_raw,
            "eps_growth_capped": min(growth_raw, 100.0) if growth_raw is not None else None,
            "eps_growth_flag": flag,
        })

    df = pd.DataFrame(results)
    return df


def _compute_eps_growth(
    eps_current: float,
    eps_prior: float,
) -> tuple[float | None, str]:
    """
    Compute EPS growth percentage with comprehensive edge-case handling.

    Returns
    -------
    (growth_pct, flag)
        growth_pct : float or None
        flag       : str describing the case
    """
    # Case 1: Prior EPS is zero -> division by zero
    if eps_prior == 0:
        if eps_current > 0:
            return 100.0, "prior_zero_positive_current"
        elif eps_current == 0:
            return 0.0, "both_zero"
        else:
            return 0.0, "prior_zero_negative_current"

    # Case 2: Turnaround --- prior negative, current positive
    # This is a high-conviction signal: assign maximum raw growth.
    if eps_prior < 0 and eps_current > 0:
        return 999.0, "turnaround"

    # Case 3: Both negative
    if eps_prior < 0 and eps_current < 0:
        # Improving (less negative) should yield a positive growth number.
        # E.g., prior = -1.00, current = -0.50 -> improving by 50%.
        # Standard formula with abs(prior): (-0.50 - (-1.00)) / 1.00 = 50%
        improvement = (eps_current - eps_prior) / abs(eps_prior) * 100.0
        return improvement, "both_negative"

    # Case 4: Deterioration --- prior positive, current negative
    if eps_prior > 0 and eps_current < 0:
        # Standard formula works: (negative - positive) / positive -> large negative %
        growth = (eps_current - eps_prior) / abs(eps_prior) * 100.0
        return growth, "deterioration"

    # Case 5: Normal case --- both positive
    growth = (eps_current - eps_prior) / abs(eps_prior) * 100.0
    return growth, "normal"
```

### Edge Cases (Detailed)

| Scenario | `eps_prior` | `eps_current` | Raw Growth | Flag | Rationale |
|----------|-------------|---------------|------------|------|-----------|
| Normal growth | 1.00 | 1.50 | 50.0% | `normal` | Standard calculation |
| Normal decline | 1.50 | 1.00 | -33.3% | `normal` | Standard calculation |
| Turnaround | -0.50 | 0.30 | 999.0% | `turnaround` | Inflection point --- highest conviction signal. The exact magnitude is meaningless when crossing zero, so we assign a sentinel value that will be capped to 100 in scoring. |
| Both negative, improving | -1.00 | -0.50 | 50.0% | `both_negative` | Loss cut in half. Using `abs(prior)` in denominator makes the math intuitive. |
| Both negative, worsening | -0.50 | -1.00 | -100.0% | `both_negative` | Losses doubled. |
| Prior zero, current positive | 0.00 | 0.50 | 100.0% | `prior_zero_positive_current` | Cannot divide by zero. Assign 100% as a reasonable positive signal. |
| Both zero | 0.00 | 0.00 | 0.0% | `both_zero` | No change. |
| Deterioration | 0.50 | -0.30 | -160.0% | `deterioration` | Swung from profit to loss. Large negative score. |
| **One-time charges** | *varies* | *distorted* | *misleading* | --- | Not handled algorithmically. The scoring model accepts this noise. In practice, momentum (Factor 1) and revenue (Factor 3) provide cross-validation. Optionally, use `epsdil` from the "excluding extraordinary items" line if available. |
| **Fiscal year misalignment** | --- | --- | --- | --- | Sharadar's `reportperiod` reflects the fiscal quarter-end. Comparing Q0 to Q-4 by `reportperiod` rank (not calendar alignment) correctly handles fiscal years that don't align to calendar quarters. Two companies with different fiscal year-ends are both comparing their most recent quarter to the same quarter last year. |

### Academic Basis

Chan, Jegadeesh & Lakonishok, "Momentum Strategies" (1996) --- showed that earnings momentum (measured by standardized unexpected earnings, SUE) predicts future returns independently of price momentum. Using raw YoY EPS growth is a simpler but directionally equivalent signal. The effect is strongest in the 6--12 months following the earnings report, which aligns well with our quarterly rebalancing cadence.

---

## 4. Factor 3: Revenue Growth Year-over-Year (Weight: 20%)

### Concept

Compute year-over-year quarterly revenue growth. Revenue is the top line --- it is harder to manipulate than earnings and validates that business expansion is genuine rather than driven by cost-cutting, buybacks, or accounting changes.

### Mathematical Definition

```
Revenue_Growth = (Revenue_Q0 - Revenue_Q-4) / Revenue_Q-4 * 100

Scored = min(Revenue_Growth, 100)
```

Requirement: `Revenue_Q-4 > 0`. Pre-revenue companies are excluded.

### Detailed Steps

1. Pull last 8 quarters of fundamental data from Sharadar SF1 (`ARQ` dimension).
2. Identify Q0 (most recent) and Q-4 (same quarter last year).
3. Extract `revenue` field for both quarters.
4. Require positive prior-period revenue --- exclude pre-revenue companies.
5. Calculate year-over-year growth and cap at 100 for scoring.

### Data Requirements

- **Table:** Sharadar `SF1`
- **Dimension:** `ARQ`
- **Fields:** `ticker`, `datekey`, `reportperiod`, `revenue`
- **Lookback:** 8 quarters

### SQL: Fetch Quarterly Revenue

```sql
WITH ranked AS (
    SELECT
        ticker,
        reportperiod,
        datekey,
        revenue,
        ROW_NUMBER() OVER (
            PARTITION BY ticker
            ORDER BY reportperiod DESC
        ) AS qrank
    FROM sharadar.sf1
    WHERE dimension = 'ARQ'
      AND datekey <= :scoring_date
      AND revenue IS NOT NULL
)
SELECT ticker, reportperiod, revenue, qrank
FROM ranked
WHERE qrank <= 8
ORDER BY ticker, qrank;
```

### Python Implementation

```python
import pandas as pd
import numpy as np


def calculate_revenue_growth(
    engine,
    scoring_date: str,
) -> pd.DataFrame:
    """
    Calculate year-over-year quarterly revenue growth for all stocks.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    scoring_date : str
        YYYY-MM-DD

    Returns
    -------
    pd.DataFrame
        Columns: ticker, rev_current, rev_prior, rev_growth_raw,
                 rev_growth_capped, rev_growth_flag
    """
    query = """
        WITH ranked AS (
            SELECT
                ticker,
                reportperiod,
                datekey,
                revenue,
                ROW_NUMBER() OVER (
                    PARTITION BY ticker
                    ORDER BY reportperiod DESC
                ) AS qrank
            FROM sharadar.sf1
            WHERE dimension = 'ARQ'
              AND datekey <= %(scoring_date)s
              AND revenue IS NOT NULL
        )
        SELECT ticker, reportperiod, revenue, qrank
        FROM ranked
        WHERE qrank <= 8
        ORDER BY ticker, qrank
    """
    raw = pd.read_sql(query, engine, params={"scoring_date": scoring_date})

    results = []

    for ticker, group in raw.groupby("ticker"):
        group = group.sort_values("qrank")

        if len(group) < 5:
            continue

        q0_row = group[group["qrank"] == 1].iloc[0]
        q4_row = group[group["qrank"] == 5].iloc[0]

        rev_current = q0_row["revenue"]
        rev_prior = q4_row["revenue"]

        growth_raw, flag = _compute_revenue_growth(rev_current, rev_prior)

        results.append({
            "ticker": ticker,
            "reportperiod_current": q0_row["reportperiod"],
            "reportperiod_prior": q4_row["reportperiod"],
            "rev_current": rev_current,
            "rev_prior": rev_prior,
            "rev_growth_raw": growth_raw,
            "rev_growth_capped": min(growth_raw, 100.0) if growth_raw is not None else None,
            "rev_growth_flag": flag,
        })

    df = pd.DataFrame(results)
    return df


def _compute_revenue_growth(
    rev_current: float,
    rev_prior: float,
) -> tuple[float | None, str]:
    """
    Compute revenue growth with edge-case handling.

    Returns
    -------
    (growth_pct, flag)
    """
    # Pre-revenue or zero-revenue prior period: cannot compute meaningful growth
    if rev_prior is None or rev_prior <= 0:
        return None, "invalid_prior_revenue"

    # Current revenue is negative or zero (extremely rare, but possible
    # with revenue restatements or accounting adjustments)
    if rev_current is None or rev_current < 0:
        return None, "invalid_current_revenue"

    # Normal calculation
    growth = (rev_current - rev_prior) / rev_prior * 100.0

    # Flag suspiciously large growth that might indicate M&A
    flag = "normal"
    if growth > 200.0:
        flag = "possible_inorganic"  # May be M&A-driven; not filtered, just flagged

    return growth, flag
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| **Pre-revenue companies** (biotech, early-stage) | Excluded (`rev_prior <= 0` guard). These stocks can still score on the other 3 factors; this factor contributes 0 to their composite. See the assembly section for handling missing factors. |
| **Negative or zero prior revenue** | Excluded. Negative revenue can occur in rare cases (e.g., revenue reversals). The growth calculation is meaningless here. |
| **Revenue restatements** | Sharadar updates historical records when companies restate. For backtesting, use `datekey` to ensure you only see the data that was available at the time. However, note that Sharadar's point-in-time handling of restatements is imperfect --- the `datekey` may reflect the restatement date, not the original filing. This is an accepted limitation. |
| **M&A-driven inorganic revenue jumps** | Flagged as `possible_inorganic` when growth exceeds 200%, but not filtered out. The 100-cap in scoring limits the damage. A company that doubled revenue via acquisition still gets a capped score of 100, same as a 100% organic grower. |
| **Currency effects** | Sharadar normalizes revenue to USD. For multinational companies, large FX swings can inflate or deflate reported growth. This is an accepted limitation --- hedging against FX noise would require segment-level data that isn't available. |
| **Fiscal quarter alignment** | Same approach as EPS: we compare Q0 to Q-4 by `reportperiod` rank. A company with a January fiscal year-end compares its January quarter to the prior year's January quarter. |

### Rationale for Inclusion

Revenue growth validates earnings growth. A company can grow EPS through buybacks, cost-cutting, or accounting changes --- but revenue growth requires actual customers paying actual money. When a stock has strong momentum, strong EPS growth, *and* strong revenue growth, the probability that all three signals are coincidentally false is low. Revenue is the hardest of the three to fake.

Additionally, for emerging growth companies, revenue growth often *leads* earnings growth. A fast-growing company may be reinvesting aggressively (suppressing current earnings) while growing revenue at 50%+ per year. The revenue factor ensures these companies are not penalized for growth-oriented capital allocation.

---

## 5. Factor 4: Price vs 52-Week High (Weight: 20%)

### Concept

Measure how close the current price is to its trailing 252-trading-day high. A stock trading at its 52-week high scores 100; a stock 50% below its high scores 50.

### Mathematical Definition

```
Price_vs_52W_High = (Current_Close / Max_Close_252d) * 100
```

The result is naturally bounded between 0 and 100 (assuming no negative prices).

### Detailed Steps

1. For each stock, pull the last 252 trading days of adjusted close prices from Sharadar SEP.
2. Find the maximum close in that 252-day window.
3. Divide the current close by that maximum and multiply by 100.
4. Result is a percentage: 100 means the stock is at its 52-week high.

### Data Requirements

- **Table:** Sharadar `SEP`
- **Fields:** `ticker`, `date`, `close` (split-adjusted)
- **Lookback:** 252 trading days (~12 calendar months)

### SQL: Compute Directly in Database

```sql
-- Compute price vs 52-week high for all stocks in a single query.
-- This is efficient because it avoids pulling 252 rows per ticker into Python.

WITH trading_days AS (
    -- Identify the 252 most recent trading days up to scoring_date
    SELECT DISTINCT date
    FROM sharadar.sep
    WHERE date <= :scoring_date
    ORDER BY date DESC
    LIMIT 252
),
date_bounds AS (
    SELECT
        MAX(date) AS current_date,
        MIN(date) AS lookback_start
    FROM trading_days
),
highs AS (
    SELECT
        s.ticker,
        MAX(s.close) AS high_252d
    FROM sharadar.sep s
    CROSS JOIN date_bounds b
    WHERE s.date BETWEEN b.lookback_start AND b.current_date
      AND s.close > 0
    GROUP BY s.ticker
),
current_prices AS (
    SELECT
        s.ticker,
        s.close AS current_close
    FROM sharadar.sep s
    CROSS JOIN date_bounds b
    WHERE s.date = b.current_date
      AND s.close > 0
)
SELECT
    c.ticker,
    c.current_close,
    h.high_252d,
    (c.current_close / h.high_252d) * 100.0 AS price_vs_high
FROM current_prices c
JOIN highs h ON c.ticker = h.ticker;
```

### Python Implementation

```python
import pandas as pd
import numpy as np


def calculate_price_vs_52w_high(
    engine,
    scoring_date: str,
    lookback_days: int = 252,
) -> pd.DataFrame:
    """
    Calculate price as a percentage of 52-week high for all stocks.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    scoring_date : str
        YYYY-MM-DD
    lookback_days : int
        Number of trading days (default 252).

    Returns
    -------
    pd.DataFrame
        Columns: ticker, current_close, high_252d, price_vs_high
    """
    # ------------------------------------------------------------------
    # Step 1: Determine the date range
    # ------------------------------------------------------------------
    td_query = """
        SELECT DISTINCT date
        FROM sharadar.sep
        WHERE date <= %(scoring_date)s
        ORDER BY date DESC
        LIMIT %(limit)s
    """
    trading_days = pd.read_sql(
        td_query, engine, params={"scoring_date": scoring_date, "limit": lookback_days}
    )
    if len(trading_days) < 2:
        raise ValueError("Insufficient trading day history.")

    current_date = trading_days["date"].iloc[0]
    lookback_start = trading_days["date"].iloc[-1]

    # ------------------------------------------------------------------
    # Step 2: Pull all close prices in the window (batch query)
    # ------------------------------------------------------------------
    price_query = """
        SELECT ticker, date, close
        FROM sharadar.sep
        WHERE date BETWEEN %(start)s AND %(end)s
          AND close > 0
    """
    prices = pd.read_sql(
        price_query,
        engine,
        params={"start": lookback_start, "end": current_date},
    )

    # ------------------------------------------------------------------
    # Step 3: Compute 52-week high per ticker
    # ------------------------------------------------------------------
    highs = prices.groupby("ticker")["close"].max().rename("high_252d")

    # ------------------------------------------------------------------
    # Step 4: Get current price per ticker
    # ------------------------------------------------------------------
    current = (
        prices[prices["date"] == current_date]
        .set_index("ticker")["close"]
        .rename("current_close")
    )

    # ------------------------------------------------------------------
    # Step 5: Combine and compute the ratio
    # ------------------------------------------------------------------
    df = pd.concat([current, highs], axis=1).dropna()
    df["price_vs_high"] = (df["current_close"] / df["high_252d"]) * 100.0

    # Sanity check: should never exceed 100 (current <= max by definition)
    assert (df["price_vs_high"] <= 100.01).all(), "Price vs high exceeds 100%"
    df["price_vs_high"] = df["price_vs_high"].clip(upper=100.0)

    return df.reset_index().rename(columns={"index": "ticker"})
```

### Edge Cases

| Scenario | Handling |
|----------|----------|
| **Stock with < 252 days of history** | Uses whatever history is available. A stock with 60 days of history will have its "52-week high" computed over those 60 days. This is acceptable --- new IPOs with strong early performance should not be penalized. |
| **Stock splits** | Sharadar SEP `close` is split-adjusted. A 2:1 split does not create a false "50% below high" reading because all historical prices are adjusted downward. Always use `close`, never `closeunadj`. |
| **Stocks at all-time highs** | Score = 100.0. This is the maximum and represents the strongest possible signal for this factor. |
| **Stocks that were halted or had no trading** | If a stock has no `close` on the current date (trading halt, suspension), it will be excluded from `current` and thus from the output. |
| **Ex-dividend price drops** | A stock paying a large special dividend may drop significantly on the ex-date. Since Sharadar's `close` is split-adjusted but not dividend-adjusted, this creates a real (if temporary) drop in the price-vs-high metric. This is actually desirable behavior --- the stock genuinely did lose price momentum. |

### Academic Basis

George & Hwang, "The 52-Week High and Momentum Investing" (2004) --- found that a stock's nearness to its 52-week high is a better predictor of future returns than conventional momentum measures in many specifications. Their explanation: traders use the 52-week high as a psychological anchor. When good news pushes a stock toward its high, traders are reluctant to bid it above that level, creating underreaction. Once the stock breaks through, the removal of this resistance often triggers further gains.

Li & Yu (2012) extended this to show the effect is stronger for stocks with high analyst coverage and institutional ownership --- exactly the emerging growth universe we target.

---

## 6. Composite Score Assembly

### Full Formula with Capping

```
Composite = 0.40 * RS_Percentile
          + 0.20 * min(EPS_Growth, 100)
          + 0.20 * min(Revenue_Growth, 100)
          + 0.20 * Price_vs_52W_High
```

### Score Range Analysis

| Component | Min | Max | Weighted Min | Weighted Max |
|-----------|-----|-----|--------------|--------------|
| RS Percentile (40%) | 0 | 100 | 0 | 40 |
| EPS Growth, capped (20%) | large negative | 100 | large negative | 20 |
| Revenue Growth, capped (20%) | 0 (excluded if negative) | 100 | 0 | 20 |
| Price vs 52W High (20%) | ~0 | 100 | ~0 | 20 |
| **Composite** | **large negative** | **100** | --- | --- |

**Why cap at 100?** Without capping, a turnaround stock with 999% EPS growth would score 0.20 * 999 = 199.8 on that factor alone --- completely drowning out the other three factors. Capping at 100 ensures no single factor can contribute more than its allocated weight to the composite. A stock with 100% EPS growth and a stock with 2000% EPS growth receive the same score on this factor, which is the correct behavior: both demonstrate exceptional growth, and the difference between "very fast" and "absurdly fast" is mostly noise.

**Floor behavior:** The composite can go negative if EPS growth is deeply negative (e.g., a company whose earnings collapsed). In practice, such stocks will also have weak momentum (low RS percentile) and a low price-vs-high reading, producing a strongly negative composite that correctly ranks them at the bottom.

### Python: Full Composite Scoring Function

```python
import pandas as pd
import numpy as np
from sqlalchemy import create_engine


def compute_composite_scores(
    engine,
    scoring_date: str,
) -> pd.DataFrame:
    """
    Compute the 4-factor composite score for all stocks in the universe.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    scoring_date : str
        YYYY-MM-DD. Must be a trading day.

    Returns
    -------
    pd.DataFrame
        Columns: ticker, rs_percentile, eps_growth_capped, rev_growth_capped,
                 price_vs_high, composite_score
        Sorted by composite_score descending.
    """
    # ------------------------------------------------------------------
    # Step 1: Compute each factor independently
    # ------------------------------------------------------------------
    rs_df = calculate_relative_strength(engine, scoring_date)
    eps_df = calculate_eps_growth(engine, scoring_date)
    rev_df = calculate_revenue_growth(engine, scoring_date)
    pvh_df = calculate_price_vs_52w_high(engine, scoring_date)

    # ------------------------------------------------------------------
    # Step 2: Merge all factors on ticker
    # ------------------------------------------------------------------
    # Start with RS (the widest factor — all stocks with 6mo price history)
    composite = rs_df[["ticker", "rs_percentile"]].copy()

    # Merge EPS growth
    if not eps_df.empty:
        composite = composite.merge(
            eps_df[["ticker", "eps_growth_capped"]],
            on="ticker",
            how="left",
        )
    else:
        composite["eps_growth_capped"] = np.nan

    # Merge Revenue growth
    if not rev_df.empty:
        composite = composite.merge(
            rev_df[["ticker", "rev_growth_capped"]],
            on="ticker",
            how="left",
        )
    else:
        composite["rev_growth_capped"] = np.nan

    # Merge Price vs 52W High
    composite = composite.merge(
        pvh_df[["ticker", "price_vs_high"]],
        on="ticker",
        how="left",
    )

    # ------------------------------------------------------------------
    # Step 3: Handle missing factors
    # ------------------------------------------------------------------
    # Policy: If a factor is missing (e.g., no fundamental data for a stock),
    # score that factor as 0. This penalizes stocks without data, which is
    # conservative and appropriate — we want stocks where ALL signals confirm.
    #
    # Alternative policy (commented out): redistribute weights among available
    # factors. This is more forgiving but risks promoting stocks with thin data.

    composite["eps_growth_capped"] = composite["eps_growth_capped"].fillna(0.0)
    composite["rev_growth_capped"] = composite["rev_growth_capped"].fillna(0.0)
    composite["price_vs_high"] = composite["price_vs_high"].fillna(0.0)

    # ------------------------------------------------------------------
    # Step 4: Compute composite score
    # ------------------------------------------------------------------
    composite["composite_score"] = (
        0.40 * composite["rs_percentile"]
        + 0.20 * composite["eps_growth_capped"]
        + 0.20 * composite["rev_growth_capped"]
        + 0.20 * composite["price_vs_high"]
    )

    # ------------------------------------------------------------------
    # Step 5: Sort and return
    # ------------------------------------------------------------------
    composite = composite.sort_values("composite_score", ascending=False).reset_index(
        drop=True
    )

    # Add rank for convenience
    composite["rank"] = composite.index + 1

    return composite


def score_summary(composite_df: pd.DataFrame, top_n: int = 20) -> str:
    """Pretty-print the top N stocks by composite score."""
    top = composite_df.head(top_n)
    lines = [
        f"{'Rank':<6}{'Ticker':<8}{'Composite':>10}{'RS%':>8}"
        f"{'EPS_G':>8}{'Rev_G':>8}{'PvH':>8}"
    ]
    lines.append("-" * 56)
    for _, row in top.iterrows():
        lines.append(
            f"{int(row['rank']):<6}{row['ticker']:<8}"
            f"{row['composite_score']:>10.1f}"
            f"{row['rs_percentile']:>8.1f}"
            f"{row['eps_growth_capped']:>8.1f}"
            f"{row['rev_growth_capped']:>8.1f}"
            f"{row['price_vs_high']:>8.1f}"
        )
    return "\n".join(lines)
```

### Example Output

```
Rank  Ticker  Composite     RS%   EPS_G   Rev_G     PvH
--------------------------------------------------------
1     NVDA        91.2    95.3   100.0    88.4    96.2
2     SMCI        88.7    92.1   100.0   100.0    85.3
3     META        85.4    88.6   100.0    72.1    97.8
4     PLTR        82.1    90.2    65.3    40.8    99.5
5     CRWD        79.8    85.4    78.2    33.1    95.6
```

*(Illustrative --- not real scores.)*

---

## 7. Point-in-Time Data Integrity

This section is **critical** for backtesting. Every factor calculation above must respect the information boundary: on any given historical date, you can only use data that was actually available to market participants at that time.

### The Problem

Fundamental data has a reporting lag. A company's Q4 earnings (fiscal quarter ending December 31) may not be filed until mid-February. If your backtest on January 15 uses Q4 EPS data, you are using information that did not exist yet --- this is look-ahead bias.

Similarly, price data can be retroactively adjusted for splits and dividends. You must ensure that backtested price calculations use the adjusted values that would have been computable at the time.

### Sharadar's Point-in-Time Fields

Sharadar provides two date fields on the SF1 (fundamentals) table that are essential:

| Field | Meaning | Use |
|-------|---------|-----|
| `reportperiod` | The fiscal quarter-end date (e.g., 2025-03-31) | Identifies *which* quarter the data describes. |
| `datekey` | The date Sharadar recorded the data as "known" --- typically the SEC filing date or press release date. | **This is your point-in-time filter.** A row with `datekey = 2025-05-02` means this data was not available before May 2, 2025. |

### Rules for Backtesting

1. **Fundamentals (SF1):** Always filter `WHERE datekey <= scoring_date`. Never filter solely on `reportperiod`, which tells you the fiscal period but not when the data became available.

2. **Prices (SEP):** Daily close prices are available at market close on the same day. No additional lag is needed. However, ensure that split adjustments are applied correctly --- Sharadar retroactively adjusts all historical prices when a split occurs, so the `close` field on any given historical date may differ from what it was originally. For backtesting, this is actually correct behavior (you want adjusted prices for return calculations).

3. **Universe membership:** On each historical rebalance date, reconstruct the universe of eligible stocks. A stock that was delisted in March 2024 should not appear in your April 2024 universe. Use the SEP table to verify a stock had an active close price on the scoring date.

### Python: Point-in-Time Aware Backtest Loop

```python
import pandas as pd
from sqlalchemy import create_engine


def backtest_scoring(
    engine,
    rebalance_dates: list[str],
) -> dict[str, pd.DataFrame]:
    """
    Run the composite scoring model on each historical rebalance date,
    respecting point-in-time data availability.

    Parameters
    ----------
    engine : sqlalchemy.Engine
    rebalance_dates : list[str]
        List of YYYY-MM-DD scoring dates (must be trading days).

    Returns
    -------
    dict mapping date -> composite DataFrame
    """
    results = {}

    for scoring_date in rebalance_dates:
        print(f"Scoring {scoring_date}...")

        # Each call to compute_composite_scores uses scoring_date
        # to filter datekey in fundamentals queries, ensuring
        # no look-ahead bias.
        composite = compute_composite_scores(engine, scoring_date)

        # Tag with the scoring date for later analysis
        composite["scoring_date"] = scoring_date
        results[scoring_date] = composite

    return results


def generate_monthly_rebalance_dates(
    engine,
    start_date: str,
    end_date: str,
) -> list[str]:
    """
    Generate the last trading day of each month between start and end.
    These serve as rebalance dates.
    """
    query = """
        SELECT date
        FROM (
            SELECT
                date,
                ROW_NUMBER() OVER (
                    PARTITION BY DATE_TRUNC('month', date)
                    ORDER BY date DESC
                ) AS rn
            FROM (SELECT DISTINCT date FROM sharadar.sep) d
            WHERE date BETWEEN %(start)s AND %(end)s
        ) sub
        WHERE rn = 1
        ORDER BY date
    """
    df = pd.read_sql(query, engine, params={"start": start_date, "end": end_date})
    return df["date"].dt.strftime("%Y-%m-%d").tolist()
```

### Common Look-Ahead Bias Traps

| Trap | How It Manifests | Prevention |
|------|-----------------|------------|
| **Using `reportperiod` instead of `datekey`** | Q4 data (reportperiod = Dec 31) used in January backtest, but it wasn't filed until February. | Always filter `datekey <= scoring_date`. |
| **Survivorship bias in universe** | Only testing stocks that exist today, ignoring delistings. | Reconstruct universe from SEP table on each scoring date. |
| **Future split adjustments** | A stock splits 4:1 in June. Your January backtest uses the post-split adjusted price, which is correct for returns but the *dollar price* looks different than what traders saw. | For return calculations, adjusted prices are correct. For price-level filters (e.g., "> $5"), use `closeunadj` from SEP. |
| **Stale fundamentals** | Using Q3 data in December because Q4 hasn't been filed yet. | The `ROW_NUMBER() ... ORDER BY reportperiod DESC` with `datekey <= scoring_date` automatically selects the most recent *available* quarter. If Q4 isn't filed yet, Q3 is correctly used. |
| **Index reconstitution** | Filtering to "S&P 600 members" using today's membership list. | Maintain historical index membership tables, or avoid index-based filtering entirely (score the full Sharadar universe). |

### Verification Query

To verify your point-in-time logic is correct, run this sanity check:

```sql
-- For a given ticker and scoring date, show which quarters are "known"
SELECT
    ticker,
    reportperiod,
    datekey,
    epsdil,
    revenue
FROM sharadar.sf1
WHERE ticker = 'AAPL'
  AND dimension = 'ARQ'
  AND datekey <= '2025-01-15'   -- What did we know on Jan 15?
ORDER BY reportperiod DESC
LIMIT 8;
```

If the most recent `reportperiod` returned is 2024-09-28 (Q4 FY2024 for Apple, whose fiscal year ends in September), that is correct --- Apple's December quarter wouldn't be filed until late January. If you see a December `reportperiod` with a `datekey` after January 15, your filter is working: that row is excluded.

---

## Appendix: Quick Reference

### Factor Summary Table

| Factor | Weight | Input Table | Key Fields | Lookback | Score Range |
|--------|--------|-------------|------------|----------|-------------|
| RS Percentile | 40% | SEP | `close` | 126 trading days | 0--100 |
| EPS Growth YoY | 20% | SF1 (ARQ) | `epsdil`, `datekey` | 5+ quarters | capped to [-inf, 100] |
| Revenue Growth YoY | 20% | SF1 (ARQ) | `revenue`, `datekey` | 5+ quarters | capped to [0, 100]* |
| Price vs 52W High | 20% | SEP | `close` | 252 trading days | 0--100 |

*Revenue growth is `None` (scored as 0) for pre-revenue companies, so effective floor is 0.

### Required Database Tables

```
sharadar.sep    -- Daily equity prices (split-adjusted)
    ticker      VARCHAR
    date        DATE
    close       NUMERIC    -- split-adjusted close
    closeunadj  NUMERIC    -- unadjusted close (for price-level filters)

sharadar.sf1    -- Quarterly/annual fundamentals
    ticker       VARCHAR
    dimension    VARCHAR    -- 'ARQ' for as-reported quarterly
    reportperiod DATE       -- fiscal quarter end
    datekey      DATE       -- when data became known (point-in-time)
    calendardate DATE       -- calendar quarter end
    epsdil       NUMERIC    -- diluted EPS
    revenue      NUMERIC    -- total revenue
```

### Rebalance Workflow

```
1. Determine scoring_date (last trading day of month)
2. Build universe: all tickers with close price on scoring_date, close > $5
3. Compute Factor 1: RS Percentile (126-day momentum, ranked)
4. Compute Factor 2: EPS Growth YoY (capped at 100)
5. Compute Factor 3: Revenue Growth YoY (capped at 100)
6. Compute Factor 4: Price vs 52-Week High
7. Assemble composite: 0.40*F1 + 0.20*F2 + 0.20*F3 + 0.20*F4
8. Rank by composite score descending
9. Select top N stocks for portfolio
```
