# 01 - Universe Screening: Implementation Guide

## 1. Overview

### Purpose

The universe screener is the first stage of the emerging growth small-cap strategy pipeline. Its job is to reduce the full Sharadar database of ~15,000 US equities down to a tradeable universe of approximately 2,000 stocks that meet institutional-quality standards for market capitalization, liquidity, exchange listing, and minimum price.

### Rationale

Small-cap stocks in the $50M-$10B market cap range represent the sweet spot for emerging growth exposure:

- **Large enough** to have real revenue, audited financials, and analyst coverage, filtering out speculative micro-caps and shell companies.
- **Small enough** that institutional ownership is incomplete, creating pricing inefficiencies that a systematic strategy can exploit.
- **Liquid enough** (minimum $500K average daily dollar volume) that positions can be entered and exited without excessive market impact.
- **Price floor** ($2.00 minimum) excludes penny stocks subject to manipulation, wider bid-ask spreads, and broker restrictions.

### Data Source

Sharadar (via Nasdaq Data Link) provides institutional-grade data covering 15,000+ US equities at $200/month. The three tables relevant to universe screening are:

| Table | Description | Key Fields |
|-------|-------------|------------|
| `SHARADAR/TICKERS` | Ticker metadata | `ticker`, `exchange`, `category`, `isdelisted`, `siccode`, `scalemarketcap` |
| `SHARADAR/SEP` | Daily equity prices | `ticker`, `date`, `close`, `volume`, `closeunadj`, `lastupdated` |
| `SHARADAR/SF1` | Fundamentals (quarterly/annual) | `ticker`, `calendardate`, `marketcap`, `dimension` |

### Technology Stack

- **Database**: PostgreSQL 15+ with TimescaleDB extension (hypertable on SEP for time-series queries)
- **Language**: Python 3.11+ with NumPy, Pandas, and psycopg2/SQLAlchemy
- **Scheduling**: Monthly cron or Airflow DAG for universe refresh

---

## 2. Filter Specifications

### Filter 1: Market Capitalization ($50M - $10B)

#### Threshold and Logic

```
50,000,000 <= market_cap <= 10,000,000,000
```

Both bounds are **inclusive**. Stocks exactly at $50M or $10B are included. This range captures traditional small-cap ($300M-$2B) plus the lower end of mid-cap ($2B-$10B) and the upper end of micro-cap ($50M-$300M) where companies have graduated past the speculative phase.

#### Data Fields

**Primary source**: `SHARADAR/SF1` table, `marketcap` field, `dimension = 'MRQ'` (most recent quarter).

**Secondary source**: `SHARADAR/SEP` table allows computing a real-time market cap as `close * sharesbas` if `sharesbas` is available, or via the `SHARADAR/DAILY` table which has a direct `marketcap` column updated daily.

The SF1 fundamentals-based market cap is updated quarterly on filing dates. For screening purposes where monthly refresh is sufficient, the SF1 market cap is acceptable. For daily monitoring, use the DAILY table or compute from SEP price times shares outstanding.

#### SQL Implementation

```sql
-- Get most recent market cap per ticker from SF1 (quarterly fundamentals)
WITH latest_marketcap AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        calendardate,
        marketcap
    FROM sharadar.sf1
    WHERE dimension = 'MRQ'
      AND marketcap IS NOT NULL
      AND calendardate >= CURRENT_DATE - INTERVAL '6 months'
    ORDER BY ticker, calendardate DESC
)
SELECT ticker, marketcap, calendardate
FROM latest_marketcap
WHERE marketcap BETWEEN 50000000 AND 10000000000;
```

#### Edge Cases and Gotchas

1. **Multiple share classes**: Companies like Alphabet (GOOGL/GOOG) or Berkshire Hathaway (BRK.A/BRK.B) have multiple tickers. Sharadar reports market cap at the *company* level in SF1, so both share classes will show the total enterprise market cap. For screening, this is correct behavior -- you want to include both classes if the company qualifies. However, you must be careful not to double-count the company when computing portfolio weights. Track a `relatedtickers` field from the TICKERS table to group share classes.

2. **Stale market cap data**: If a company has not filed recently (late filer, going through restatement), the most recent SF1 market cap could be 6+ months old. The `calendardate >= CURRENT_DATE - INTERVAL '6 months'` guard prevents using data older than two quarters. Stocks with no recent market cap data are excluded.

3. **Market cap drift**: A stock at $48M market cap on screening day is excluded, but might cross $50M the next day. The monthly refresh cycle handles this naturally. Do not add buffer zones or hysteresis at this stage -- the composite scoring downstream handles borderline cases.

4. **SPACs and blank-check companies**: Pre-merger SPACs often have market caps in this range but hold only cash in trust. These should be filtered out separately (by SIC code or category), not in this market cap filter.

---

### Filter 2: Exchange Listing (NASDAQ / NYSE / NYSE American)

#### Threshold and Logic

```
exchange IN ('NASDAQ', 'NYSE', 'NYSEAMERICAN')
```

Only stocks listed on a qualifying major US exchange pass this filter. This ensures SEC reporting requirements, minimum listing standards, and exchange-level oversight.

#### Data Fields

**Source**: `SHARADAR/TICKERS` table, `exchange` field.

Sharadar uses the following exchange string values:

