# T3: Build the Python Screening & Scoring Engine

**Status:** PENDING
**Assigned to:** Terminal 2
**Created:** 2026-02-27

---

## Objective

Build the complete Python engine that takes Bloomberg Excel exports as input and produces monthly portfolio picks with BUY/SELL/HOLD signals. The engine must match the strategy spec in `STRATEGY.md` exactly.

**Key constraint:** We do NOT have Bloomberg data yet. Build the engine to read from the Excel template structure defined in `docs/06-bloomberg-data-pull.md`. Also create sample/mock data so the engine can be tested end-to-end without Bloomberg access.

---

## Reference Docs (agents MUST read these)

- `STRATEGY.md` — canonical strategy specification
- `docs/01-universe-screening.md` — universe filter logic
- `docs/02-factor-calculations.md` — factor calculation details
- `docs/03-quality-filters-and-scoring.md` — quality filters, composite score, signal generation
- `docs/05-portfolio-management.md` — position sizing, sector caps, rebalancing
- `docs/06-bloomberg-data-pull.md` — Excel template structure (5 sheets) that defines input format

---

## Bloomberg Excel Template Structure (Input Format)

The engine reads from a 5-sheet Excel workbook exported from Bloomberg:

### Sheet 1: "Universe"
| Column | Header | Content |
|--------|--------|---------|
| A | Ticker | Stock ticker symbol |
| B | Market Cap ($M) | Market cap in millions |
| C | Exchange | Exchange code (NAS/NYS/ASE) |
| D | Avg Volume (20d) | 20-day average daily share volume |
| E | Price | Current share price |
| F | Dollar Volume | D * E (daily dollar volume) |
| G-K | Filter columns | Boolean pass/fail (can be ignored — engine re-applies filters) |

### Sheet 2: "Price History"
- Column A: Ticker (one per block, blocks spaced 320 rows apart)
- Columns B-G: Date, Open, High, Low, Close, Volume (BDH output, ~315 rows per ticker)

### Sheet 3: "Fundamentals"
- Column A: Ticker (one per block, blocks spaced 10 rows apart)
- Columns B-C: Date, EPS (8 quarters from BDH)
- Columns J-K: Date, Revenue (8 quarters from BDH)

### Sheet 4: "Factor Scores" (optional — engine can recompute)
### Sheet 5: "Composite + Rankings" (optional — engine produces this)

---

## Subtasks (deploy as parallel agent teams)

### Agent 1: Data Ingestion Module — `src/data_loader.py`

Build a module that reads the Bloomberg Excel workbook and returns clean DataFrames.

**Functions needed:**
- `load_universe(filepath) -> pd.DataFrame` — Read Sheet 1 ("Universe"), return DataFrame with columns: ticker, market_cap, exchange, avg_volume, price, dollar_volume
- `load_price_history(filepath) -> dict[str, pd.DataFrame]` — Read Sheet 2 ("Price History"), parse the block layout (tickers every 320 rows), return dict mapping ticker -> DataFrame with columns: date, open, high, low, close, volume
- `load_fundamentals(filepath) -> dict[str, dict]` — Read Sheet 3 ("Fundamentals"), parse the block layout (tickers every 10 rows), return dict mapping ticker -> {"eps": DataFrame(date, eps), "revenue": DataFrame(date, revenue)}

**Edge cases to handle:**
- #N/A values from Bloomberg (treat as NaN, skip ticker for that field)
- Missing tickers (some tickers in universe may not have price/fundamental data)
- Variable row counts per block (some tickers may have fewer than 315 price rows or fewer than 8 quarters)

**Also create:** `src/mock_data.py` — generates a realistic mock Excel workbook with ~100 fake tickers, 15 months of random price data, and 8 quarters of fake EPS/revenue. This lets us test end-to-end without Bloomberg. Use `openpyxl` to write the Excel file.

### Agent 2: Universe Screener — `src/screener.py`

**Function:** `screen_universe(universe_df: pd.DataFrame) -> pd.DataFrame`

Apply all universe filters and return qualifying tickers:
- Market cap: $50M <= cap <= $10B (Bloomberg reports in millions, so 50 <= cap <= 10000)
- Exchange: must be in ["NAS", "NYS", "ASE"]
- Dollar volume: >= $500,000
- Price: >= $2.00

Return filtered DataFrame. Log how many tickers pass each filter stage.

### Agent 3: Factor Calculator — `src/factors.py`

Build functions to compute each of the 4 factors from raw data:

1. **`calc_rs_percentile(price_data: dict[str, pd.DataFrame], tickers: list[str]) -> pd.Series`**
   - For each ticker: 6-month (126 trading day) price return = (close_today / close_126_days_ago) - 1
   - Rank all tickers cross-sectionally on 0-100 percentile scale
   - Return Series: ticker -> RS percentile (0-100)

