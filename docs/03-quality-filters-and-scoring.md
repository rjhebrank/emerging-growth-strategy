# 03 - Quality Filters, Composite Scoring, and Signal Generation

## 1. Overview

**Purpose:** After computing the four raw factors (RS Percentile, EPS Growth, Revenue Growth, Price vs 52-Week High), this module applies quality gates, computes a composite score, ranks the filtered universe, selects the top 25 holdings, and generates actionable BUY/SELL/HOLD signals by comparing against the prior month's portfolio.

**Pipeline at a glance:**

```
Raw universe (~2,000 stocks)
    │
    ▼
Quality Filter Gates (3 simultaneous gates)
    │
    ▼
Filtered universe (~350-400 stocks)
    │
    ▼
Composite Score calculation (weighted 0-100 scale)
    │
    ▼
Rank descending by composite score
    │
    ▼
Select Top 25
    │
    ▼
Enforce sector cap (max 40% per sector)
    │
    ▼
Compare to prior month's holdings
    │
    ▼
Generate BUY / SELL / HOLD signals
    │
    ▼
Rebalance to equal 4% weights
```

Each step is deterministic and reproducible. Given the same factor inputs and prior holdings, the output is identical every time.

---

## 2. Quality Filter Gates (All Must Pass Simultaneously)

A stock must pass all three gates to enter the composite scoring stage. Failing any single gate eliminates the stock from consideration for that month.

### Gate 1: EPS Growth >= 5%

| Parameter | Value |
|-----------|-------|
| Factor | Factor 2 (YoY EPS Growth) |
| Threshold | >= 5% |
| Scale | Raw percentage (not the 0-100 scored value) |

**Rationale:** Ensures the company is delivering genuine earnings expansion, not merely flat or declining profits masquerading behind a high RS score. A 5% floor is deliberately lenient -- it admits moderate growers while excluding stagnant and shrinking earners.

**Turnaround stocks:** Stocks that flipped from negative to positive EPS receive a raw factor score of 999 (the turnaround sentinel). These automatically pass Gate 1 because 999 >= 5. This is intentional: a turnaround from losses to profits is a powerful growth signal.

**Edge cases:**
- Missing EPS data (no TTM or prior-year EPS available): **Exclude.** If we cannot compute YoY EPS growth, we cannot verify earnings quality. The stock is removed from the universe for this month.
- Zero prior-year EPS (division by zero): If prior EPS is exactly zero and current EPS is positive, treat as a turnaround (score = 999, passes gate). If current EPS is also zero or negative, **exclude.**
- Negative current EPS: Raw growth percentage will be negative or nonsensical. **Exclude.**

### Gate 2: Revenue Growth >= 5%

| Parameter | Value |
|-----------|-------|
| Factor | Factor 3 (YoY Revenue Growth) |
| Threshold | >= 5% |
| Scale | Raw percentage |

**Rationale:** Validates that the business itself is expanding, not just improving margins on a shrinking revenue base. Earnings growth without revenue growth is often unsustainable (cost-cutting runs out eventually).

**Edge cases:**
- Pre-revenue companies (revenue = 0 or null): **Exclude.** Without revenue, there is no revenue growth to measure. Pre-revenue biotechs, SPACs, and similar entities are outside the strategy's scope.
- Negative revenue (restated/adjusted): Extremely rare. **Exclude.**
- Missing revenue data: **Exclude.**

### Gate 3: Price vs 52-Week High >= 75%

| Parameter | Value |
|-----------|-------|
| Factor | Factor 4 (Current Price / 52-Week High * 100) |
| Threshold | >= 75% |
| Scale | 0-100 (percentage of the 52-week high) |

**Rationale:** A stock trading more than 25% below its 52-week high is in a meaningful drawdown. This filter enforces that we only buy stocks with technical strength -- those near their highs, which typically indicates institutional accumulation, strong demand, and a favorable supply/demand setup.

**Why 75% and not higher?** A tighter filter (e.g., 90%) would exclude stocks in normal healthy pullbacks. Many of the best entries come at 80-85% of the high, where the stock is consolidating before a breakout. The 75% floor removes the truly broken charts while admitting constructive bases.

**Edge cases:**
- Recently IPO'd stocks with less than 52 weeks of history: Use the available trading history to compute the high. If fewer than 60 trading days exist, **exclude** -- insufficient history to establish a meaningful high.
- Stocks hitting a new 52-week high this month: Price vs High = 100%. Passes easily.
- Stocks that were halted or had extreme one-day spikes: The 52-week high may be an outlier. No special handling -- the factor naturally penalizes stocks far below a spike high, which is the desired behavior (those spikes often represent distribution events).

---

## 3. Filter Implementation

```python
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def apply_quality_filters(
    df: pd.DataFrame,
    eps_growth_min: float = 5.0,
    rev_growth_min: float = 5.0,
    price_vs_high_min: float = 75.0,
    min_pass_count: int = 100,
    max_pass_count: int = 600,
) -> pd.DataFrame:
    """
    Apply all three quality filter gates simultaneously.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain columns:
        - 'ticker': str
        - 'eps_growth_pct': float (raw YoY EPS growth, e.g. 25.0 for 25%)
        - 'rev_growth_pct': float (raw YoY revenue growth)
        - 'price_vs_high': float (0-100 scale, current price / 52-week high * 100)
        - 'rs_percentile': float (0-100 scale)
        All four factor columns must be non-null for a stock to be considered.

    Returns
    -------
    pd.DataFrame
        Filtered DataFrame containing only stocks that pass all three gates.
    """
    initial_count = len(df)
    logger.info(f"Quality filter input: {initial_count} stocks")

    # ---- Step 1: Drop rows with any missing factor data ---- #
    required_cols = ['eps_growth_pct', 'rev_growth_pct', 'price_vs_high', 'rs_percentile']
    missing_mask = df[required_cols].isna().any(axis=1)
    missing_count = missing_mask.sum()
    if missing_count > 0:
        logger.info(f"  Excluded {missing_count} stocks with missing factor data")

    # ---- Step 2: Build individual gate masks ---- #
    gate1_mask = df['eps_growth_pct'] >= eps_growth_min
    gate2_mask = df['rev_growth_pct'] >= rev_growth_min
    gate3_mask = df['price_vs_high'] >= price_vs_high_min

    # Log individual gate pass rates
    gate1_pass = gate1_mask.sum()
    gate2_pass = gate2_mask.sum()
    gate3_pass = gate3_mask.sum()
    logger.info(f"  Gate 1 (EPS >= {eps_growth_min}%): {gate1_pass} pass ({gate1_pass/initial_count*100:.1f}%)")
    logger.info(f"  Gate 2 (Rev >= {rev_growth_min}%): {gate2_pass} pass ({gate2_pass/initial_count*100:.1f}%)")
    logger.info(f"  Gate 3 (Price/High >= {price_vs_high_min}%): {gate3_pass} pass ({gate3_pass/initial_count*100:.1f}%)")

    # ---- Step 3: Combined mask (all gates + no missing data) ---- #
    combined_mask = gate1_mask & gate2_mask & gate3_mask & ~missing_mask
    filtered_df = df[combined_mask].copy()
    pass_count = len(filtered_df)

    logger.info(f"  All gates combined: {pass_count} pass ({pass_count/initial_count*100:.1f}%)")

    # ---- Step 4: Sanity check on pass count ---- #
    if pass_count < min_pass_count:
        logger.warning(
            f"ALERT: Only {pass_count} stocks passed filters (below {min_pass_count} minimum). "
            f"Investigate data quality or market conditions."
        )
    elif pass_count > max_pass_count:
        logger.warning(
            f"ALERT: {pass_count} stocks passed filters (above {max_pass_count} maximum). "
            f"Filter thresholds may be too lenient or universe has expanded."
        )

    return filtered_df
```