| Sharadar Value | Exchange | Include? |
|----------------|----------|----------|
| `NASDAQ` | NASDAQ Stock Market (all tiers: Global Select, Global, Capital) | Yes |
| `NYSE` | New York Stock Exchange | Yes |
| `NYSEAMERICAN` | NYSE American (formerly NYSE MKT, formerly AMEX) | Yes |
| `NYSEMKT` | Legacy code for NYSE American (may appear in historical data) | Yes |
| `OTC` | OTC Markets (OTCQX, OTCQB, Pink Sheets) | No |
| `BATS` | BATS/Cboe BZX Exchange | No* |
| (blank/null) | Missing exchange data | No |

*BATS-listed equities are rare and typically ETFs. Exclude unless specifically targeting ETFs.

#### SQL Implementation

```sql
SELECT ticker, exchange, name, category, isdelisted, siccode
FROM sharadar.tickers
WHERE exchange IN ('NASDAQ', 'NYSE', 'NYSEAMERICAN', 'NYSEMKT')
  AND category = 'Domestic'
  AND table_name = 'SEP';
```

#### Edge Cases and Gotchas

1. **NYSE American naming history**: This exchange has been renamed multiple times: AMEX -> NYSE MKT -> NYSE American. Sharadar has mostly standardized to `NYSEAMERICAN`, but older data snapshots may contain `NYSEMKT` or even `AMEX`. Include all variants in your filter.

2. **Foreign ADRs**: ADRs of foreign companies listed on NYSE/NASDAQ will have qualifying exchange codes. The `category = 'Domestic'` filter in the TICKERS table excludes these. If you want to include ADRs (some emerging growth strategies do), remove this filter but add a separate ADR-aware position sizing module since ADRs carry currency risk and different liquidity profiles.

3. **Dual-listed stocks**: Some stocks trade on both a qualifying exchange and OTC. Sharadar typically records the primary listing. The exchange filter on the TICKERS table uses the primary listing, which is correct.

4. **Exchange transfers**: A stock may transfer from NASDAQ to NYSE or vice versa. For point-in-time backtesting, you need the exchange as of the screening date, not the current exchange. Sharadar TICKERS reflects the *current* exchange. For historical accuracy in backtesting, log the exchange at each monthly screening date in your own audit table.

5. **ETFs, ETNs, and CEFs**: The TICKERS table includes ETFs and other fund structures. Filter to `category = 'Domestic'` and optionally check `siccode` to exclude investment companies (SIC codes 6726, 6199). Alternatively, Sharadar's `table_name = 'SEP'` on the TICKERS table restricts to equities tracked in the SEP prices table, which excludes most funds.

---

### Filter 3: Average Daily Dollar Volume (Minimum $500K)

#### Threshold and Logic

```
avg_daily_dollar_volume_20d >= 500,000
```

Computed as the arithmetic mean of daily dollar volume over the trailing 20 trading days, where:

```
daily_dollar_volume = close_price * share_volume
```

Days with zero volume (trading halts, exchange holidays that somehow appear in the data) are **excluded** from the average to avoid artificially deflating the liquidity measure.

The 20-day lookback represents approximately one calendar month of trading days, providing a stable liquidity estimate that smooths out single-day anomalies.

#### Data Fields

**Source**: `SHARADAR/SEP` table, `close` and `volume` fields.

| Field | Description | Notes |
|-------|-------------|-------|
| `close` | Split-adjusted closing price | Use this for dollar volume calculation |
| `volume` | Share volume traded | Already adjusted for splits in SEP |
| `date` | Trading date | Used for the 20-day lookback window |

#### SQL Implementation

```sql
WITH daily_dollar_volume AS (
    SELECT
        ticker,
        date,
        close * volume AS dollar_volume
    FROM sharadar.sep
    WHERE date >= CURRENT_DATE - INTERVAL '35 days'  -- buffer for weekends/holidays
      AND volume > 0                                   -- exclude halted/zero-volume days
),
avg_dollar_volume AS (
    SELECT
        ticker,
        AVG(dollar_volume) AS avg_adv_20d,
        COUNT(*) AS trading_days
    FROM (
        SELECT
            ticker,
            date,
            dollar_volume,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
        FROM daily_dollar_volume
    ) ranked
    WHERE rn <= 20
    GROUP BY ticker
)
SELECT ticker, avg_adv_20d, trading_days
FROM avg_dollar_volume
WHERE avg_adv_20d >= 500000
  AND trading_days >= 15;  -- require at least 15 of 20 days to have data
```

#### Edge Cases and Gotchas

1. **Zero-volume days**: Trading halts, circuit breakers, or data gaps can produce days with `volume = 0`. These must be excluded from the average. The filter `volume > 0` handles this. Additionally, the `trading_days >= 15` guard ensures that a stock with only 5 days of trading data in the window (e.g., a recent IPO or a stock that was halted for 3 weeks) does not pass the filter based on a few high-volume days.

2. **Stock splits**: Sharadar's SEP table provides split-adjusted `close` and `volume` fields. This means a 2-for-1 split is already reflected: the historical prices are halved and historical volumes are doubled. Using the adjusted fields, the dollar volume calculation (`close * volume`) is consistent across splits. Do **not** use `closeunadj` for this calculation.

3. **Recent IPOs**: A stock that IPO'd 10 trading days ago will only have 10 days of data. The `trading_days >= 15` minimum ensures recently listed stocks must survive a few weeks before entering the universe. This is intentional -- IPO-day and first-week volumes are artificially inflated and not representative of ongoing liquidity.

4. **Volume spikes from news/events**: A single day where a stock trades 50x its normal volume (earnings surprise, takeover announcement) can inflate the 20-day average. The strategy's monthly rebalance naturally handles this since the spike will wash out within a month. For more robustness, you could use a **median** instead of mean, but mean is standard for ADV calculations and is what brokers/institutions use.

