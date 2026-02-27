# 06 — Bloomberg Excel Add-in Data Pull

## 1. Overview

**Purpose:** Pull all data required by the Emerging Growth Strategy using ONLY the Bloomberg Excel Add-in. No terminal commands, no EQS screens, no BQL, no Python.

**Functions used:**

| Function | What It Does | Example |
|----------|-------------|---------|
| **BDP** | Single current data point for one security | `=BDP("AAPL US Equity","PX_LAST")` |
| **BDH** | Historical time series (daily, weekly, quarterly) | `=BDH("AAPL US Equity","PX_LAST","1/1/2025","2/27/2026")` |
| **BDS** | Bulk data set (e.g., index members, fund holdings) | `=BDS("RTY Index","INDX_MEMBERS")` |

**Data required for ~2,000 US small-cap stocks ($50M--$10B market cap):**

| # | Data Field | Use in Strategy |
|---|-----------|-----------------|
| 1 | Price data (OHLCV) -- 15 months daily | 52-week high + 6-month relative strength |
| 2 | Market capitalization | Universe filter ($50M--$10B) |
| 3 | Average daily dollar volume | Liquidity filter ($500K minimum) |
| 4 | EPS (quarterly) -- last 8 quarters | YoY EPS growth for composite score |
| 5 | Revenue (quarterly) -- last 8 quarters | YoY revenue growth for composite score |
| 6 | Exchange listing | NASDAQ / NYSE / NYSE American filter |
| 7 | Current share price | $2.00 minimum price filter |
| 8 | 52-week high | Price vs. 52-week high for composite score |

---

## 2. Initial Universe Pull (First Time Setup)

How to get ~2,000 small-cap stocks using only Excel formulas. Open a blank Excel workbook with the Bloomberg Add-in active.

### Step 1: Pull Index Constituents as Starting Universe

Paste this in cell **A1** on Sheet 1 ("Universe"):

```
=BDS("RTY Index","INDX_MEMBERS")
```

This spills ~2,000 Russell 2000 tickers down column A. Each cell will contain a ticker symbol (e.g., "ACAD", "AAON", "ABCB").

**Alternative** if `RTY Index` does not return results:

```
=BDS("IWM US Equity","FUND_HOLDINGS")
```

This pulls the iShares Russell 2000 ETF holdings instead. Note: ETF holdings may lag index changes by a few days.

Leave at least 2,500 empty rows below A1 for the array to spill into.

### Step 2: Add Screening Data for Each Ticker

Once column A is populated with tickers, paste the following formulas in row 1 of columns B through F. Then drag each formula down to match the last row of tickers in column A.

**Cell B1** -- Market Cap (millions USD):
```
=BDP(A1 & " US Equity","CUR_MKT_CAP")
```

**Cell C1** -- Exchange Code:
```
=BDP(A1 & " US Equity","EXCH_CODE")
```

**Cell D1** -- 20-Day Average Volume (shares):
```
=BDP(A1 & " US Equity","VOLUME_AVG_20D")
```

**Cell E1** -- Current Price (unadjusted):
```
=BDP(A1 & " US Equity","PX_LAST")
```

**Cell F1** -- Dollar Volume (calculated, no Bloomberg call):
```
=D1*E1
```

Drag B1:F1 down to match the last ticker row.

### Step 3: Filter Columns (Pass/Fail for Each Criterion)

Paste the following Boolean formulas starting in row 1, then drag down:

**Cell G1** -- Market cap pass ($50M to $10B; Bloomberg returns millions):
```
=AND(B1>=50,B1<=10000)
```

**Cell H1** -- Exchange pass (NASDAQ, NYSE, or NYSE American):
```
=OR(C1="NAS",C1="NYS",C1="ASE")
```

**Cell I1** -- Dollar volume pass ($500K minimum daily):
```
=F1>=500000
```

**Cell J1** -- Price pass ($2.00 minimum):
```
=E1>=2
```

**Cell K1** -- ALL filters pass (master filter):
```
=AND(G1,H1,I1,J1)
```

Drag G1:K1 down. Filter column K to TRUE to get the qualifying universe. Copy those tickers to the other sheets for data pulls.

---

## 3. Monthly Data Pull (All Fields)

For each filtered ticker in the universe, use the formulas below. In these examples, the ticker is referenced from cell A1. Adjust cell references as needed for your layout.

### Price Data (15 Months Daily OHLCV)