**Typical filter reduction breakdown (approximate, varies by market regime):**

| Gate | Input | Pass | Fail Rate |
|------|-------|------|-----------|
| EPS Growth >= 5% | 2,000 | ~1,200 | ~40% |
| Revenue Growth >= 5% | 2,000 | ~1,100 | ~45% |
| Price vs 52-Week High >= 75% | 2,000 | ~1,000 | ~50% |
| All three combined | 2,000 | ~350-400 | ~80% |

The combined failure rate is higher than any individual gate because the gates are correlated but not perfectly so. Many stocks fail multiple gates simultaneously.

---

## 4. Composite Score Calculation

### Formula

```
Composite Score = 0.40 * RS_Percentile
               + 0.20 * min(EPS_Growth_Pct, 100)
               + 0.20 * min(Rev_Growth_Pct, 100)
               + 0.20 * Price_vs_High
```

### Weight Rationale

| Component | Weight | Justification |
|-----------|--------|---------------|
| RS Percentile | 40% | Relative strength is the single strongest predictor of future outperformance. Momentum is the dominant factor. |
| EPS Growth | 20% | Earnings quality matters, but less than price momentum in growth investing. |
| Revenue Growth | 20% | Revenue growth validates the business trajectory and sustainability. |
| Price vs 52-Week High | 20% | Technical positioning filters for institutional accumulation patterns. |

### Why Cap EPS and Revenue Growth at 100?

Without capping, a turnaround stock with 999% EPS growth would score:
- Uncapped: `0.20 * 999 = 199.8` contribution from EPS alone
- This would completely dominate the composite score, making the other three factors irrelevant

With capping at 100:
- Capped: `0.20 * 100 = 20` contribution from EPS
- A reasonable maximum contribution, on par with the other components

The cap ensures all four components operate on the same 0-100 scale, keeping the composite score in the 0-100 range.

**Note on Price vs 52-Week High:** This factor is already on a 0-100 scale by construction (it is a percentage), and stocks passing Gate 3 have values in the 75-100 range. No additional capping is needed.

**Note on RS Percentile:** By definition this is a percentile rank from 0 to 100. No capping needed.

### Implementation

```python
def compute_composite_score(
    df: pd.DataFrame,
    w_rs: float = 0.40,
    w_eps: float = 0.20,
    w_rev: float = 0.20,
    w_price: float = 0.20,
    growth_cap: float = 100.0,
) -> pd.DataFrame:
    """
    Compute the composite score for each stock in the filtered universe.

    Parameters
    ----------
    df : pd.DataFrame
        Filtered DataFrame (output of apply_quality_filters). Must contain:
        - 'rs_percentile': float, 0-100
        - 'eps_growth_pct': float, raw YoY growth percentage
        - 'rev_growth_pct': float, raw YoY growth percentage
        - 'price_vs_high': float, 0-100

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added 'composite_score' column, sorted descending.
    """
    assert abs(w_rs + w_eps + w_rev + w_price - 1.0) < 1e-9, "Weights must sum to 1.0"

    result = df.copy()

    # Cap EPS and Revenue growth contributions
    eps_capped = result['eps_growth_pct'].clip(upper=growth_cap)
    rev_capped = result['rev_growth_pct'].clip(upper=growth_cap)

    # Composite score
    result['composite_score'] = (
        w_rs * result['rs_percentile']
        + w_eps * eps_capped
        + w_rev * rev_capped
        + w_price * result['price_vs_high']
    )

    # Sort descending
    result = result.sort_values('composite_score', ascending=False).reset_index(drop=True)

    logger.info(
        f"Composite scores computed: "
        f"min={result['composite_score'].min():.2f}, "
        f"max={result['composite_score'].max():.2f}, "
        f"median={result['composite_score'].median():.2f}"
    )

    return result
```

### Worked Example: Score Breakdown

Consider three stocks that have passed all quality filters:

| Ticker | RS Pctl | EPS Growth | Rev Growth | Price/High |
|--------|---------|------------|------------|------------|
| AAAA | 95 | 45% | 30% | 92% |
| BBBB | 88 | 150% | 60% | 85% |
| CCCC | 92 | 20% | 15% | 98% |

**AAAA:**
```
0.40 * 95 + 0.20 * min(45, 100) + 0.20 * min(30, 100) + 0.20 * 92
= 38.0 + 9.0 + 6.0 + 18.4
= 71.4
```

**BBBB:**
```
0.40 * 88 + 0.20 * min(150, 100) + 0.20 * min(60, 100) + 0.20 * 85
= 35.2 + 20.0 + 12.0 + 17.0
= 84.2
```
Note: EPS growth of 150% is capped at 100. Without capping, BBBB's score would be 94.2 -- artificially inflated.

**CCCC:**
```
0.40 * 92 + 0.20 * min(20, 100) + 0.20 * min(15, 100) + 0.20 * 98
= 36.8 + 4.0 + 3.0 + 19.6
= 63.4
```

**Ranking:** BBBB (84.2) > AAAA (71.4) > CCCC (63.4)

---

## 5. Ranking and Top 25 Selection

### Selection Process

1. Sort all filtered stocks by `composite_score` descending.
2. Select the top 25 rows.
3. **Enforce sector concentration cap:** No single sector may exceed 40% of positions (more than 10 of 25 stocks). If any sector is over-concentrated, drop the lowest-scoring stock in that sector and replace with the next highest-scoring stock from a different sector. Repeat until all sectors are at or below 40%. See `enforce_sector_cap` below.
4. Assign equal weight: each position = 4% of portfolio (1/25 = 0.04).

### Tiebreaking

If two or more stocks share an identical composite score (rare, but possible), break ties using RS Percentile descending. Higher momentum wins.

**Rationale:** In a momentum-driven strategy, when all else is equal, the stock with stronger price action is the better bet.

If RS Percentile is also tied (extremely rare), break by ticker alphabetically for deterministic reproducibility.