5. **Close price timing**: Sharadar's `close` is the official closing price, not the last trade price. These can differ slightly for illiquid stocks. For our $500K threshold, this difference is immaterial.

---

### Filter 4: Minimum Share Price ($2.00)

#### Threshold and Logic

```
most_recent_close >= 2.00
```

The most recent closing price must be at or above $2.00. This is a point-in-time check using the latest available trading day.

#### Data Fields

**Source**: `SHARADAR/SEP` table, `close` field (split-adjusted) or `closeunadj` field (unadjusted).

**Which price to use -- adjusted vs. unadjusted**:

Use the **unadjusted** close (`closeunadj`) for this filter. The rationale:

- The $2.00 minimum is a **regulatory and practical constraint**, not an analytical one. Brokers restrict trading in sub-$2 stocks, exchanges issue delisting warnings below $1, and market microstructure degrades at low price levels.
- Split-adjusted prices can show historical prices below $2.00 that were actually above $2.00 at the time (pre-split). For the *current* screening date, adjusted and unadjusted close are identical (adjustments only change historical values). So for the current-day filter, it does not matter.
- For **backtesting** (historical screening dates), you **must** use `closeunadj` to get the actual price that was trading on that date. A stock at $3.00 pre-split that later did a 2:1 split would show as $1.50 adjusted -- incorrectly failing the $2.00 filter in a historical backtest.

#### SQL Implementation

```sql
WITH latest_price AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        date,
        closeunadj,
        close
    FROM sharadar.sep
    WHERE date >= CURRENT_DATE - INTERVAL '7 days'  -- recent data only
    ORDER BY ticker, date DESC
)
SELECT ticker, date, closeunadj, close
FROM latest_price
WHERE closeunadj >= 2.00;
```

#### Edge Cases and Gotchas

1. **Reverse splits**: A stock trading at $0.80 does a 1-for-5 reverse split to reach $4.00. The `closeunadj` will correctly show the post-split price of $4.00 on dates after the reverse split. The stock passes the filter. This is correct behavior -- the stock is now genuinely trading at $4.00.

2. **Penny stock bounce**: A stock drops to $1.50, gets excluded from the universe, then recovers to $2.50 next month. It re-enters the universe at the next monthly screen. This churn is acceptable and expected. The composite scoring downstream will assign it a low conviction score initially.

3. **Intraday price drops**: A stock closes at $2.10 on screening day but traded as low as $1.80 intraday. The close-based filter includes it. This is standard practice -- close prices are the reference for screening.

4. **Currency**: All Sharadar US equity prices are in USD. No currency conversion needed.

---

## 3. Handling Delistings and Survivorship Bias

### Why This Matters

Survivorship bias is the single largest source of overstated backtest returns in equity strategies. If your backtest universe only includes stocks that survived to the present day, you systematically exclude the losers (bankruptcies, failed companies) and include the winners (companies that grew from small-cap to large-cap). This can inflate annualized returns by 1-3% per year.

### Sharadar's Delisted Securities Coverage

Sharadar includes delisted securities in all tables. The TICKERS table has an `isdelisted` field:

| `isdelisted` | Meaning |
|--------------|---------|
| `N` | Currently active and trading |
| `Y` | Delisted (includes bankruptcies, mergers, acquisitions, exchange transfers to non-qualifying venues) |

The SEP table retains the full price history for delisted securities up to their final trading date. This is critical for survivorship-bias-free backtesting.

### Point-in-Time Universe Construction

For backtesting, the universe must be constructed using only information available on the screening date. The procedure for each monthly rebalance date `T`:

```sql
-- Point-in-time universe construction for backtest date T
-- Step 1: Find tickers that were actively trading on date T
-- (had at least one price record in the 7 days up to and including T)

WITH active_on_date AS (
    SELECT DISTINCT ticker
    FROM sharadar.sep
    WHERE date BETWEEN :rebalance_date - INTERVAL '7 days' AND :rebalance_date
),

-- Step 2: Get exchange info as of date T
-- Note: Sharadar TICKERS only has current exchange. For true point-in-time,
-- maintain your own exchange history table (see note below)
ticker_info AS (
    SELECT ticker, exchange, category, isdelisted
    FROM sharadar.tickers
    WHERE table_name = 'SEP'
),

-- Step 3: Get most recent market cap as of date T
-- Use SF1 filings with calendardate <= T
latest_mcap AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        marketcap,
        calendardate
    FROM sharadar.sf1
    WHERE dimension = 'MRQ'
      AND calendardate <= :rebalance_date
      AND calendardate >= :rebalance_date - INTERVAL '6 months'
      AND marketcap IS NOT NULL
    ORDER BY ticker, calendardate DESC
),

-- Step 4: Get price and volume as of date T
latest_price AS (
    SELECT DISTINCT ON (ticker)
        ticker,
        date,
        closeunadj,
        close
    FROM sharadar.sep
    WHERE date <= :rebalance_date
    ORDER BY ticker, date DESC
),

-- Step 5: Compute 20-day average dollar volume as of date T
adv_20d AS (
    SELECT
        ticker,
        AVG(close * volume) AS avg_dollar_volume,
        COUNT(*) AS trading_days
    FROM (
        SELECT
            ticker, date, close, volume,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
        FROM sharadar.sep
        WHERE date <= :rebalance_date
          AND volume > 0
    ) sub
    WHERE rn <= 20
    GROUP BY ticker
    HAVING COUNT(*) >= 15
)

-- Final: Combine all filters
SELECT
    a.ticker,
    m.marketcap,
    t.exchange,
    p.closeunadj AS last_price,
    v.avg_dollar_volume,
    v.trading_days
FROM active_on_date a
JOIN ticker_info t ON a.ticker = t.ticker
JOIN latest_mcap m ON a.ticker = m.ticker
JOIN latest_price p ON a.ticker = p.ticker
JOIN adv_20d v ON a.ticker = v.ticker
WHERE t.exchange IN ('NASDAQ', 'NYSE', 'NYSEAMERICAN', 'NYSEMKT')
  AND t.category = 'Domestic'
  AND m.marketcap BETWEEN 50000000 AND 10000000000
  AND p.closeunadj >= 2.00
  AND v.avg_dollar_volume >= 500000
ORDER BY m.marketcap DESC;
```