```
=BDH(A1 & " US Equity","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","1/1/2025","2/27/2026","Days","A","Fill","P","CshAdjNormal","Y","CshAdjAbnormal","Y")
```

**Parameter breakdown:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Security | `A1 & " US Equity"` | Ticker from universe sheet with Bloomberg yellow key |
| Fields | `"PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME"` | Open, High, Low, Close, Volume -- comma-separated in one string |
| Start Date | `"1/1/2025"` | 15 months before today (update monthly) |
| End Date | `"2/27/2026"` | Today's date (update monthly) |
| `"Days","A"` | Actual trading days | Excludes weekends/holidays |
| `"Fill","P"` | Previous value fill | Fills gaps from halts/holidays with last known price |
| `"CshAdjNormal","Y"` | Adjust for regular dividends | Ensures RS calc reflects total return |
| `"CshAdjAbnormal","Y"` | Adjust for splits and special dividends | Prevents false 52-week highs from pre-split prices |

The formula returns 6 columns (Date, Open, High, Low, Close, Volume) and ~315 rows (trading days). Leave enough empty space below and to the right.

**Use adjusted prices** (`CshAdjNormal=Y`, `CshAdjAbnormal=Y`) for relative strength and 52-week high calculations. Use unadjusted `PX_LAST` from BDP (not BDH) for the $2.00 price filter.

**Dynamic date version** (auto-updates, no manual date edits needed):
```
=BDH(A1 & " US Equity","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME",TEXT(EDATE(TODAY(),-15),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days","A","Fill","P","CshAdjNormal","Y","CshAdjAbnormal","Y")
```

**Alternative fields if primary fails:**

| Situation | Try Instead |
|-----------|-------------|
| `PX_LAST` returns #N/A | `LAST_PRICE` or `PX_CLOSE_1D` |
| Need unadjusted prices | Omit the `CshAdjNormal` and `CshAdjAbnormal` parameters |
| Need total-return index | `TOT_RETURN_INDEX_GROSS_DVDS` instead of `PX_LAST` |

---

### Quarterly EPS (Last 8 Quarters)

```
=BDH(A1 & " US Equity","IS_DILUTED_EPS","1/1/2024","2/27/2026","Per","Q","Days","A","Fill","P")
```

**Parameter breakdown:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| Field | `IS_DILUTED_EPS` | Diluted earnings per share, as reported quarterly |
| Start Date | `"1/1/2024"` | ~2 years back to capture 8 fiscal quarters |
| End Date | `"2/27/2026"` | Today |
| `"Per","Q"` | Quarterly periodicity | Returns one value per fiscal quarter |
| `"Days","A"` | Actual | Aligns to fiscal period end dates |
| `"Fill","P"` | Previous fill | Fills gaps if a quarter is delayed |

Returns 2 columns (Date, EPS) and up to 8 rows (one per fiscal quarter).

**Alternative fields:**

| Alternative | When to Use |
|-------------|------------|
| `IS_EPS` | Basic (undiluted) EPS -- use if diluted not available |
| `TRAIL_12M_DILUTED_EPS` | Trailing 12-month EPS -- use only if quarterly breakout unavailable |
| `IS_OPER_INC` / shares outstanding | Operating EPS -- excludes one-time charges |

**Gotcha -- Fiscal vs. Calendar Quarters:** Bloomberg reports EPS on the company's fiscal year basis. A company with a January fiscal year-end has Q1 = Feb--Apr, not Jan--Mar. When computing YoY growth, always compare the same fiscal quarter (row N vs. row N+4 in the BDH output). Bloomberg's `Per=Q` handles this automatically -- just make sure you compare Q to Q-4, not calendar-aligned quarters.

---

### Quarterly Revenue (Last 8 Quarters)

```
=BDH(A1 & " US Equity","SALES_REV_TURN","1/1/2024","2/27/2026","Per","Q","Days","A","Fill","P")
```

**Primary field:** `SALES_REV_TURN` (total revenue / net sales / turnover).

Returns 2 columns (Date, Revenue) and up to 8 rows.

**Alternative fields:**

| Alternative | When to Use |
|-------------|------------|
| `IS_COMP_SALES` | Comparable / reported sales (may differ for some sectors) |
| `TOTAL_REVENUE` | May include non-operating revenue -- use with caution |
| `NET_REV` | Net revenue after returns/allowances |