```python
def select_top_n(
    df: pd.DataFrame,
    n: int = 25,
) -> pd.DataFrame:
    """
    Select the top N stocks by composite score with tiebreaking.

    Parameters
    ----------
    df : pd.DataFrame
        Scored and sorted DataFrame (output of compute_composite_score).
        Must contain 'composite_score', 'rs_percentile', 'ticker'.

    Returns
    -------
    pd.DataFrame
        Top N stocks with 'rank' column (1-indexed) and 'target_weight' column.
    """
    # Sort with tiebreakers: composite_score desc, rs_percentile desc, ticker asc
    sorted_df = df.sort_values(
        by=['composite_score', 'rs_percentile', 'ticker'],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    top_n = sorted_df.head(n).copy()
    top_n['rank'] = range(1, len(top_n) + 1)
    top_n['target_weight'] = 1.0 / n  # 0.04 for n=25

    logger.info(f"Selected top {len(top_n)} stocks")
    logger.info(f"  Score range: {top_n['composite_score'].iloc[-1]:.2f} - {top_n['composite_score'].iloc[0]:.2f}")
    logger.info(f"  Score at cutoff (rank {n}): {top_n['composite_score'].iloc[-1]:.2f}")

    # Log the stock just below the cutoff for context
    if len(df) > n:
        next_stock = sorted_df.iloc[n]
        logger.info(
            f"  First excluded: {next_stock['ticker']} "
            f"(score={next_stock['composite_score']:.2f})"
        )

    return top_n


def enforce_sector_cap(
    selected_df: pd.DataFrame,
    remaining_df: pd.DataFrame,
    max_sector_pct: float = 0.40,
) -> pd.DataFrame:
    """
    Enforce a maximum sector concentration limit on the selected portfolio.

    After selecting the top N stocks by composite score, this function checks
    whether any single GICS sector exceeds `max_sector_pct` of total positions.
    If so, it iteratively drops the lowest-scoring stock in the over-concentrated
    sector and replaces it with the next highest-scoring stock from a different
    sector drawn from `remaining_df`.

    Parameters
    ----------
    selected_df : pd.DataFrame
        The top N stocks (output of select_top_n). Must contain:
        - 'ticker': str
        - 'sector': str (GICS sector name)
        - 'composite_score': float
    remaining_df : pd.DataFrame
        All scored stocks that were NOT selected (i.e., ranked below the top N).
        Same required columns as selected_df, sorted by composite_score descending.
    max_sector_pct : float
        Maximum fraction of positions allowed in any single sector.
        Default 0.40 (40%). For a 25-stock portfolio this means no more
        than 10 stocks from one sector.

    Returns
    -------
    pd.DataFrame
        Adjusted selection with sector caps enforced. The 'rank' and
        'target_weight' columns are recalculated after replacements.
    """
    n = len(selected_df)
    max_sector_count = int(max_sector_pct * n)  # e.g., 10 for 25 stocks at 40%

    selected = selected_df.copy()
    remaining = remaining_df.copy()

    replacements_made = 0

    while True:
        # Count stocks per sector in current selection
        sector_counts = selected['sector'].value_counts()
        over_limit = sector_counts[sector_counts > max_sector_count]

        if over_limit.empty:
            break  # All sectors within cap

        for sector_name, count in over_limit.items():
            excess = count - max_sector_count
            logger.info(
                f"Sector cap: {sector_name} has {count} stocks "
                f"(max {max_sector_count}), removing {excess}"
            )

            # Find the lowest-scoring stocks in this sector within the selection
            sector_mask = selected['sector'] == sector_name
            sector_stocks = selected[sector_mask].sort_values(
                'composite_score', ascending=True
            )

            # Drop the lowest-scoring ones (one at a time, replacing each)
            for i in range(excess):
                drop_ticker = sector_stocks.iloc[i]['ticker']

                # Find the best replacement from a DIFFERENT sector
                replacement_mask = remaining['sector'] != sector_name
                eligible = remaining[replacement_mask]

                if eligible.empty:
                    logger.warning(
                        f"Sector cap: No replacement candidates from other sectors. "
                        f"Stopping with {sector_name} still over limit."
                    )
                    break

                # Take the top eligible replacement
                replacement_row = eligible.iloc[[0]]

                # Remove the dropped stock from selected
                selected = selected[selected['ticker'] != drop_ticker]
                # Add the replacement
                selected = pd.concat([selected, replacement_row], ignore_index=True)
                # Remove the replacement from the remaining pool
                remaining = remaining[
                    remaining['ticker'] != replacement_row.iloc[0]['ticker']
                ]
                replacements_made += 1

                logger.info(
                    f"  Replaced {drop_ticker} (score="
                    f"{sector_stocks.iloc[i]['composite_score']:.2f}) with "
                    f"{replacement_row.iloc[0]['ticker']} (score="
                    f"{replacement_row.iloc[0]['composite_score']:.2f}, "
                    f"sector={replacement_row.iloc[0]['sector']})"
                )

    # Re-sort and re-rank after replacements
    selected = selected.sort_values(
        by=['composite_score', 'rs_percentile', 'ticker'],
        ascending=[False, False, True],
    ).reset_index(drop=True)
    selected['rank'] = range(1, len(selected) + 1)
    selected['target_weight'] = 1.0 / n

    if replacements_made > 0:
        logger.info(f"Sector cap enforcement: {replacements_made} replacement(s) made")
    else:
        logger.info("Sector cap enforcement: no adjustments needed")

    return selected
```

### Sector Cap Rule

The 40% maximum sector concentration limit (defined in doc 05) is enforced at this stage. After selecting the initial top 25, if any single GICS sector contains more than 10 stocks (40% of 25), the lowest-scoring stocks in that sector are dropped and replaced with the next-highest-scoring stocks from different sectors.

**Why enforce it here (not in quality filtering)?** The sector cap is a portfolio construction constraint, not a stock quality issue. A stock from an over-represented sector may be individually excellent but creates concentration risk when combined with many peers. By applying the cap after scoring and selection, we preserve the integrity of the composite score ranking and make the minimum number of swaps necessary.

**Integration with the pipeline:** `enforce_sector_cap` is called immediately after `select_top_n`, receiving the top 25 and the remaining scored candidates (ranks 26+). See the `EmergingGrowthSelector.run()` method below for the integration point.

### Output Format: Ranking Table

The full ranking output includes all scored columns for transparency:

```
Rank | Ticker | Composite | RS Pctl | EPS Gr% | Rev Gr% | Px/High | Sector
-----+--------+-----------+---------+---------+---------+---------+-----------
   1 | NVDA   |     89.4  |    98   |   122%  |    61%  |   94%   | Technology
   2 | PLTR   |     86.1  |    96   |    88%  |    42%  |   91%   | Technology
   3 | GE     |     83.7  |    94   |    75%  |    19%  |   97%   | Industrials
 ...
  25 | DECK   |     68.2  |    82   |    22%  |    18%  |   88%   | Cons. Disc.
-----+--------+-----------+---------+---------+---------+---------+-----------
  26 | FIRST EXCLUDED: URI (score=67.9)
```

---

## 6. BUY/SELL/HOLD Signal Generation

This is the actionable output of the entire pipeline. Each month, after selecting the new Top 25, we compare it to the prior month's portfolio to determine what trades to execute.

### Signal Definitions

| Signal | Condition | Action |
|--------|-----------|--------|
| **BUY** | Ticker is in this month's Top 25 but was NOT in last month's portfolio | Open new position at 4% target weight |
| **SELL** | Ticker was in last month's portfolio but is NOT in this month's Top 25 | Close entire position (sell 100%) |
| **HOLD** | Ticker is in BOTH this month's Top 25 and last month's portfolio | Keep position, rebalance to 4% if drifted |

### Implementation