### Treatment of Corporate Events

| Event | Treatment | Implementation |
|-------|-----------|----------------|
| **Bankruptcy/Chapter 11** | Stock remains in universe until delisted or price drops below $2.00. Final price in SEP is the last traded price. | Normal filter application handles this. |
| **Acquisition (cash)** | Stock trades until deal closes, then delisted. Final SEP price reflects tender offer price. | Stock exits universe at next monthly screen after delisting. For returns, use the final trading price. |
| **Acquisition (stock-for-stock)** | Target delisted, replaced by acquirer shares. | Use final SEP price as exit. If acquirer is in universe, it continues normally. |
| **Merger of equals** | Both tickers may delist, new ticker created. | Both exit universe; new ticker enters at next screen if it meets filters. |
| **Spinoff** | Parent remains; new child ticker created. | Child enters universe at next monthly screen if it meets all filters. No special handling needed. |
| **Exchange transfer** | Ticker moves from NASDAQ to OTC (or vice versa). | If it moves to a non-qualifying exchange, it exits universe at next screen. Sharadar TICKERS reflects current exchange. |

### Exchange History Table

Since Sharadar TICKERS only shows the *current* exchange, you need to maintain a historical snapshot for backtesting:

```sql
CREATE TABLE IF NOT EXISTS universe_audit.exchange_history (
    ticker       TEXT NOT NULL,
    exchange     TEXT NOT NULL,
    snapshot_date DATE NOT NULL,
    PRIMARY KEY (ticker, snapshot_date)
);

-- Populate monthly: run on each rebalance date
INSERT INTO universe_audit.exchange_history (ticker, exchange, snapshot_date)
SELECT ticker, exchange, CURRENT_DATE
FROM sharadar.tickers
WHERE table_name = 'SEP'
ON CONFLICT (ticker, snapshot_date) DO NOTHING;
```

For backtesting, join on this table instead of the live TICKERS table when determining exchange eligibility at historical dates.

---

## 4. Implementation

### Complete SQL: Universe Screening Query

The query below chains all four filters for a current-date (live) screen. For backtesting, substitute `CURRENT_DATE` with the rebalance date parameter and use the point-in-time query from Section 3.

```sql
-- ============================================================
-- Universe Screener: Emerging Growth Small-Cap Strategy
-- Filters: Market Cap, Exchange, ADV, Min Price
-- Expected output: ~2,000 tickers
-- ============================================================

WITH latest_marketcap AS (
    -- Most recent quarterly market cap per ticker
    SELECT DISTINCT ON (ticker)
        ticker,
        marketcap,
        calendardate AS mcap_date
    FROM sharadar.sf1
    WHERE dimension = 'MRQ'
      AND marketcap IS NOT NULL
      AND calendardate >= CURRENT_DATE - INTERVAL '6 months'
    ORDER BY ticker, calendardate DESC
),

exchange_filter AS (
    -- Qualifying domestic equities on major exchanges
    SELECT ticker, exchange, name, sector, industry, siccode, isdelisted
    FROM sharadar.tickers
    WHERE exchange IN ('NASDAQ', 'NYSE', 'NYSEAMERICAN', 'NYSEMKT')
      AND category = 'Domestic'
      AND table_name = 'SEP'
      AND isdelisted = 'N'
),

latest_price AS (
    -- Most recent closing price per ticker
    SELECT DISTINCT ON (ticker)
        ticker,
        date AS price_date,
        close,
        closeunadj
    FROM sharadar.sep
    WHERE date >= CURRENT_DATE - INTERVAL '7 days'
    ORDER BY ticker, date DESC
),

adv_calc AS (
    -- 20-day average daily dollar volume
    SELECT
        ticker,
        AVG(dollar_volume) AS avg_adv_20d,
        COUNT(*) AS trading_days_in_window
    FROM (
        SELECT
            ticker,
            date,
            close * volume AS dollar_volume,
            ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY date DESC) AS rn
        FROM sharadar.sep
        WHERE date >= CURRENT_DATE - INTERVAL '35 days'
          AND volume > 0
    ) ranked
    WHERE rn <= 20
    GROUP BY ticker
    HAVING COUNT(*) >= 15
)

SELECT
    e.ticker,
    e.name,
    e.exchange,
    e.sector,
    e.industry,
    m.marketcap,
    m.mcap_date,
    p.closeunadj AS last_price,
    p.price_date,
    a.avg_adv_20d,
    a.trading_days_in_window
FROM exchange_filter e
INNER JOIN latest_marketcap m ON e.ticker = m.ticker
INNER JOIN latest_price p ON e.ticker = p.ticker
INNER JOIN adv_calc a ON e.ticker = a.ticker
WHERE m.marketcap BETWEEN 50000000 AND 10000000000     -- Filter 1: Market Cap
  AND p.closeunadj >= 2.00                              -- Filter 4: Min Price
  AND a.avg_adv_20d >= 500000                           -- Filter 3: Min ADV
ORDER BY m.marketcap DESC;
```