**Gotcha -- Revenue Units:** Bloomberg typically reports revenue in millions for US equities, but units vary by company. A revenue figure of "50" could be $50M or $50K depending on the company's reporting scale. Check individual tickers that look suspicious. Use `=BDP(A1 & " US Equity","SCALING_FACTOR")` to verify.

---

### Market Cap (Current)

```
=BDP(A1 & " US Equity","CUR_MKT_CAP")
```

Returns market cap in millions USD.

**Alternative 1** -- Calculate from shares outstanding and price:
```
=BDP(A1 & " US Equity","EQY_SH_OUT") * BDP(A1 & " US Equity","PX_LAST")
```

**Alternative 2** -- Historical point-in-time market cap:
```
=BDP(A1 & " US Equity","HISTORICAL_MARKET_CAP")
```

---

### Average Daily Volume (20-Day)

```
=BDP(A1 & " US Equity","VOLUME_AVG_20D")
```

Returns 20-day average daily share volume.

**Alternative:** `VOLUME_AVG_30D` (30-day average, smoother).

**Remember:** This is share volume, not dollar volume. Multiply by price for dollar volume:
```
=BDP(A1 & " US Equity","VOLUME_AVG_20D") * BDP(A1 & " US Equity","PX_LAST")
```

Or if price is already in another cell (e.g., E1):
```
=BDP(A1 & " US Equity","VOLUME_AVG_20D") * E1
```

---

### 52-Week High

```
=BDP(A1 & " US Equity","HIGH_52WEEK")
```

**Alternative** -- Derive from BDH price history (more precise, uses your adjustment method):
```
=MAX(BDH(A1 & " US Equity","PX_LAST",TEXT(TODAY()-365,"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days","A","CshAdjNormal","Y","CshAdjAbnormal","Y"))
```

**Price vs. 52-Week High percentage** (used in composite score):
```
=BDP(A1 & " US Equity","PX_LAST") / BDP(A1 & " US Equity","HIGH_52WEEK") * 100
```

Or using cell references (more efficient, fewer Bloomberg calls):
```
=E1/L1*100
```

Where E1 = current price and L1 = 52-week high.

---

### Current Price

```
=BDP(A1 & " US Equity","PX_LAST")
```

**Alternative 1:** `LAST_PRICE` (real-time last traded price during market hours)