2. **`calc_eps_growth(fundamentals: dict[str, dict], tickers: list[str]) -> pd.Series`**
   - Compare most recent quarter EPS to same quarter 4 periods ago (YoY)
   - Turnaround scoring: if prior EPS <= 0 and current EPS > 0, return 999.0
   - Both negative: return 0.0
   - Normal: (current - prior) / abs(prior) * 100
   - Return Series: ticker -> EPS growth %

3. **`calc_revenue_growth(fundamentals: dict[str, dict], tickers: list[str]) -> pd.Series`**
   - Compare most recent quarter revenue to same quarter 4 periods ago (YoY)
   - Requires positive revenue base. If prior revenue <= 0 and current > 0, return 999.0
   - Normal: (current - prior) / prior * 100
   - Return Series: ticker -> Revenue growth %

4. **`calc_price_vs_high(price_data: dict[str, pd.DataFrame], tickers: list[str]) -> pd.Series`**
   - Current price / max price over trailing 252 trading days * 100
   - Return Series: ticker -> percentage (0-100)

### Agent 4: Scoring & Signal Engine — `src/scoring.py`

**Functions needed:**

1. **`apply_quality_filters(eps_growth, rev_growth, price_vs_high) -> list[str]`**
   - EPS growth >= 5%
   - Revenue growth >= 5%
   - Price vs 52-week high >= 75%
   - ALL three must pass. Return list of qualifying tickers.

2. **`calc_composite_score(rs, eps, rev, pvh, qualified_tickers) -> pd.DataFrame`**
   - Formula: 0.40 * RS_percentile + 0.20 * min(eps_growth, 100) + 0.20 * min(rev_growth, 100) + 0.20 * price_vs_high
   - Return DataFrame with columns: ticker, composite_score, rs_percentile, eps_growth, rev_growth, price_vs_high, rank

3. **`enforce_sector_cap(ranked_df, sector_data, max_pct=0.40) -> pd.DataFrame`**
   - If any sector has more than 40% of top 25 (i.e., >10 stocks), drop lowest-scoring in that sector, replace with next highest-scoring from another sector
   - Note: sector data may not be in Bloomberg export initially. Make this optional — skip if sector column not available.

4. **`generate_signals(current_top25: list[str], prior_top25: list[str]) -> pd.DataFrame`**
   - BUY: in current but not in prior
   - SELL: in prior but not in current
   - HOLD: in both
   - Return DataFrame: ticker, signal, current_rank, prior_rank

### Agent 5: Main Pipeline & CLI — `src/main.py` + `src/portfolio.py`

**`src/portfolio.py`:**
- `build_portfolio(top25: pd.DataFrame) -> pd.DataFrame` — assign equal 4% weights to top 25
- `calc_rebalance_trades(current_weights, target_weights, portfolio_value) -> pd.DataFrame` — compute trade list with dollar amounts and share counts

**`src/main.py`:**
- CLI entry point using `argparse`
- Commands:
  - `python -m src.main run --input data/bloomberg_export.xlsx --prior data/prior_month.xlsx --output reports/` — full monthly pipeline
  - `python -m src.main mock --output data/mock_data.xlsx` — generate mock data for testing
- Full pipeline: load data → screen universe → calculate factors → apply filters → score → rank → enforce sector cap → generate signals → output report
- Output: CSV report with all tickers, scores, ranks, signals + summary to stdout

**`requirements.txt`:**
- pandas
- openpyxl
- numpy

### Agent 6: Project Setup Files

Create:
- `requirements.txt` — minimal deps (pandas, openpyxl, numpy)
- `src/__init__.py` — empty
- `.gitignore` — ignore data/*.xlsx, reports/, __pycache__, .venv, *.pyc
- `README.md` — brief usage instructions (how to generate mock data, how to run monthly pipeline)

---

## Output Structure

```
emerging-growth-strategy/
├── src/
│   ├── __init__.py
│   ├── main.py          # CLI entry point
│   ├── data_loader.py   # Bloomberg Excel ingestion
│   ├── mock_data.py     # Mock data generator
│   ├── screener.py      # Universe filtering
│   ├── factors.py       # 4 factor calculations
│   ├── scoring.py       # Quality filters, composite score, signals
│   └── portfolio.py     # Position sizing, rebalancing
├── data/                # Bloomberg exports go here (gitignored)
├── reports/             # Output reports go here (gitignored)
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Testing

After building everything, run:
```bash
cd ~/emerging-growth-strategy
pip install -r requirements.txt
python -m src.main mock --output data/mock_data.xlsx
python -m src.main run --input data/mock_data.xlsx --output reports/
```

This should produce a complete report from mock data. If it errors, fix it before marking the task DONE.

---

## Instructions for Terminal 2

1. Read this task file + all reference docs listed above
2. Deploy 6 agents in parallel (one per subtask)
3. Review all outputs, ensure imports are consistent across modules
4. Run the mock data test to verify end-to-end
5. Update this task status to DONE when complete