### Python Implementation

```python
"""
universe_screener.py

Universe screening module for the Emerging Growth Small-Cap Strategy.
Applies four filters (market cap, exchange, ADV, min price) to produce
a tradeable universe of ~2,000 stocks.
"""

import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScreeningParams:
    """Configuration for universe screening filters."""
    min_market_cap: float = 50_000_000          # $50M
    max_market_cap: float = 10_000_000_000      # $10B
    qualifying_exchanges: tuple = ('NASDAQ', 'NYSE', 'NYSEAMERICAN', 'NYSEMKT')
    min_avg_dollar_volume: float = 500_000      # $500K
    min_share_price: float = 2.00               # $2.00
    adv_lookback_days: int = 20                 # trading days
    min_trading_days: int = 15                  # minimum data points for ADV
    max_mcap_staleness_months: int = 6          # reject market cap older than this
    price_staleness_days: int = 7               # reject price data older than this


class UniverseScreener:
    """
    Screens the Sharadar equity universe to produce a tradeable universe
    of emerging growth small-cap stocks.
    """

    def __init__(self, db_url: str, params: Optional[ScreeningParams] = None):
        """
        Args:
            db_url: PostgreSQL connection string.
            params: Screening parameters. Uses defaults if not provided.
        """
        self.engine = create_engine(db_url)
        self.params = params or ScreeningParams()

    def screen(self, as_of_date: Optional[date] = None) -> pd.DataFrame:
        """
        Run the full universe screen.

        Args:
            as_of_date: Date to screen as of. Defaults to today.
                        For backtesting, pass historical dates.

        Returns:
            DataFrame with columns: ticker, name, exchange, sector, industry,
            marketcap, last_price, avg_adv_20d, price_date, mcap_date
        """
        if as_of_date is None:
            as_of_date = date.today()

        logger.info(f"Running universe screen as of {as_of_date}")

        # Step 1: Get exchange-qualified tickers
        tickers = self._get_exchange_tickers(as_of_date)
        logger.info(f"Exchange filter: {len(tickers)} tickers")

        # Step 2: Get market cap data and apply filter
        mcap = self._get_market_caps(as_of_date)
        logger.info(f"Market cap filter: {len(mcap)} tickers in range")

        # Step 3: Get latest prices and apply min price filter
        prices = self._get_latest_prices(as_of_date)
        logger.info(f"Price filter: {len(prices)} tickers >= ${self.params.min_share_price}")

        # Step 4: Compute ADV and apply liquidity filter
        adv = self._get_average_dollar_volume(as_of_date)
        logger.info(f"ADV filter: {len(adv)} tickers >= ${self.params.min_avg_dollar_volume:,.0f}")

        # Step 5: Inner join all filters
        universe = (
            tickers
            .merge(mcap, on='ticker', how='inner')
            .merge(prices, on='ticker', how='inner')
            .merge(adv, on='ticker', how='inner')
        )

        logger.info(f"Final universe: {len(universe)} tickers")
        self._validate_universe_count(universe)

        return universe.sort_values('marketcap', ascending=False).reset_index(drop=True)

    def _get_exchange_tickers(self, as_of_date: date) -> pd.DataFrame:
        """Filter 2: Qualifying exchange listings."""
        query = text("""
            SELECT ticker, name, exchange, sector, industry, siccode
            FROM sharadar.tickers
            WHERE exchange IN :exchanges
              AND category = 'Domestic'
              AND table_name = 'SEP'
              AND (isdelisted = 'N' OR :include_delisted = TRUE)
        """)
        # For backtesting (as_of_date in the past), include delisted stocks
        include_delisted = as_of_date < date.today()

        with self.engine.connect() as conn:
            df = pd.read_sql(
                query, conn,
                params={
                    'exchanges': self.params.qualifying_exchanges,
                    'include_delisted': include_delisted,
                }
            )
        return df

    def _get_market_caps(self, as_of_date: date) -> pd.DataFrame:
        """Filter 1: Market cap between $50M and $10B."""
        staleness_cutoff = as_of_date - timedelta(
            days=self.params.max_mcap_staleness_months * 30
        )
        query = text("""
            SELECT DISTINCT ON (ticker)
                ticker,
                marketcap,
                calendardate AS mcap_date
            FROM sharadar.sf1
            WHERE dimension = 'MRQ'
              AND marketcap IS NOT NULL
              AND calendardate <= :as_of_date
              AND calendardate >= :staleness_cutoff
              AND marketcap BETWEEN :min_mcap AND :max_mcap
            ORDER BY ticker, calendardate DESC
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(
                query, conn,
                params={
                    'as_of_date': as_of_date,
                    'staleness_cutoff': staleness_cutoff,
                    'min_mcap': self.params.min_market_cap,
                    'max_mcap': self.params.max_market_cap,
                }
            )
        return df

    def _get_latest_prices(self, as_of_date: date) -> pd.DataFrame:
        """Filter 4: Minimum share price."""
        price_cutoff = as_of_date - timedelta(days=self.params.price_staleness_days)
        query = text("""
            SELECT DISTINCT ON (ticker)
                ticker,
                date AS price_date,
                closeunadj AS last_price,
                close AS last_price_adj
            FROM sharadar.sep
            WHERE date <= :as_of_date
              AND date >= :price_cutoff
              AND closeunadj >= :min_price
            ORDER BY ticker, date DESC
        """)
        with self.engine.connect() as conn:
            df = pd.read_sql(
                query, conn,
                params={
                    'as_of_date': as_of_date,
                    'price_cutoff': price_cutoff,
                    'min_price': self.params.min_share_price,
                }
            )
        return df

    def _get_average_dollar_volume(self, as_of_date: date) -> pd.DataFrame:
        """Filter 3: Minimum 20-day average daily dollar volume."""
        # Fetch ~35 calendar days of data to cover 20 trading days
        lookback_start = as_of_date - timedelta(days=35)
        query = text("""
            SELECT ticker, date, close, volume
            FROM sharadar.sep
            WHERE date BETWEEN :start_date AND :as_of_date
              AND volume > 0
        """)
        with self.engine.connect() as conn:
            raw = pd.read_sql(
                query, conn,
                params={
                    'start_date': lookback_start,
                    'as_of_date': as_of_date,
                }
            )

        if raw.empty:
            return pd.DataFrame(columns=['ticker', 'avg_adv_20d', 'trading_days'])

        # Compute dollar volume
        raw['dollar_volume'] = raw['close'] * raw['volume']

        # Keep only the most recent 20 trading days per ticker
        raw = raw.sort_values(['ticker', 'date'], ascending=[True, False])
        raw['rank'] = raw.groupby('ticker').cumcount() + 1
        raw = raw[raw['rank'] <= self.params.adv_lookback_days]

        # Aggregate
        adv = (
            raw.groupby('ticker')
            .agg(
                avg_adv_20d=('dollar_volume', 'mean'),
                trading_days=('dollar_volume', 'count'),
            )
            .reset_index()
        )

        # Apply filters
        adv = adv[
            (adv['avg_adv_20d'] >= self.params.min_avg_dollar_volume)
            & (adv['trading_days'] >= self.params.min_trading_days)
        ]

        return adv[['ticker', 'avg_adv_20d', 'trading_days']]

    def _validate_universe_count(self, universe: pd.DataFrame) -> None:
        """
        Sanity check: the universe should contain roughly 1,500-2,500 stocks.
        Log a warning if outside this range.
        """
        count = len(universe)
        if count < 1000:
            logger.warning(
                f"Universe has only {count} stocks (expected ~2000). "
                "Check data freshness and filter thresholds."
            )
        elif count > 3500:
            logger.warning(
                f"Universe has {count} stocks (expected ~2000). "
                "Filters may be too loose or data may include non-equities."
            )
        else:
            logger.info(f"Universe count {count} is within expected range.")


# --------------------------------------------------------------------------
# Convenience entry point
# --------------------------------------------------------------------------

def build_universe(
    db_url: str,
    as_of_date: Optional[date] = None,
    params: Optional[ScreeningParams] = None,
) -> pd.DataFrame:
    """
    Build the investable universe for a given date.

    Args:
        db_url: PostgreSQL connection string.
        as_of_date: Screen as of this date (default: today).
        params: Override default screening parameters.

    Returns:
        DataFrame of ~2,000 qualifying tickers with metadata.
    """
    screener = UniverseScreener(db_url, params)
    return screener.screen(as_of_date)
```