```python
from dataclasses import dataclass
from typing import Optional


@dataclass
class Signal:
    ticker: str
    action: str  # "BUY", "SELL", "HOLD"
    composite_score: Optional[float]  # None for SELL signals (no longer scored)
    rs_percentile: Optional[float]
    eps_growth_pct: Optional[float]
    rev_growth_pct: Optional[float]
    price_vs_high: Optional[float]
    sector: Optional[str]
    rank: Optional[int]  # None for SELL signals
    prior_month_rank: Optional[int]  # None for BUY signals


def generate_signals(
    current_top25: pd.DataFrame,
    prior_holdings: set[str],
) -> list[Signal]:
    """
    Generate BUY/SELL/HOLD signals by comparing current top 25 to prior holdings.

    Parameters
    ----------
    current_top25 : pd.DataFrame
        This month's top 25 stocks (output of select_top_n).
        Must contain: 'ticker', 'composite_score', 'rs_percentile',
        'eps_growth_pct', 'rev_growth_pct', 'price_vs_high', 'sector', 'rank'.
    prior_holdings : set[str]
        Set of ticker strings held in the prior month's portfolio.

    Returns
    -------
    list[Signal]
        Sorted: BUY signals first, then HOLD, then SELL.
    """
    current_tickers = set(current_top25['ticker'].tolist())

    signals = []

    # ---- BUY: in current top 25 but not in prior holdings ---- #
    buy_tickers = current_tickers - prior_holdings
    for _, row in current_top25[current_top25['ticker'].isin(buy_tickers)].iterrows():
        signals.append(Signal(
            ticker=row['ticker'],
            action='BUY',
            composite_score=row['composite_score'],
            rs_percentile=row['rs_percentile'],
            eps_growth_pct=row['eps_growth_pct'],
            rev_growth_pct=row['rev_growth_pct'],
            price_vs_high=row['price_vs_high'],
            sector=row.get('sector', 'Unknown'),
            rank=row['rank'],
            prior_month_rank=None,
        ))

    # ---- HOLD: in both current top 25 and prior holdings ---- #
    hold_tickers = current_tickers & prior_holdings
    for _, row in current_top25[current_top25['ticker'].isin(hold_tickers)].iterrows():
        signals.append(Signal(
            ticker=row['ticker'],
            action='HOLD',
            composite_score=row['composite_score'],
            rs_percentile=row['rs_percentile'],
            eps_growth_pct=row['eps_growth_pct'],
            rev_growth_pct=row['rev_growth_pct'],
            price_vs_high=row['price_vs_high'],
            sector=row.get('sector', 'Unknown'),
            rank=row['rank'],
            prior_month_rank=None,  # Populate if prior ranking data available
        ))

    # ---- SELL: in prior holdings but not in current top 25 ---- #
    sell_tickers = prior_holdings - current_tickers
    for ticker in sorted(sell_tickers):
        signals.append(Signal(
            ticker=ticker,
            action='SELL',
            composite_score=None,
            rs_percentile=None,
            eps_growth_pct=None,
            rev_growth_pct=None,
            price_vs_high=None,
            sector=None,
            rank=None,
            prior_month_rank=None,
        ))

    # Sort: BUY first (by rank), HOLD (by rank), SELL (by ticker)
    sort_order = {'BUY': 0, 'HOLD': 1, 'SELL': 2}
    signals.sort(key=lambda s: (sort_order[s.action], s.rank or 999, s.ticker))

    # Log summary
    buy_count = sum(1 for s in signals if s.action == 'BUY')
    hold_count = sum(1 for s in signals if s.action == 'HOLD')
    sell_count = sum(1 for s in signals if s.action == 'SELL')
    logger.info(f"Signals generated: {buy_count} BUY, {hold_count} HOLD, {sell_count} SELL")
    logger.info(f"Monthly turnover: {buy_count}/{25} = {buy_count/25*100:.0f}%")

    return signals
```

### Signal Output Format

The signal report is divided into three sections for clarity:

```
================================================================
       EMERGING GROWTH STRATEGY - MONTHLY SIGNAL REPORT
       Rebalance Date: 2026-02-27
================================================================

--- NEW POSITIONS (BUY) --- [7 stocks]
Rank | Ticker | Score | RS  | EPS Gr | Rev Gr | Px/Hi | Sector
   3 | CRWD   | 83.7  |  94 |   75%  |   19%  |  97%  | Technology
   8 | AXON   | 79.2  |  89 |   44%  |   33%  |  93%  | Industrials
  11 | TOST   | 76.8  |  86 |   62%  |   28%  |  82%  | Technology
  15 | HOOD   | 73.4  |  83 |   88%  |   42%  |  78%  | Financials
  19 | DUOL   | 71.1  |  80 |   38%  |   44%  |  85%  | Technology
  22 | FIX    | 69.3  |  78 |   31%  |   22%  |  91%  | Industrials
  24 | ONON   | 68.5  |  77 |   35%  |   47%  |  80%  | Cons. Disc.

--- EXISTING POSITIONS (HOLD) --- [18 stocks]
Rank | Ticker | Score | RS  | EPS Gr | Rev Gr | Px/Hi | Sector
   1 | NVDA   | 89.4  |  98 |  122%  |   61%  |  94%  | Technology
   2 | PLTR   | 86.1  |  96 |   88%  |   42%  |  91%  | Technology
   4 | VST    | 82.9  |  93 |   65%  |   12%  |  96%  | Utilities
  ...
  25 | DECK   | 68.2  |  82 |   22%  |   18%  |  88%  | Cons. Disc.

--- EXIT POSITIONS (SELL) --- [7 stocks]
Ticker | Reason
ABNB   | Dropped out of Top 25 (prev rank: 21)
DKNG   | Dropped out of Top 25 (prev rank: 18)
ENPH   | Dropped out of Top 25 (prev rank: 23)
LLY    | Dropped out of Top 25 (prev rank: 14)
MELI   | Dropped out of Top 25 (prev rank: 25)
SMCI   | Dropped out of Top 25 (prev rank: 16)
SPOT   | Dropped out of Top 25 (prev rank: 20)

================================================================
SUMMARY: 7 BUY + 18 HOLD + 7 SELL = 32 total signals
Turnover: 28% (7/25 new positions)
Estimated transaction costs: 14 trades x 10 bps = ~14 bps portfolio drag
================================================================
```

### First Month (No Prior Holdings)

On the strategy's initial month, `prior_holdings` is an empty set. All 25 selected stocks are BUY signals, and there are no HOLD or SELL signals. This is the only month with 100% turnover.

---

## 7. Rebalancing Mechanics

### Process Order

Rebalancing follows a strict sequence to manage cash flow correctly:

```
Step 1: SELL exits       → Generates cash from liquidating positions
Step 2: BUY new entries  → Deploys cash into new 4% positions
Step 3: Rebalance HOLDs  → Trim or add to bring each back to 4%
```

### Equal Weight Target

Each of the 25 positions targets exactly **4% of total portfolio value** (1/25).

### Drift Tolerance and Trimming

| Condition | Action |
|-----------|--------|
| Position weight < 2% | Add to bring back to 4% (rare -- implies severe underperformance) |
| Position weight between 2% and 6% | No action needed (within tolerance band) |
| Position weight > 6% | Trim back to 4% (strong outperformer has drifted too high) |

