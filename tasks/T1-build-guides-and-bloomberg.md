# T1: Build Implementation Guides + Bloomberg Data Pull Specs

**Status:** PENDING
**Assigned to:** Terminal 2
**Created:** 2026-02-27

---

## Objective

Review `STRATEGY.md` thoroughly, then produce implementation docs and Bloomberg data extraction specs so the strategy can be rebuilt from scratch.

---

## Subtasks (deploy as parallel agent teams)

### Subtask A: Review STRATEGY.md
- Read the full `STRATEGY.md` file
- Identify every implementable component
- Note any gaps, ambiguities, or missing details that would block a rebuild
- Output a brief review summary before launching the build agents

### Subtask B: Create Implementation Build Guides (docs/)
Deploy agents to create these markdown files in `docs/`:

1. **`docs/01-universe-screening.md`** — How to build the universe screener
   - Exact filters: market cap $50M-$10B, exchanges (NASDAQ/NYSE/NYSE American), min $500K avg daily volume, min $2.00 price
   - Data sources, API calls or database queries needed
   - How to handle delistings and survivorship bias
   - Expected output: ~2,000 stocks

2. **`docs/02-factor-calculations.md`** — How to compute each of the 4 factors
   - RS Percentile: 6-month price momentum, rank against full universe (0-100)
   - EPS Growth YoY: latest quarter vs same quarter 4 periods ago, 999% turnaround scoring for negative→positive transitions
   - Revenue Growth YoY: top-line sales comparison, requires positive revenue base
   - Price vs 52-Week High: current price / max price over trailing 252 trading days
   - Include pseudocode/formulas for each

3. **`docs/03-quality-filters-and-scoring.md`** — Filters + composite score
   - Three quality gates: EPS growth >= 5%, Rev growth >= 5%, Price >= 75% of 52-week high
   - Composite score formula: 0.40 * RS + 0.20 * min(EPS_growth, 100) + 0.20 * min(Rev_growth, 100) + 0.20 * Price_vs_High
   - Ranking, top 25 selection, equal 4% weighting
   - BUY/SELL/HOLD signal generation logic

4. **`docs/04-backtesting-framework.md`** — How to backtest the strategy
   - Monthly rebalancing mechanics
   - Transaction cost modeling (10 bps per trade)
   - Point-in-time data requirements (no look-ahead bias)
   - Performance metric calculations: Sharpe, Sortino, Calmar, Profit Factor, Max Drawdown
   - Subperiod analysis and bootstrap validation approach
   - Tools: VectorBT Pro or custom Python

5. **`docs/05-portfolio-management.md`** — Live portfolio operations
   - Monthly execution timeline (Day 1 market open → Day 1-3 execution → hold)
   - Position sizing: equal 4% weight, trim winners >6%
   - Sector concentration limit: max 40% per sector
   - Max drawdown threshold: -25%
   - Rebalancing mechanics and signal interpretation

### Subtask C: Bloomberg Data Pull Specifications (`docs/06-bloomberg-data-pull.md`)
Deploy an agent to create a complete Bloomberg Terminal data extraction guide:

For EACH data field needed by the strategy, provide:
- **Bloomberg function** (e.g., `BDH`, `BDP`, `BDS`)
- **Exact Excel formula** with Bloomberg field codes
- **2-3 ticker alternatives** if primary doesn't work (e.g., if a field isn't available for a specific ticker, what substitute tickers/fields to try)
- **Date range and frequency** needed

Data fields required:
1. **Price data (OHLCV)** — 15 months daily for 52-week high calc + 6-month RS
2. **Market capitalization** — for universe filtering ($50M-$10B)
3. **Average daily volume** — for liquidity filter ($500K min)
4. **EPS (quarterly)** — last 8 quarters for YoY comparison
5. **Revenue (quarterly)** — last 8 quarters for YoY comparison
6. **Exchange listing** — NASDAQ/NYSE/NYSE American filter
7. **Share price** — current, for $2.00 minimum filter
8. **52-week high** — or derive from 252-day price history

Include:
- How to pull the full small-cap universe from Bloomberg (screening function)
- Excel template structure recommendation
- Refresh/update workflow for monthly rebalancing
- Common Bloomberg gotchas (adjusted vs unadjusted prices, fiscal vs calendar quarters, etc.)

---

## Output Structure

```
docs/
├── 01-universe-screening.md
├── 02-factor-calculations.md
├── 03-quality-filters-and-scoring.md
├── 04-backtesting-framework.md
├── 05-portfolio-management.md
└── 06-bloomberg-data-pull.md
```

---

## Instructions for Terminal 2

1. Read this task file and `STRATEGY.md`
2. Deploy agent teams in parallel for Subtasks B and C
3. Write all output files to `docs/`
4. Mark this task as DONE when complete