### Expected Output and Validation

The screen should produce approximately **1,800-2,200 stocks**. Here is how to sanity-check each filter's reduction:

| Stage | Approximate Count | Rationale |
|-------|-------------------|-----------|
| Full Sharadar SEP universe | ~15,000 | All equities with price data |
| After exchange filter | ~7,000 | Removes OTC, foreign, non-equity |
| After market cap filter | ~3,000 | Removes mega/large-cap and nano-cap |
| After ADV filter | ~2,200 | Removes illiquid small-caps |
| After min price filter | ~2,000 | Removes sub-$2 stocks |

If your count deviates significantly from these checkpoints, investigate:

```python
def diagnose_filter_cascade(db_url: str, as_of_date: date = None):
    """Run each filter independently and report reduction at each stage."""
    screener = UniverseScreener(db_url)
    as_of_date = as_of_date or date.today()

    tickers = screener._get_exchange_tickers(as_of_date)
    mcap = screener._get_market_caps(as_of_date)
    prices = screener._get_latest_prices(as_of_date)
    adv = screener._get_average_dollar_volume(as_of_date)

    all_tickers = set(tickers['ticker'])
    mcap_tickers = set(mcap['ticker'])
    price_tickers = set(prices['ticker'])
    adv_tickers = set(adv['ticker'])

    print(f"Exchange-qualified tickers:  {len(all_tickers):>6,}")
    print(f"  + Market cap filter:       {len(all_tickers & mcap_tickers):>6,}")
    print(f"  + ADV filter:              {len(all_tickers & mcap_tickers & adv_tickers):>6,}")
    print(f"  + Min price filter:        {len(all_tickers & mcap_tickers & adv_tickers & price_tickers):>6,}")
```

### Monthly Refresh Process

The universe should be refreshed **monthly**, on the first trading day of each month (or the rebalance date defined by the strategy). The process:

1. **Run the screen** with `as_of_date` set to the rebalance date.
2. **Diff against the previous universe** to identify additions and removals.
3. **Log additions/removals** to an audit table for turnover analysis.
4. **Publish the new universe** to the downstream pipeline (signal generation, portfolio construction).