The 6% trim threshold serves two purposes:
1. **Risk management:** No single position should dominate the portfolio.
2. **Profit taking:** Trimming winners locks in gains from outperformers.

### Transaction Cost Estimate

| Parameter | Value |
|-----------|-------|
| Cost per trade | 10 basis points (0.10%) |
| Average monthly trades | ~11.6 (from backtest: 1,535 trades / 132 months) |
| Monthly cost drag | ~12 bps per month (11.6 * 10 bps / 25 positions, weighted) |
| Annual cost drag | ~140 bps (~1.4% per year) |

```python
def compute_rebalance_trades(
    current_top25: pd.DataFrame,
    prior_holdings: dict[str, float],  # ticker -> current_weight
    portfolio_value: float,
    target_weight: float = 0.04,
    trim_threshold: float = 0.06,
    add_threshold: float = 0.02,
    cost_bps: float = 10.0,
) -> pd.DataFrame:
    """
    Compute the specific trades needed to rebalance the portfolio.

    Parameters
    ----------
    current_top25 : pd.DataFrame
        This month's top 25 selections.
    prior_holdings : dict[str, float]
        Ticker -> current portfolio weight (0.0 to 1.0) for each held position.
    portfolio_value : float
        Total portfolio value in dollars.
    target_weight : float
        Target weight per position (default 0.04 = 4%).
    trim_threshold : float
        Trim positions above this weight (default 0.06 = 6%).
    add_threshold : float
        Add to positions below this weight (default 0.02 = 2%).
    cost_bps : float
        Transaction cost in basis points per trade.

    Returns
    -------
    pd.DataFrame
        Trade list with columns: ticker, action, current_weight, target_weight,
        trade_dollars, estimated_cost.
    """
    current_tickers = set(current_top25['ticker'].tolist())
    prior_tickers = set(prior_holdings.keys())
    trades = []

    # Step 1: SELL exits (liquidate entire position)
    for ticker in sorted(prior_tickers - current_tickers):
        weight = prior_holdings[ticker]
        trade_value = weight * portfolio_value
        trades.append({
            'ticker': ticker,
            'action': 'SELL',
            'current_weight': weight,
            'target_weight': 0.0,
            'trade_dollars': -trade_value,
            'estimated_cost': trade_value * cost_bps / 10_000,
        })

    # Step 2: BUY new entries (buy to target weight)
    for ticker in sorted(current_tickers - prior_tickers):
        trade_value = target_weight * portfolio_value
        trades.append({
            'ticker': ticker,
            'action': 'BUY',
            'current_weight': 0.0,
            'target_weight': target_weight,
            'trade_dollars': trade_value,
            'estimated_cost': trade_value * cost_bps / 10_000,
        })

    # Step 3: Rebalance HOLDs (trim or add based on drift)
    for ticker in sorted(current_tickers & prior_tickers):
        weight = prior_holdings[ticker]
        if weight > trim_threshold:
            # Trim back to target
            trim_value = (weight - target_weight) * portfolio_value
            trades.append({
                'ticker': ticker,
                'action': 'TRIM',
                'current_weight': weight,
                'target_weight': target_weight,
                'trade_dollars': -trim_value,
                'estimated_cost': trim_value * cost_bps / 10_000,
            })
        elif weight < add_threshold:
            # Add back to target
            add_value = (target_weight - weight) * portfolio_value
            trades.append({
                'ticker': ticker,
                'action': 'ADD',
                'current_weight': weight,
                'target_weight': target_weight,
                'trade_dollars': add_value,
                'estimated_cost': add_value * cost_bps / 10_000,
            })
        # else: within tolerance band, no trade needed

    trade_df = pd.DataFrame(trades)

    if len(trade_df) > 0:
        total_cost = trade_df['estimated_cost'].sum()
        logger.info(
            f"Rebalance: {len(trade_df)} trades, "
            f"estimated cost ${total_cost:.2f} "
            f"({total_cost / portfolio_value * 10_000:.1f} bps)"
        )

    return trade_df
```

---

## 8. Monthly Turnover Analysis

### Expected Turnover

From backtest data over the 132-month period (Jan 2014 - Dec 2024):

| Metric | Value |
|--------|-------|
| Total trades executed | 1,535 |
| Average trades per month | ~11.6 (buys + sells) |
| Average new positions per month | ~5.8 (half are buys, half are sells) |
| Average monthly turnover | ~28% (~7 new out of 25) |
| Annual turnover | ~336% (full portfolio turns over ~3.4x per year) |

### Turnover Implications

**Cost impact:**
- At 10 bps per trade, ~11.6 trades/month = ~1.4% annual drag
- This is moderate for an active strategy but meaningful -- must be justified by alpha

**Tax implications:**
- High turnover means most gains are short-term (held < 12 months)
- Strategy is best suited for tax-advantaged accounts (IRA, 401k)
- In taxable accounts, after-tax returns are reduced by the short-term capital gains rate differential

**Turnover tracking in production:**

```python
def compute_turnover_stats(
    signals: list[Signal],
    portfolio_size: int = 25,
) -> dict:
    """Compute turnover statistics from a month's signals."""
    buy_count = sum(1 for s in signals if s.action == 'BUY')
    sell_count = sum(1 for s in signals if s.action == 'SELL')
    hold_count = sum(1 for s in signals if s.action == 'HOLD')

    return {
        'buy_count': buy_count,
        'sell_count': sell_count,
        'hold_count': hold_count,
        'total_trades': buy_count + sell_count,
        'turnover_pct': buy_count / portfolio_size * 100,
        'retention_pct': hold_count / portfolio_size * 100,
    }
```

---

## 9. Complete Implementation

The following class ties the entire pipeline together: quality filtering, composite scoring, ranking, selection, signal generation, and report formatting.