**Alternative 2:** `PX_CLOSE_1D` (previous trading day's official close -- use this for consistency if running screens during market hours)

---

### Exchange Listing

```
=BDP(A1 & " US Equity","EXCH_CODE")
```

**Expected return values:**

| Code | Exchange |
|------|----------|
| `NAS` | NASDAQ (all tiers) |
| `NYS` | New York Stock Exchange |
| `ASE` | NYSE American (formerly AMEX) |

**Alternative 1:** `ID_MIC_PRIM_EXCH` -- returns ISO MIC codes: XNAS, XNYS, XASE

**Alternative 2:** `EQY_PRIM_EXCH` -- returns full text: "NASDAQ", "New York", etc.

---

## 4. Monthly Refresh Workflow (Excel Only)

Execute on the **first trading day of each month**:

1. **Open the workbook.** Ensure the Bloomberg Excel Add-in is loaded (you should see a Bloomberg ribbon tab). If not, restart Excel with the Bloomberg Terminal open.

2. **Update date ranges in BDH formulas.** If using hardcoded dates, change the end date to today's date and the start date to 15 months prior (price data) or 24 months prior (fundamentals). If using dynamic dates (`EDATE(TODAY(),-15)` and `TODAY()`), skip this step.

3. **Refresh all Bloomberg links.** Use one of these methods:
   - Keyboard: `Ctrl+Shift+R`
   - Bloomberg ribbon: click **Refresh Workbook**
   - Right-click any Bloomberg formula cell: **Bloomberg > Refresh Selected**

4. **Wait for data population.** 2,000 tickers across multiple fields takes approximately 5--10 minutes. Watch the Bloomberg status bar in the lower-left corner of Excel. Do NOT edit cells or switch sheets while refreshing.

5. **Check for #N/A errors.** Use these verification formulas:
   ```
   =COUNTIF(B:B,"#N/A")
   ```
   If more than 10% of a column shows #N/A, there may be a connectivity issue. Try refreshing again. For individual #N/A tickers, try the alternative field codes listed in Section 3.

6. **Re-run universe filter.** Some stocks may have fallen below market cap, price, or volume thresholds since last month. Check column K (All Pass) for any tickers that flipped from TRUE to FALSE. Remove them from the portfolio sheets.

7. **Factor calculations auto-update** if formulas reference live Bloomberg data. Verify RS percentiles, EPS growth, revenue growth, and price-vs-high ratios look reasonable.

8. **Save a dated snapshot:**
   ```
   File > Save As > Strategy_2026-03-01.xlsx
   ```
   Always keep prior months' files -- they provide the "last month's top 25" for signal generation.

---

## 5. Excel Template Layout

Five-sheet workbook. Every formula below is copy-pasteable.

### Sheet 1: Universe

| Col | Header | Cell 1 Formula | Notes |
|-----|--------|----------------|-------|
| A | Ticker | `=BDS("RTY Index","INDX_MEMBERS")` | Paste in A1; spills ~2,000 rows |
| B | Market Cap ($M) | `=BDP(A1 & " US Equity","CUR_MKT_CAP")` | Paste in B1; drag down |
| C | Exchange | `=BDP(A1 & " US Equity","EXCH_CODE")` | Paste in C1; drag down |
| D | Avg Volume (20d) | `=BDP(A1 & " US Equity","VOLUME_AVG_20D")` | Paste in D1; drag down |
| E | Price | `=BDP(A1 & " US Equity","PX_LAST")` | Paste in E1; drag down |
| F | Dollar Volume | `=D1*E1` | Paste in F1; drag down |
| G | Mkt Cap Pass | `=AND(B1>=50,B1<=10000)` | Paste in G1; drag down |
| H | Exchange Pass | `=OR(C1="NAS",C1="NYS",C1="ASE")` | Paste in H1; drag down |
| I | DolVol Pass | `=F1>=500000` | Paste in I1; drag down |
| J | Price Pass | `=E1>=2` | Paste in J1; drag down |
| K | All Pass | `=AND(G1,H1,I1,J1)` | Paste in K1; drag down |

Filter column K to TRUE. Copy qualifying tickers to the other sheets.

---

### Sheet 2: Price History

One BDH pull per qualifying ticker. Place filtered tickers in column A, then put the BDH formula in column B.

**Cell A1:** First qualifying ticker (e.g., paste or link from Universe sheet).

**Cell B1:**
```
=BDH(A1 & " US Equity","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","1/1/2025","2/27/2026","Days","A","Fill","P","CshAdjNormal","Y","CshAdjAbnormal","Y")
```

This spills 6 columns (Date, Open, High, Low, Close, Volume) and ~315 rows per ticker.

**Layout option:** Place each ticker's BDH block 320 rows apart vertically. Ticker 1 in B1, Ticker 2 in B321, Ticker 3 in B641, etc. Put the ticker reference in the A column of each block's starting row.

**Alternative layout:** Use separate columns per ticker. Ticker 1's BDH in B1, Ticker 2's BDH in H1, etc. (each BDH occupies 6 columns).

Pull in batches of 50--100 tickers to avoid Bloomberg request limits. Refresh one batch, wait for completion, then start the next.

---

### Sheet 3: Fundamentals

Place qualifying tickers in column A. For each ticker, pull EPS and Revenue.

| Col | Header | Cell 1 Formula |
|-----|--------|----------------|
| A | Ticker | *(linked from Universe sheet)* |
| B | EPS (8Q) | `=BDH(A1 & " US Equity","IS_DILUTED_EPS","1/1/2024","2/27/2026","Per","Q","Days","A","Fill","P")` |
| J | Revenue (8Q) | `=BDH(A1 & " US Equity","SALES_REV_TURN","1/1/2024","2/27/2026","Per","Q","Days","A","Fill","P")` |

Each BDH spills 2 columns (Date, Value) and up to 8 rows. Leave columns B--I for EPS data and J--Q for Revenue data. Space ticker blocks 10 rows apart vertically.

**EPS YoY Growth** (paste in column R, same row as each ticker's EPS block):

Assuming most recent quarter EPS is in cell C1 and same-quarter-last-year EPS is in cell C5:
```
=IF(C5<=0,IF(C1>0,999,IF(C1=0,0,"")),(C1-C5)/ABS(C5)*100)
```

Turnaround scoring: if prior EPS is zero or negative and current EPS is positive, assigns 999% (sentinel value that gets capped to 100 in composite scoring). If both are non-positive, returns 0 or blank.

**Revenue YoY Growth** (paste in column S):

Assuming most recent quarter revenue is in cell K1 and same-quarter-last-year revenue is in cell K5:
```
=IF(K5<=0,"",(K1-K5)/K5*100)
```

Note: Unlike EPS, revenue does NOT get turnaround scoring (999). If prior-period revenue is zero or negative, the cell is left blank (excluded). Pre-revenue companies are outside the strategy's scope per the specification.

---

### Sheet 4: Factor Scores

Place qualifying tickers in column A. Compute all four factors used in the composite score.

| Col | Header | Cell 1 Formula | Notes |
|-----|--------|----------------|-------|
| A | Ticker | *(linked from Universe sheet)* | |
| B | 6-Mo Return (%) | `=(CurrentClose-Close126DaysAgo)/Close126DaysAgo*100` | Reference cells from Sheet 2 price history. CurrentClose = most recent PX_LAST; Close126DaysAgo = PX_LAST from 126 trading days prior. |
| C | RS Percentile | `=PERCENTRANK.INC($B$1:$B$2000,B1)*100` | Cross-sectional rank across all qualifying tickers |
| D | EPS Growth YoY (capped) | `=MIN(Fundamentals!R1,100)` | Cap at 100 for composite score |
| E | Rev Growth YoY (capped) | `=MIN(Fundamentals!S1,100)` | Cap at 100 for composite score |
| F | Price vs 52-Wk High (%) | `=Universe!E1/BDP(A1 & " US Equity","HIGH_52WEEK")*100` | Or reference a 52-week high column if already pulled |

Drag all formulas down to cover all qualifying tickers.

---

### Sheet 5: Composite + Rankings + Signals

This sheet combines everything into the final output.

| Col | Header | Cell 1 Formula | Notes |
|-----|--------|----------------|-------|
| A | Ticker | *(linked from Universe sheet)* | |
| B | Composite Score | `=0.40*FactorScores!C1 + 0.20*FactorScores!D1 + 0.20*FactorScores!E1 + 0.20*FactorScores!F1` | Weighted: 40% RS + 20% EPS + 20% Rev + 20% Price/High |
| C | Rank | `=RANK(B1,$B$1:$B$2000,0)` | Rank 1 = highest composite score |
| D | In Top 25 | `=C1<=25` | TRUE if this ticker makes the cut |
| E | Prior Month Rank | *(manually paste from prior month's file)* | |
| F | Signal | `=IF(AND(D1=TRUE,E1=""),"BUY",IF(AND(D1=FALSE,E1<>""),"SELL",IF(AND(D1=TRUE,E1<>""),"HOLD","")))` | |

**Signal logic:**
- **BUY:** In this month's top 25 but NOT in last month's top 25
- **SELL:** In last month's top 25 but NOT in this month's top 25
- **HOLD:** In both months' top 25
- Blank: Not in either month's top 25

Sort by column C ascending. The top 25 rows are the portfolio for this month.

---

## 6. Bloomberg Excel Add-in Gotchas

1. **Adjusted vs. Unadjusted Prices.** Bloomberg returns unadjusted prices by default. You MUST add `"CshAdjNormal","Y","CshAdjAbnormal","Y"` as parameters to BDH for adjusted prices. Use adjusted prices for the RS calculation and 52-week high derivation. Use unadjusted `PX_LAST` from BDP (no extra parameters) for the $2.00 price filter.

2. **Fiscal vs. Calendar Quarters.** Companies have different fiscal year-ends. Bloomberg's `Per=Q` returns data aligned to each company's fiscal quarters. When computing YoY EPS or Revenue growth, compare row N to row N+4 in the BDH output (same fiscal quarter, one year apart). Do NOT try to calendar-align quarters across companies.

3. **Data Request Limits.** The Bloomberg Excel Add-in limits concurrent BDH requests. Pull data in batches of 50--100 tickers. Too many simultaneous requests will cause timeouts, partial data, or #N/A errors. Refresh one batch, wait for it to complete, then start the next.

4. **Refresh Time.** 2,000 tickers across multiple fields takes 5--10 minutes for a full refresh. Do NOT edit cells, switch sheets, or interact with the workbook while Bloomberg is populating data.

5. **#N/A Errors.** The field is not available for that specific ticker. Try the alternative field codes listed in Section 3. Common causes: pre-revenue companies (no `SALES_REV_TURN`), recently IPO'd stocks (no `HIGH_52WEEK`), delisted tickers.

6. **Date Format.** Bloomberg Excel expects **MM/DD/YYYY** format (e.g., `"1/1/2025"` or `"02/27/2026"`). Other date formats (DD/MM/YYYY, YYYY-MM-DD) may cause errors or return wrong data silently.

7. **Array Spill.** BDH and BDS return arrays that spill downward (and rightward for multi-field BDH). Leave enough empty rows below BDS formulas (~2,500 for Russell 2000) and enough empty rows + columns below/right of BDH formulas (~320 rows x 6 columns per ticker).

8. **Stale Fundamental Data.** Small-cap companies may not update financials promptly. Check data freshness with:
   ```
   =BDP(A1 & " US Equity","LATEST_PERIOD_END_DT_FULL_RECORD")
   ```
   If the most recent period end is more than 6 months old, flag the ticker for manual review.

9. **Formula Count / Performance.** Excel may slow significantly with more than 10,000 Bloomberg formulas. Minimize live BDP calls by pulling data once and pasting values where possible. Use helper sheets for intermediate calculations. Consider splitting into multiple workbooks if performance degrades.

10. **Bloomberg Add-in Must Be Active.** Ensure the Bloomberg Excel Add-in is loaded: **File > Options > Add-ins > Manage COM Add-ins > Go** and check "Bloomberg Excel Tools". If formulas show `#NAME?`, restart Excel with the Bloomberg Terminal open. The terminal must be running for the add-in to connect.

---

## 7. Troubleshooting

### #N/A Errors

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| #N/A for all fields on a ticker | Ticker format wrong | Ensure Bloomberg receives `"TICKER US Equity"` -- the `& " US Equity"` suffix is required |
| #N/A for `IS_DILUTED_EPS` | Company does not report diluted EPS | Try `IS_EPS` (basic EPS) or `TRAIL_12M_DILUTED_EPS` |
| #N/A for `SALES_REV_TURN` | Pre-revenue company or different field name | Try `IS_COMP_SALES` or `TOTAL_REVENUE` |
| #N/A for `HIGH_52WEEK` | Recently IPO'd (less than 52 weeks of history) | Derive from available history: `=MAX(BDH(A1 & " US Equity","PX_LAST","IPO_date","2/27/2026","Days","A"))` |
| #N/A for `CUR_MKT_CAP` | Delisted or OTC security | Check `=BDP(A1 & " US Equity","MARKET_STATUS")` -- should return "ACTV". Remove if not. |

### #NAME? Errors

The Bloomberg Excel Add-in is not loaded. Fix:

1. Close Excel completely.
2. Ensure the Bloomberg Terminal is running.
3. Reopen Excel -- the Bloomberg Add-in should auto-load.
4. If not: **File > Options > Add-ins > Manage COM Add-ins > Go** > check "Bloomberg Excel Tools".
5. Restart Excel again after enabling the add-in.

### Slow Refresh

- **Reduce batch size:** Pull 25--50 tickers at a time instead of 100.
- **Fewer fields per BDH:** Split OHLCV into separate pulls if needed.
- **Off-peak hours:** Bloomberg servers are less loaded before 7 AM ET and after 6 PM ET.
- **Check your connection:** If refresh is unusually slow, the Bloomberg Terminal session may have timed out. Re-login.

### Missing Quarters in Fundamentals

- Some companies report semi-annually (common for foreign filers even if US-listed).
- Check reporting frequency: `=BDP(A1 & " US Equity","ANNOUNCEMENT_FREQUENCY")` -- should return "Quarterly" for US companies.
- If a company returns only 4 data points instead of 8 for the 2-year window, it is likely semi-annual. Either exclude from growth calculations or interpolate.

### Data Mismatch vs. Sharadar

If Bloomberg and Sharadar data disagree:

- **Price data:** Minor differences are normal due to different adjustment methodologies. Both should be split-adjusted.
- **Fundamentals:** Check reporting date -- Sharadar uses filing date (`datekey`) while Bloomberg uses fiscal period end date. Timing differences of 1--5 days are common.
- **Market cap:** Small differences (<5%) are normal due to different calculation methods.
- **Resolution:** Bloomberg is the authoritative source for live trading decisions. Use Sharadar for backtesting where longer history and easier programmatic access matter more.
