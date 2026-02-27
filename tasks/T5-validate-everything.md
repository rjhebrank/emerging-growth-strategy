# T5: Full Project Validation — Find and Fix All Bugs

**Status:** PENDING
**Assigned to:** Terminal 2
**Created:** 2026-02-27

---

## Objective

Deploy a team of validator agents to audit the ENTIRE project — Python engine, Bloomberg template, docs, and cross-component integration. Find every bug, inconsistency, and issue. Then fix them all.

---

## CRITICAL: Deploy ALL validators as parallel agents. Minimum 6 agents.

---

## Validator 1: Python Engine Code Audit

Read every file in `src/` and validate:

- **Import consistency** — do all modules import each other correctly? No circular imports?
- **Function signatures** — does `main.py` call functions with the right arguments? Do return types match what callers expect?
- **DataFrame column names** — are column names consistent across modules? (e.g., does `data_loader.py` output what `screener.py` expects as input?)
- **Edge cases** — what happens with empty DataFrames, NaN values, zero-division, missing tickers?
- **Filter thresholds** — do they match STRATEGY.md exactly? ($50M-$10B, $500K volume, $2.00 price, 5% EPS, 5% rev, 75% price vs high)
- **Composite formula** — is it exactly 0.40 * RS + 0.20 * min(EPS,100) + 0.20 * min(Rev,100) + 0.20 * PriceVsHigh?
- **Turnaround scoring** — does EPS growth return 999 for negative-to-positive transitions?
- **RS calculation** — is it 126 days (6-month), NOT 252?
- **Signal logic** — BUY = new in top 25, SELL = dropped from top 25, HOLD = stayed?

**Fix all bugs found.** Write fixes directly to the src/ files.

## Validator 2: Bloomberg Template Formula Audit

Read `templates/bloomberg_template.xlsx` using openpyxl and validate every formula:

- **BDS formula** — does A2 on Universe sheet have `=BDS("RTY Index","INDX_MEMBERS")`?
- **BDP formulas** — are field codes correct? `CUR_MKT_CAP`, `EXCH_CODE`, `VOLUME_AVG_20D`, `PX_LAST`
- **BDH formulas** — do Price History BDH calls include `CshAdjNormal","Y","CshAdjAbnormal","Y"` for adjusted prices?
- **BDH date parameters** — are they dynamic (`EDATE(TODAY(),-15)`) not hardcoded dates?
- **Filter formulas** — G: market cap 50-10000, H: exchange NAS/NYS/ASE, I: dollar vol >=500000, J: price >=2, K: AND(G,H,I,J)?
- **Cell references** — do formulas in rows 3-2501 correctly reference their own row? (B3 references A3, B4 references A4, etc.)
- **Price History ticker chaining** — does the ticker input column (I) correctly map to the 320-row-spaced blocks in column A?
- **Fundamentals block spacing** — are blocks 10 rows apart? Do YoY growth formulas compare correct rows (row N vs row N+4)?
- **Factor Scores sheet** — does composite formula match STRATEGY.md weights?
- **Portfolio sheet** — signal formula logic correct? RANK formula correct?
- **Sector BDP** — does it use `GICS_SECTOR_NAME`?

**Fix all formula errors found.** Write the corrected template back.

## Validator 3: Data Flow Integration Test

Trace the COMPLETE data pipeline from Bloomberg template → Python engine:

- **What columns does the Python `data_loader.py` expect from the Excel file?** Read the loader code.
- **What columns does the Bloomberg template actually produce?** Read the template.
- **Do they match?** Column names, sheet names, data types, row layouts?
- **Specifically check:**
  - Does `load_universe()` read from a sheet named exactly what the template uses?
  - Does `load_price_history()` handle the 320-row block layout the template uses?
  - Does `load_fundamentals()` handle the 10-row block layout the template uses?
  - What if the user saves-as-values (static data) vs. leaving formulas?
- **Mock data format** — does `mock_data.py` produce the same format as the Bloomberg template? If not, either the mock data or the loader needs updating so both paths work.

**Fix any mismatches.** Update either the template or the Python code (prefer updating Python to match template since template is what runs on Bloomberg).

## Validator 4: Doc Consistency Audit

Read ALL docs in `docs/` and cross-reference against `STRATEGY.md` and the actual code in `src/`:

- **Do the docs match the code?** If doc 02 says RS uses 126 days, does `src/factors.py` actually use 126?
- **Were T2 fixes actually applied?** Check that the inconsistencies from T2 were resolved:
  - RS lookback: must be 126 days everywhere
  - Universe filters: $50M-$10B, $2.00 min price everywhere
  - Rebalance thresholds: consistent across docs
  - Column naming: consistent
- **Bloomberg guide** — does `docs/06-bloomberg-data-pull.md` match the actual template formulas?
- **Any remaining contradictions between any two docs?**

**Fix any remaining inconsistencies.**

## Validator 5: End-to-End Pipeline Test

Actually run the pipeline and verify correctness:

```bash
cd ~/emerging-growth-strategy
pip install -r requirements.txt
python -m src.main mock --output data/mock_test.xlsx
python -m src.main run --input data/mock_test.xlsx --output reports/validation_test/
```

Then validate the output:
- **Does it run without errors?**
- **Are there exactly 25 stocks in the top 25?** (or fewer if <25 pass quality filters)
- **Are composite scores calculated correctly?** Manually verify 2-3 stocks: take their RS percentile, min(EPS,100), min(Rev,100), price vs high, apply 40/20/20/20 weights, check the score matches.
- **Are quality filters applied correctly?** Verify no stock in top 25 has EPS growth <5%, rev growth <5%, or price vs high <75%.
- **Are signals correct?** First month should be all BUY (no prior month).
- **Do output files exist and have correct content?** Check all files in reports/.

**If any test fails, trace the bug and fix it.**

## Validator 6: Requirements & Project Structure

- **requirements.txt** — are all needed packages listed? (pandas, openpyxl, numpy — anything else?)
- **Imports** — run `python -c "from src import main, data_loader, screener, factors, scoring, portfolio, mock_data"` to verify all modules import cleanly
- **.gitignore** — does it ignore data/, reports/, __pycache__, .venv, *.pyc?
- **README.md** — does it have accurate usage instructions that match actual CLI commands?
- **src/__init__.py** and **src/__main__.py** — do they exist and work?
- **No hardcoded paths** — check all src/ files for hardcoded absolute paths
- **No secrets or credentials** — scan for any API keys, passwords, tokens

**Fix anything broken.**

---

## Output

Each validator agent should:
1. List every issue found (file, line, description)
2. Fix the issue directly in the file
3. Return a summary of all changes made

After all validators complete, do a FINAL end-to-end test run to confirm everything works together.

---

## Instructions for Terminal 2

1. Read this task file
2. Deploy ALL 6 validator agents in PARALLEL
3. After all complete, review their findings
4. Run one final end-to-end test to confirm everything passes
5. Mark task DONE when complete