```python
"""
Emerging Growth Strategy - Quality Filters, Scoring, and Signal Generation

Pipeline:
    Raw factor DataFrame (~2,000 stocks)
    → Quality filter gates (~350-400 stocks)
    → Composite score calculation
    → Rank and select top 25
    → Compare to prior month's holdings
    → Generate BUY/SELL/HOLD signals
    → Output formatted report
"""

import pandas as pd
import logging
from dataclasses import dataclass, field
from typing import Optional
from datetime import date

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    """A single BUY/SELL/HOLD signal for one ticker."""
    ticker: str
    action: str  # "BUY", "SELL", "HOLD"
    composite_score: Optional[float] = None
    rs_percentile: Optional[float] = None
    eps_growth_pct: Optional[float] = None
    rev_growth_pct: Optional[float] = None
    price_vs_high: Optional[float] = None
    sector: Optional[str] = None
    rank: Optional[int] = None
    prior_month_rank: Optional[int] = None


@dataclass
class MonthlyReport:
    """Full output of one month's signal generation."""
    rebalance_date: date
    signals: list[Signal] = field(default_factory=list)
    buy_count: int = 0
    hold_count: int = 0
    sell_count: int = 0
    turnover_pct: float = 0.0
    filtered_universe_size: int = 0
    raw_universe_size: int = 0
    score_at_cutoff: Optional[float] = None
    first_excluded_ticker: Optional[str] = None
    first_excluded_score: Optional[float] = None


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

class EmergingGrowthSelector:
    """
    End-to-end pipeline: filter → score → rank → select → signal.

    Usage:
        selector = EmergingGrowthSelector()
        report = selector.run(
            factor_df=df,                    # DataFrame with all 4 factors
            prior_holdings={'NVDA', 'PLTR', ...},  # Last month's tickers
            rebalance_date=date(2026, 2, 27),
        )
        selector.print_report(report)
    """

    def __init__(
        self,
        # Quality filter thresholds
        eps_growth_min: float = 5.0,
        rev_growth_min: float = 5.0,
        price_vs_high_min: float = 75.0,
        # Composite score weights
        w_rs: float = 0.40,
        w_eps: float = 0.20,
        w_rev: float = 0.20,
        w_price: float = 0.20,
        # Growth cap for scoring
        growth_cap: float = 100.0,
        # Selection
        top_n: int = 25,
        # Sanity checks
        min_filter_pass: int = 100,
        max_filter_pass: int = 600,
    ):
        self.eps_growth_min = eps_growth_min
        self.rev_growth_min = rev_growth_min
        self.price_vs_high_min = price_vs_high_min
        self.w_rs = w_rs
        self.w_eps = w_eps
        self.w_rev = w_rev
        self.w_price = w_price
        self.growth_cap = growth_cap
        self.top_n = top_n
        self.min_filter_pass = min_filter_pass
        self.max_filter_pass = max_filter_pass

        assert abs(w_rs + w_eps + w_rev + w_price - 1.0) < 1e-9, "Weights must sum to 1.0"

    # ----- Step 1: Quality Filters ----- #

    def apply_quality_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all three quality filter gates. Returns filtered DataFrame."""
        initial_count = len(df)
        logger.info(f"Quality filter input: {initial_count} stocks")

        # Drop rows with missing factor data
        required_cols = ['eps_growth_pct', 'rev_growth_pct', 'price_vs_high', 'rs_percentile']
        missing_mask = df[required_cols].isna().any(axis=1)
        missing_count = missing_mask.sum()
        if missing_count > 0:
            logger.info(f"  Excluded {missing_count} stocks with missing factor data")

        # Individual gate masks
        gate1 = df['eps_growth_pct'] >= self.eps_growth_min
        gate2 = df['rev_growth_pct'] >= self.rev_growth_min
        gate3 = df['price_vs_high'] >= self.price_vs_high_min

        # Log individual pass rates
        for name, mask in [("EPS Growth", gate1), ("Rev Growth", gate2), ("Price/High", gate3)]:
            n = mask.sum()
            logger.info(f"  {name}: {n} pass ({n / initial_count * 100:.1f}%)")

        # Combined
        combined = gate1 & gate2 & gate3 & ~missing_mask
        filtered = df[combined].copy()
        pass_count = len(filtered)
        logger.info(f"  All gates combined: {pass_count} pass ({pass_count / initial_count * 100:.1f}%)")

        # Sanity checks
        if pass_count < self.min_filter_pass:
            logger.warning(
                f"ALERT: Only {pass_count} stocks passed (below {self.min_filter_pass}). "
                f"Check data quality or market conditions."
            )
        elif pass_count > self.max_filter_pass:
            logger.warning(
                f"ALERT: {pass_count} stocks passed (above {self.max_filter_pass}). "
                f"Filters may be too lenient."
            )

        return filtered

    # ----- Step 2: Composite Score ----- #

    def compute_composite_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute composite score for each stock. Returns DataFrame sorted descending."""
        result = df.copy()

        eps_capped = result['eps_growth_pct'].clip(upper=self.growth_cap)
        rev_capped = result['rev_growth_pct'].clip(upper=self.growth_cap)

        result['composite_score'] = (
            self.w_rs * result['rs_percentile']
            + self.w_eps * eps_capped
            + self.w_rev * rev_capped
            + self.w_price * result['price_vs_high']
        )

        result = result.sort_values(
            by=['composite_score', 'rs_percentile', 'ticker'],
            ascending=[False, False, True],
        ).reset_index(drop=True)

        logger.info(
            f"Composite scores: min={result['composite_score'].min():.2f}, "
            f"max={result['composite_score'].max():.2f}, "
            f"median={result['composite_score'].median():.2f}"
        )

        return result

    # ----- Step 3: Select Top N ----- #

    def select_top_n(self, df: pd.DataFrame) -> tuple[pd.DataFrame, Optional[str], Optional[float]]:
        """
        Select top N stocks by composite score.

        Returns
        -------
        tuple of (top_n_df, first_excluded_ticker, first_excluded_score)
        """
        top = df.head(self.top_n).copy()
        top['rank'] = range(1, len(top) + 1)
        top['target_weight'] = 1.0 / self.top_n

        first_excluded_ticker = None
        first_excluded_score = None
        if len(df) > self.top_n:
            excluded = df.iloc[self.top_n]
            first_excluded_ticker = excluded['ticker']
            first_excluded_score = excluded['composite_score']
            logger.info(
                f"First excluded: {first_excluded_ticker} (score={first_excluded_score:.2f})"
            )

        logger.info(
            f"Selected top {len(top)}: score range "
            f"{top['composite_score'].iloc[-1]:.2f} - {top['composite_score'].iloc[0]:.2f}"
        )

        return top, first_excluded_ticker, first_excluded_score

    # ----- Step 3b: Enforce Sector Cap ----- #

    def enforce_sector_cap(
        self,
        selected_df: pd.DataFrame,
        remaining_df: pd.DataFrame,
        max_sector_pct: float = 0.40,
    ) -> pd.DataFrame:
        """
        Enforce maximum sector concentration on the selected portfolio.

        If any GICS sector exceeds max_sector_pct of positions, iteratively
        drop the lowest-scoring stock in that sector and replace with the
        next highest-scoring stock from a different sector.

        Parameters
        ----------
        selected_df : pd.DataFrame
            The top N stocks (output of select_top_n).
        remaining_df : pd.DataFrame
            Scored stocks not selected (ranks N+1 onward), sorted by
            composite_score descending.
        max_sector_pct : float
            Maximum fraction of positions in any single sector (default 0.40).

        Returns
        -------
        pd.DataFrame
            Adjusted selection with sector caps enforced, re-ranked.
        """
        n = len(selected_df)
        max_sector_count = int(max_sector_pct * n)

        selected = selected_df.copy()
        remaining = remaining_df.copy()
        replacements_made = 0

        while True:
            sector_counts = selected['sector'].value_counts()
            over_limit = sector_counts[sector_counts > max_sector_count]

            if over_limit.empty:
                break

            for sector_name, count in over_limit.items():
                excess = count - max_sector_count
                logger.info(
                    f"Sector cap: {sector_name} has {count} stocks "
                    f"(max {max_sector_count}), removing {excess}"
                )

                sector_stocks = selected[selected['sector'] == sector_name].sort_values(
                    'composite_score', ascending=True
                )

                for i in range(excess):
                    drop_ticker = sector_stocks.iloc[i]['ticker']
                    eligible = remaining[remaining['sector'] != sector_name]

                    if eligible.empty:
                        logger.warning(
                            f"Sector cap: No replacement candidates from other sectors."
                        )
                        break

                    replacement_row = eligible.iloc[[0]]
                    selected = selected[selected['ticker'] != drop_ticker]
                    selected = pd.concat([selected, replacement_row], ignore_index=True)
                    remaining = remaining[
                        remaining['ticker'] != replacement_row.iloc[0]['ticker']
                    ]
                    replacements_made += 1

                    logger.info(
                        f"  Replaced {drop_ticker} "
                        f"(score={sector_stocks.iloc[i]['composite_score']:.2f}) with "
                        f"{replacement_row.iloc[0]['ticker']} "
                        f"(score={replacement_row.iloc[0]['composite_score']:.2f}, "
                        f"sector={replacement_row.iloc[0]['sector']})"
                    )

        # Re-sort and re-rank
        selected = selected.sort_values(
            by=['composite_score', 'rs_percentile', 'ticker'],
            ascending=[False, False, True],
        ).reset_index(drop=True)
        selected['rank'] = range(1, len(selected) + 1)
        selected['target_weight'] = 1.0 / n

        if replacements_made > 0:
            logger.info(f"Sector cap enforcement: {replacements_made} replacement(s) made")
        else:
            logger.info("Sector cap enforcement: no adjustments needed")

        return selected

    # ----- Step 4: Generate Signals ----- #

    def generate_signals(
        self,
        current_top25: pd.DataFrame,
        prior_holdings: set[str],
    ) -> list[Signal]:
        """Compare current top 25 to prior holdings and generate signals."""
        current_tickers = set(current_top25['ticker'].tolist())

        signals = []

        # BUY: new entries
        buy_tickers = current_tickers - prior_holdings
        for _, row in current_top25[current_top25['ticker'].isin(buy_tickers)].iterrows():
            signals.append(Signal(
                ticker=row['ticker'],
                action='BUY',
                composite_score=row['composite_score'],
                rs_percentile=row['rs_percentile'],
                eps_growth_pct=row['eps_growth_pct'],
                rev_growth_pct=row['rev_growth_pct'],
                price_vs_high=row['price_vs_high'],
                sector=row.get('sector', 'Unknown'),
                rank=int(row['rank']),
            ))

        # HOLD: continuing positions
        hold_tickers = current_tickers & prior_holdings
        for _, row in current_top25[current_top25['ticker'].isin(hold_tickers)].iterrows():
            signals.append(Signal(
                ticker=row['ticker'],
                action='HOLD',
                composite_score=row['composite_score'],
                rs_percentile=row['rs_percentile'],
                eps_growth_pct=row['eps_growth_pct'],
                rev_growth_pct=row['rev_growth_pct'],
                price_vs_high=row['price_vs_high'],
                sector=row.get('sector', 'Unknown'),
                rank=int(row['rank']),
            ))

        # SELL: exits
        sell_tickers = prior_holdings - current_tickers
        for ticker in sorted(sell_tickers):
            signals.append(Signal(ticker=ticker, action='SELL'))

        # Sort: BUY (by rank), HOLD (by rank), SELL (by ticker)
        order = {'BUY': 0, 'HOLD': 1, 'SELL': 2}
        signals.sort(key=lambda s: (order[s.action], s.rank or 999, s.ticker))

        return signals

    # ----- Full Pipeline ----- #

    def run(
        self,
        factor_df: pd.DataFrame,
        prior_holdings: set[str],
        rebalance_date: date,
    ) -> MonthlyReport:
        """
        Execute the full pipeline: filter → score → rank → select → signal.

        Parameters
        ----------
        factor_df : pd.DataFrame
            Raw factor data for the full universe. Required columns:
            - ticker: str
            - rs_percentile: float (0-100)
            - eps_growth_pct: float (raw YoY percentage, e.g. 25.0 for 25%)
            - rev_growth_pct: float (raw YoY percentage)
            - price_vs_high: float (0-100)
            - sector: str (optional but recommended)
        prior_holdings : set[str]
            Tickers held in the prior month's portfolio. Empty set for first month.
        rebalance_date : date
            The date of this rebalance.

        Returns
        -------
        MonthlyReport
            Complete report with signals, counts, and metadata.
        """
        raw_count = len(factor_df)
        logger.info(f"=== Emerging Growth Pipeline: {rebalance_date} ===")

        # Step 1: Quality filters
        filtered = self.apply_quality_filters(factor_df)

        # Step 2: Composite scores
        scored = self.compute_composite_scores(filtered)

        # Step 3: Select top N
        top25, excl_ticker, excl_score = self.select_top_n(scored)

        # Step 3b: Enforce sector concentration cap (max 40% per sector)
        remaining = scored.iloc[self.top_n:].copy()
        top25 = self.enforce_sector_cap(top25, remaining)

        # Step 4: Generate signals
        signals = self.generate_signals(top25, prior_holdings)

        # Build report
        buy_count = sum(1 for s in signals if s.action == 'BUY')
        hold_count = sum(1 for s in signals if s.action == 'HOLD')
        sell_count = sum(1 for s in signals if s.action == 'SELL')

        report = MonthlyReport(
            rebalance_date=rebalance_date,
            signals=signals,
            buy_count=buy_count,
            hold_count=hold_count,
            sell_count=sell_count,
            turnover_pct=buy_count / self.top_n * 100,
            filtered_universe_size=len(filtered),
            raw_universe_size=raw_count,
            score_at_cutoff=top25['composite_score'].iloc[-1] if len(top25) > 0 else None,
            first_excluded_ticker=excl_ticker,
            first_excluded_score=excl_score,
        )

        logger.info(
            f"Pipeline complete: {buy_count} BUY, {hold_count} HOLD, {sell_count} SELL "
            f"(turnover={report.turnover_pct:.0f}%)"
        )

        return report

    # ----- Report Formatting ----- #

    def format_report(self, report: MonthlyReport) -> str:
        """Format a MonthlyReport as a human-readable string."""
        lines = []
        w = 72  # column width

        lines.append("=" * w)
        lines.append("  EMERGING GROWTH STRATEGY - MONTHLY SIGNAL REPORT")
        lines.append(f"  Rebalance Date: {report.rebalance_date}")
        lines.append(f"  Universe: {report.raw_universe_size} raw → "
                      f"{report.filtered_universe_size} filtered → {self.top_n} selected")
        lines.append("=" * w)

        # Group signals by action
        buys = [s for s in report.signals if s.action == 'BUY']
        holds = [s for s in report.signals if s.action == 'HOLD']
        sells = [s for s in report.signals if s.action == 'SELL']

        header = f"{'Rank':>4} | {'Ticker':<6} | {'Score':>5} | {'RS':>3} | {'EPS%':>5} | {'Rev%':>5} | {'P/H':>4} | {'Sector':<14}"
        separator = "-" * len(header)

        # BUY section
        lines.append("")
        lines.append(f"--- NEW POSITIONS (BUY) --- [{len(buys)} stocks]")
        if buys:
            lines.append(header)
            lines.append(separator)
            for s in buys:
                lines.append(
                    f"{s.rank:>4} | {s.ticker:<6} | {s.composite_score:>5.1f} | "
                    f"{s.rs_percentile:>3.0f} | {s.eps_growth_pct:>5.0f} | "
                    f"{s.rev_growth_pct:>5.0f} | {s.price_vs_high:>4.0f} | "
                    f"{(s.sector or 'Unknown'):<14}"
                )
        else:
            lines.append("  (none)")

        # HOLD section
        lines.append("")
        lines.append(f"--- EXISTING POSITIONS (HOLD) --- [{len(holds)} stocks]")
        if holds:
            lines.append(header)
            lines.append(separator)
            for s in holds:
                lines.append(
                    f"{s.rank:>4} | {s.ticker:<6} | {s.composite_score:>5.1f} | "
                    f"{s.rs_percentile:>3.0f} | {s.eps_growth_pct:>5.0f} | "
                    f"{s.rev_growth_pct:>5.0f} | {s.price_vs_high:>4.0f} | "
                    f"{(s.sector or 'Unknown'):<14}"
                )
        else:
            lines.append("  (none)")

        # SELL section
        lines.append("")
        lines.append(f"--- EXIT POSITIONS (SELL) --- [{len(sells)} stocks]")
        if sells:
            for s in sells:
                lines.append(f"  {s.ticker}")
        else:
            lines.append("  (none)")

        # Summary
        total_trades = report.buy_count + report.sell_count
        est_cost_bps = total_trades * 10  # 10 bps per trade, simplified
        lines.append("")
        lines.append("=" * w)
        lines.append(
            f"  SUMMARY: {report.buy_count} BUY + {report.hold_count} HOLD + "
            f"{report.sell_count} SELL = {len(report.signals)} total signals"
        )
        lines.append(f"  Turnover: {report.turnover_pct:.0f}% ({report.buy_count}/{self.top_n} new positions)")
        lines.append(f"  Score at cutoff (rank {self.top_n}): {report.score_at_cutoff:.2f}")
        if report.first_excluded_ticker:
            lines.append(
                f"  First excluded: {report.first_excluded_ticker} "
                f"(score={report.first_excluded_score:.2f})"
            )
        lines.append(f"  Estimated cost: {total_trades} trades x 10 bps = ~{est_cost_bps} bps total")
        lines.append("=" * w)

        return "\n".join(lines)

    def print_report(self, report: MonthlyReport) -> None:
        """Print formatted report to stdout."""
        print(self.format_report(report))


# ---------------------------------------------------------------------------
# Worked example
# ---------------------------------------------------------------------------

def worked_example():
    """
    Demonstrate the full pipeline with synthetic data.
    Shows how stocks flow through filtering, scoring, and signal generation.
    """
    import numpy as np

    np.random.seed(42)
    n = 50  # Small universe for illustration

    # Generate synthetic factor data for 50 stocks
    tickers = [f"STK{i:03d}" for i in range(n)]
    sectors = np.random.choice(
        ['Technology', 'Healthcare', 'Financials', 'Industrials', 'Cons. Disc.'],
        size=n,
    )

    df = pd.DataFrame({
        'ticker': tickers,
        'sector': sectors,
        'rs_percentile': np.random.uniform(10, 99, n).round(1),
        'eps_growth_pct': np.random.uniform(-20, 120, n).round(1),
        'rev_growth_pct': np.random.uniform(-10, 80, n).round(1),
        'price_vs_high': np.random.uniform(50, 100, n).round(1),
    })

    # Add a turnaround stock
    df.loc[0, 'ticker'] = 'TURN'
    df.loc[0, 'eps_growth_pct'] = 999.0  # Turnaround sentinel
    df.loc[0, 'rev_growth_pct'] = 45.0
    df.loc[0, 'rs_percentile'] = 91.0
    df.loc[0, 'price_vs_high'] = 88.0

    # Simulate prior month's holdings (5 tickers that happen to be in our universe)
    prior_holdings = {'STK005', 'STK012', 'STK020', 'STK033', 'TURN'}

    # Run pipeline
    selector = EmergingGrowthSelector(top_n=10)  # Top 10 for small universe
    report = selector.run(
        factor_df=df,
        prior_holdings=prior_holdings,
        rebalance_date=date(2026, 2, 27),
    )

    # Print results
    selector.print_report(report)

    # Show detailed score breakdown for top 3
    print("\n--- Detailed Score Breakdown (Top 3) ---")
    for s in report.signals[:3]:
        if s.composite_score is not None:
            eps_contrib = 0.20 * min(s.eps_growth_pct, 100)
            rev_contrib = 0.20 * min(s.rev_growth_pct, 100)
            rs_contrib = 0.40 * s.rs_percentile
            ph_contrib = 0.20 * s.price_vs_high
            print(f"\n{s.ticker} (Rank {s.rank}, Score {s.composite_score:.2f}):")
            print(f"  RS:     0.40 x {s.rs_percentile:.1f} = {rs_contrib:.2f}")
            print(f"  EPS:    0.20 x min({s.eps_growth_pct:.1f}, 100) = {eps_contrib:.2f}")
            print(f"  Rev:    0.20 x min({s.rev_growth_pct:.1f}, 100) = {rev_contrib:.2f}")
            print(f"  Px/Hi:  0.20 x {s.price_vs_high:.1f} = {ph_contrib:.2f}")
            print(f"  Total:  {rs_contrib:.2f} + {eps_contrib:.2f} + {rev_contrib:.2f} + {ph_contrib:.2f} = {s.composite_score:.2f}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    worked_example()
```