```python
def refresh_universe(db_url: str, as_of_date: date) -> dict:
    """
    Monthly universe refresh with audit logging.

    Returns dict with 'universe', 'additions', 'removals' DataFrames.
    """
    engine = create_engine(db_url)

    # Build new universe
    new_universe = build_universe(db_url, as_of_date)
    new_tickers = set(new_universe['ticker'])

    # Load previous universe
    with engine.connect() as conn:
        prev = pd.read_sql(text("""
            SELECT ticker FROM universe_audit.monthly_universe
            WHERE rebalance_date = (
                SELECT MAX(rebalance_date) FROM universe_audit.monthly_universe
                WHERE rebalance_date < :as_of_date
            )
        """), conn, params={'as_of_date': as_of_date})

    prev_tickers = set(prev['ticker']) if not prev.empty else set()

    additions = new_tickers - prev_tickers
    removals = prev_tickers - new_tickers

    logger.info(
        f"Universe refresh: {len(new_tickers)} total, "
        f"+{len(additions)} additions, -{len(removals)} removals, "
        f"{len(additions) + len(removals)} turnover"
    )

    # Persist to audit table
    records = [
        {'ticker': t, 'rebalance_date': as_of_date} for t in new_tickers
    ]
    audit_df = pd.DataFrame(records)

    with engine.connect() as conn:
        audit_df.to_sql(
            'monthly_universe',
            conn,
            schema='universe_audit',
            if_exists='append',
            index=False,
        )

    return {
        'universe': new_universe,
        'additions': new_universe[new_universe['ticker'].isin(additions)],
        'removals': prev[prev['ticker'].isin(removals)] if not prev.empty else pd.DataFrame(),
    }
```

---

## 5. Data Quality Checks

### Missing Data Handling

| Scenario | Detection | Resolution |
|----------|-----------|------------|
| Ticker in TICKERS but not in SEP | LEFT JOIN produces NULL price/volume | Exclude from universe (no price data = not tradeable) |
| Ticker in SEP but not in SF1 | LEFT JOIN produces NULL market cap | Exclude from universe (cannot verify market cap filter) |
| SEP price data gaps (missing dates) | Compare trading day count against exchange calendar | If < 15 of 20 expected days, exclude from ADV calc |
| Market cap = 0 or negative | `WHERE marketcap > 0` guard | Exclude; likely data error |
| Volume = 0 on non-holiday | `WHERE volume > 0` in ADV calculation | Exclude that day from ADV (possible halt) |

```python
def check_data_quality(db_url: str, as_of_date: date) -> dict:
    """
    Run data quality checks and return a report.

    Returns dict with counts of each issue found.
    """
    engine = create_engine(db_url)
    issues = {}

    with engine.connect() as conn:
        # Check 1: Tickers with no recent price data
        result = conn.execute(text("""
            SELECT COUNT(*) FROM sharadar.tickers t
            WHERE t.table_name = 'SEP'
              AND t.isdelisted = 'N'
              AND NOT EXISTS (
                  SELECT 1 FROM sharadar.sep s
                  WHERE s.ticker = t.ticker
                    AND s.date >= :cutoff
              )
        """), {'cutoff': as_of_date - timedelta(days=7)})
        issues['active_tickers_no_recent_price'] = result.scalar()

        # Check 2: Tickers with no market cap in SF1
        result = conn.execute(text("""
            SELECT COUNT(*) FROM sharadar.tickers t
            WHERE t.table_name = 'SEP'
              AND t.isdelisted = 'N'
              AND NOT EXISTS (
                  SELECT 1 FROM sharadar.sf1 f
                  WHERE f.ticker = t.ticker
                    AND f.dimension = 'MRQ'
                    AND f.calendardate >= :cutoff
              )
        """), {'cutoff': as_of_date - timedelta(days=180)})
        issues['active_tickers_no_recent_marketcap'] = result.scalar()

        # Check 3: Stale SEP data (last update > 3 days ago on a weekday)
        result = conn.execute(text("""
            SELECT MAX(date) FROM sharadar.sep
        """))
        latest_sep_date = result.scalar()
        issues['sep_latest_date'] = str(latest_sep_date)
        if latest_sep_date and (as_of_date - latest_sep_date).days > 3:
            issues['sep_data_stale'] = True
        else:
            issues['sep_data_stale'] = False

        # Check 4: Negative or zero market caps
        result = conn.execute(text("""
            SELECT COUNT(DISTINCT ticker) FROM sharadar.sf1
            WHERE dimension = 'MRQ'
              AND calendardate >= :cutoff
              AND (marketcap <= 0 OR marketcap IS NULL)
        """), {'cutoff': as_of_date - timedelta(days=180)})
        issues['tickers_invalid_marketcap'] = result.scalar()

        # Check 5: Extreme prices (likely data errors)
        result = conn.execute(text("""
            SELECT COUNT(*) FROM sharadar.sep
            WHERE date >= :cutoff
              AND (close <= 0 OR close > 100000 OR volume < 0)
        """), {'cutoff': as_of_date - timedelta(days=7)})
        issues['suspicious_price_records'] = result.scalar()

    return issues
```

### Stale Price Detection

A stock's price data is considered stale if the most recent record in SEP is more than 3 trading days behind the current date. Causes include:

- Sharadar data pipeline delay (typically data arrives by 7pm ET for same-day close)
- Stock halted by exchange (SEC investigation, pending news)
- Ticker removed from Sharadar feed but not yet marked as delisted

