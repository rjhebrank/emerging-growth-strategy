# T2: Fix Cross-Doc Inconsistencies + Rewrite Bloomberg Guide for Excel Add-in Only

**Status:** PENDING
**Assigned to:** Terminal 2
**Created:** 2026-02-27

---

## Objective

Two jobs: (A) Fix all cross-document inconsistencies identified in review, and (B) Rewrite the Bloomberg data pull guide to ONLY use the Excel Add-in method (BDH/BDP formulas) for both initial setup and monthly refreshes. No EQS terminal workflow, no BQL/Python — just Excel cell commands.

---

## Subtask A: Fix Cross-Document Inconsistencies

Deploy agents to fix these issues across all docs. The source of truth is `STRATEGY.md`.

### 1. RS Percentile Lookback — Must be 126 days (6 months)
- **Doc 02** (`02-factor-calculations.md`): Already correct (126 days). No change needed.
- **Doc 04** (`04-backtesting-framework.md`): WRONG — says 252 days / 12-month in multiple places. Fix ALL references to 126 days / 6-month.

### 2. Universe Filter Parameters — Must be $50M-$10B market cap, $2.00 min price
- **Doc 01** (`01-universe-screening.md`): Already correct. No change needed.
- **Doc 02** (`02-factor-calculations.md`): Check the appendix quick reference — may say $5 min price. Fix to $2.00.
- **Doc 04** (`04-backtesting-framework.md`): WRONG — Section 2 says $300M-$2B market cap and $5.00 min price. Fix to $50M-$10B and $2.00.

### 3. Rebalance Drift Thresholds — Pick one and apply everywhere
- **Doc 03** (`03-quality-filters-and-scoring.md`): Uses 2% ADD threshold.
- **Doc 05** (`05-portfolio-management.md`): Uses 3.5% ADD threshold.
- **Resolution:** Use 2% as the standard (tighter is more faithful to equal-weight discipline). Update Doc 05 to match.

### 4. Sector Concentration Limit — Add to Doc 03 pipeline
- **Doc 05** describes 40% max per sector but Doc 03's `EmergingGrowthSelector` doesn't enforce it.
- Add sector cap enforcement to the selection logic in Doc 03. After selecting top 25 by score, check sector concentrations. If any sector exceeds 40% (10 of 25 stocks), drop the lowest-scoring stock in that sector and replace with next highest-scoring stock from a different sector.

### 5. Column Naming — Standardize to Sharadar conventions
- Use `close` for split-adjusted close price (Sharadar SEP table convention)
- Fix Doc 04's references from `close_adj` to `close`
- Ensure all docs use consistent column names

---

## Subtask B: Rewrite Bloomberg Guide — Excel Add-in Only

Rewrite `docs/06-bloomberg-data-pull.md` completely. **Delete all EQS terminal workflow and BQL/Python sections.** The ONLY method is Bloomberg Excel Add-in (BDP and BDH formulas pasted into cells).

### Structure the rewrite as:

#### 1. Initial Universe Pull (First Time Setup)
How to get the full list of ~2,000 small-cap stocks using ONLY Excel formulas:
- Use `BDS` to pull index constituents (Russell 2000 or similar) as the starting universe
- Use `BDP` to pull market cap, exchange, avg volume, price for each ticker to apply filters
- Give me the EXACT cell formulas — like "paste this in cell A1", "paste this in B1", etc.
- Show how to filter down to the ~2,000 qualifying stocks

#### 2. Monthly Data Pull (All Fields)
For the filtered universe, give EXACT cell formulas for every data field needed:

**Price Data (BDH):**
- 15 months daily OHLCV for 52-week high and 6-month RS calculation
- Exact BDH formula with all parameters (dates, fields, adjustments)

**Fundamentals (BDP/BDH):**
- Quarterly EPS — last 8 quarters
- Quarterly Revenue — last 8 quarters
- Market cap (current)
- Average daily volume (20-day)
- 52-week high
- Current price
- Exchange listing

For EACH field provide:
- The exact Excel formula to paste (e.g., `=BDH("AAPL US Equity","PX_LAST","1/1/2025","2/27/2026","Days","A","Fill","P")`)
- 2-3 alternative Bloomberg field codes if the primary doesn't return data
- What the output looks like

#### 3. Monthly Refresh Workflow
Step-by-step process using only Excel:
1. Update universe (re-pull index constituents + filters)
2. Refresh price data (just pull latest month, append to existing)
3. Refresh fundamentals (check for new quarterly filings)
4. Which cells to update vs. which to re-pull entirely

#### 4. Excel Template Layout
Recommend exact sheet structure with column headers:
- Sheet 1: Universe (ticker, market cap, exchange, volume, price, pass/fail)
- Sheet 2: Price History (BDH pulls)
- Sheet 3: Fundamentals (quarterly EPS + revenue)
- Sheet 4: Factor Scores (RS percentile, EPS growth, rev growth, price vs high)
- Sheet 5: Composite Scores + Rankings + Signals

#### 5. Bloomberg Gotchas for Excel Add-in
Keep the existing gotchas that apply to Excel method. Remove any EQS/BQL-specific ones. Add any Excel-specific gotchas (refresh limits, formula count limits, array formula behavior, etc.)

### Key Requirements
- Every formula must be copy-pasteable — no pseudocode
- Include the exact Bloomberg field codes (e.g., `PX_LAST`, `CUR_MKT_CAP`, `IS_EPS`, `SALES_REV_TURN`)
- 2-3 alternative field codes per data point in case primary doesn't work
- Show date format Bloomberg expects
- Note any Bloomberg Excel add-in settings that need to be configured

---

## Instructions for Terminal 2

1. Read this task file
2. Read `STRATEGY.md` for canonical values
3. Deploy agents in parallel:
   - Agent team for Subtask A (fix all 5 inconsistencies across docs)
   - Agent team for Subtask B (rewrite Bloomberg guide)
4. Review outputs
5. Update this task status to DONE when complete