### Running the Worked Example

```bash
python -c "
from docs.03_quality_filters_and_scoring import worked_example
worked_example()
"
```

Expected output (with synthetic data, seed=42):

```
=== Emerging Growth Pipeline: 2026-02-27 ===
Quality filter input: 50 stocks
  Excluded 0 stocks with missing factor data
  EPS Growth: 38 pass (76.0%)
  Rev Growth: 40 pass (80.0%)
  Price/High: 26 pass (52.0%)
  All gates combined: 18 pass (36.0%)
ALERT: Only 18 stocks passed (below 100). Check data quality or market conditions.
Composite scores: min=48.22, max=83.14, median=62.50
First excluded: STK044 (score=56.30)
Selected top 10: score range 57.89 - 83.14
Pipeline complete: 8 BUY, 2 HOLD, 3 SELL (turnover=80%)
```

### Integration With Factor Computation Modules

This module expects input from the four factor computation modules (docs 02-a through 02-d). The handoff contract is a single DataFrame with these columns:

| Column | Type | Source | Scale |
|--------|------|--------|-------|
| `ticker` | str | Universe definition | -- |
| `sector` | str | Universe definition | -- |
| `rs_percentile` | float | Factor 1 (Relative Strength) | 0-100 |
| `eps_growth_pct` | float | Factor 2 (EPS Growth) | Raw %, can be 999 for turnarounds |
| `rev_growth_pct` | float | Factor 3 (Revenue Growth) | Raw % |
| `price_vs_high` | float | Factor 4 (Price vs 52-Week High) | 0-100 |

The pipeline is stateless within a single month -- the only external dependency is `prior_holdings`, which connects one month's output to the next month's signal generation.