Stale-priced stocks should be flagged but not necessarily excluded -- a stock halted for 2 days may resume trading. The `price_staleness_days = 7` parameter in `ScreeningParams` controls this threshold.

### Corporate Action Adjustments

Sharadar's SEP table provides split-adjusted data. However, be aware of:

1. **Adjustment lag**: When a split occurs, Sharadar retroactively adjusts all historical prices. If you snapshot daily data into your own tables, you need to re-pull the full history after a split or use the `lastupdated` field to detect changed records.

2. **Dividend adjustments**: SEP `close` is split-adjusted but **not** dividend-adjusted. For screening purposes (market cap, price floor, ADV), this is correct. For return calculations downstream, you may need total-return-adjusted prices.

3. **Special dividends**: Large special dividends (e.g., a $5 special dividend on a $20 stock) cause a price drop that is not reflected in the split-adjustment factor. The price filter may temporarily exclude a stock that dropped from $3.00 to $1.50 due to a special dividend. This is acceptable -- the stock genuinely trades below $2.00 post-dividend.

### Outlier Detection

Flag but do not automatically exclude the following:

```python
def detect_outliers(universe: pd.DataFrame) -> pd.DataFrame:
    """
    Flag potential outliers in the screened universe for manual review.

    Adds boolean columns: is_outlier_mcap, is_outlier_adv, is_outlier_price.
    """
    df = universe.copy()

    # Market cap outliers: more than 3 std devs from log-mean
    log_mcap = np.log10(df['marketcap'])
    mcap_z = (log_mcap - log_mcap.mean()) / log_mcap.std()
    df['is_outlier_mcap'] = mcap_z.abs() > 3.0

    # ADV outliers: top 0.5% (suspiciously high for a small-cap)
    adv_threshold = df['avg_adv_20d'].quantile(0.995)
    df['is_outlier_adv'] = df['avg_adv_20d'] > adv_threshold

    # Price outliers: above $500 for a small-cap is unusual
    df['is_outlier_price'] = df['last_price'] > 500.0

    outlier_count = (
        df['is_outlier_mcap'] | df['is_outlier_adv'] | df['is_outlier_price']
    ).sum()

    logger.info(f"Flagged {outlier_count} potential outliers for review")

    return df
```

Outliers flagged for review:
- **Market cap outliers**: Stocks near the $50M or $10B boundaries with volatile market caps that may flip in/out of the universe monthly.
- **ADV outliers**: Small-cap stocks with unusually high dollar volume may be undergoing a short squeeze, meme-stock event, or takeover battle. Their liquidity profile is not representative.
- **Price outliers**: Small-cap stocks with share prices above $500 are rare and may indicate a company that has never split (e.g., NVR Inc. historically). These are valid universe members but worth flagging.

---

## Appendix: Database Schema Setup

For teams setting up the PostgreSQL/TimescaleDB database from scratch:

```sql
-- Create schema for Sharadar data
CREATE SCHEMA IF NOT EXISTS sharadar;

-- SEP table (daily equity prices) as a TimescaleDB hypertable
CREATE TABLE IF NOT EXISTS sharadar.sep (
    ticker       TEXT NOT NULL,
    date         DATE NOT NULL,
    open         DOUBLE PRECISION,
    high         DOUBLE PRECISION,
    low          DOUBLE PRECISION,
    close        DOUBLE PRECISION,
    volume       BIGINT,
    closeadj     DOUBLE PRECISION,
    closeunadj   DOUBLE PRECISION,
    lastupdated  DATE,
    PRIMARY KEY (ticker, date)
);

SELECT create_hypertable('sharadar.sep', 'date',
    if_not_exists => TRUE,
    migrate_data => TRUE
);

CREATE INDEX IF NOT EXISTS idx_sep_ticker_date ON sharadar.sep (ticker, date DESC);

-- SF1 table (fundamentals)
CREATE TABLE IF NOT EXISTS sharadar.sf1 (
    ticker          TEXT NOT NULL,
    dimension       TEXT NOT NULL,
    calendardate    DATE NOT NULL,
    datekey         DATE,
    reportperiod    DATE,
    lastupdated     DATE,
    marketcap       DOUBLE PRECISION,
    -- ... additional fundamental fields as needed
    PRIMARY KEY (ticker, dimension, calendardate)
);

CREATE INDEX IF NOT EXISTS idx_sf1_mcap
    ON sharadar.sf1 (ticker, calendardate DESC)
    WHERE dimension = 'MRQ' AND marketcap IS NOT NULL;

-- TICKERS table (metadata)
CREATE TABLE IF NOT EXISTS sharadar.tickers (
    ticker          TEXT NOT NULL,
    table_name      TEXT,
    name            TEXT,
    exchange        TEXT,
    category        TEXT,
    isdelisted      TEXT,
    sector          TEXT,
    industry        TEXT,
    siccode         TEXT,
    scalemarketcap  TEXT,
    relatedtickers  TEXT,
    PRIMARY KEY (ticker, table_name)
);

-- Audit schema for universe history
CREATE SCHEMA IF NOT EXISTS universe_audit;

CREATE TABLE IF NOT EXISTS universe_audit.monthly_universe (
    ticker          TEXT NOT NULL,
    rebalance_date  DATE NOT NULL,
    PRIMARY KEY (ticker, rebalance_date)
);

CREATE TABLE IF NOT EXISTS universe_audit.exchange_history (
    ticker          TEXT NOT NULL,
    exchange        TEXT NOT NULL,
    snapshot_date   DATE NOT NULL,
    PRIMARY KEY (ticker, snapshot_date)
);
```
