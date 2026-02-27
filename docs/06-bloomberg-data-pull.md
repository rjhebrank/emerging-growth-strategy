# 06 — Bloomberg Terminal Data Extraction Guide

## 1. Overview

This document provides step-by-step instructions for pulling all data required by the Emerging Growth Strategy directly from a Bloomberg Terminal. It covers universe screening, historical price data, fundamental data (EPS and revenue), and the construction of an Excel workbook that calculates the composite score and generates monthly signals.

**Purpose:** Extract the following for ~2,000 US small-cap stocks ($50M--$10B market cap):

| # | Data Field | Use in Strategy |
|---|-----------|-----------------|
| 1 | Price data (OHLCV) — 15 months daily | 52-week high calculation + 6-month relative strength |
| 2 | Market capitalization | Universe filter ($50M--$10B) |
| 3 | Average daily dollar volume | Liquidity filter ($500K minimum) |
| 4 | EPS (quarterly) — last 8 quarters | YoY EPS growth for composite score |
| 5 | Revenue (quarterly) — last 8 quarters | YoY revenue growth for composite score |
| 6 | Exchange listing | NASDAQ / NYSE / NYSE American filter |
| 7 | Current share price | $2.00 minimum price filter |
| 8 | 52-week high | Price vs. 52-week high for composite score |

**Bloomberg functions used throughout:**

- **BDP** (Bloomberg Data Point) — single current data point for one security
- **BDH** (Bloomberg Data History) — time series of historical data
- **BDS** (Bloomberg Data Set) — bulk/tabular data (e.g., index members)
- **EQS** (Equity Screening) — build and run custom screens on the terminal

This guide is an alternative and complement to the Sharadar database approach described in prior documents. Bloomberg is authoritative for point-in-time screening and is particularly useful for validating Sharadar-derived signals before execution.

---

## 2. Universe Screening via Bloomberg

### 2.1 Bloomberg EQS (Equity Screening) — Terminal Workflow

Open the EQS function on the Bloomberg Terminal:

```
EQS <GO>
```

Build a new screen with the following criteria:

| Criterion | Bloomberg Field | Operator | Value |
|-----------|----------------|----------|-------|
| Market Cap | `CUR_MKT_CAP` | BETWEEN | 50 AND 10000 (millions USD) |
| Exchange | `EXCH_CODE` | IN | NAS, NYS, ASE |
| Avg Daily Dollar Volume | `VOLUME_AVG_20D * PX_LAST` | >= | 500000 |
| Share Price | `PX_LAST` | >= | 2.00 |

Step-by-step:

1. Type `EQS <GO>` and press Enter.
2. Click **Create New Screen**.
3. Under **Add Criteria**, search for `CUR_MKT_CAP`. Set operator to "Between", enter 50 and 10000.
4. Add another criterion: search for `EXCH_CODE`. Set operator to "One Of", select NAS, NYS, ASE.
5. Add another criterion: search for `PX_LAST`. Set operator to "Greater Than or Equal", enter 2.
6. For the dollar volume filter, Bloomberg EQS may not support inline multiplication. Instead:
   - Add `VOLUME_AVG_20D` >= 50000 as a rough pre-filter (50K shares/day at $10 = $500K).
   - Apply the exact dollar-volume filter in Excel after export (see Section 2.3).
7. Click **Run Screen**.
8. Review results (expect 1,500--2,500 tickers depending on market conditions).
9. Click **Actions** > **Export to Excel** to download the ticker list.
10. Save the screen for monthly reuse: **Actions** > **Save Screen As** > name it `EMERGING_GROWTH_UNIVERSE`.

### 2.2 Alternative: Pull from an Index and Filter

If you prefer starting from a known index rather than a blank screen:

```
=BDS("RTY Index","INDX_MEMBERS")
```

This pulls all Russell 2000 constituents. Then apply filters via BDP (see below). You can also use:

```
=BDS("RAY Index","INDX_MEMBERS")    // Russell 3000
=BDS("RUO Index","INDX_MEMBERS")    // Russell Microcap
```

### 2.3 Bloomberg Excel Add-in (BDP) — Universe Validation

Once you have a ticker list (Column A, rows 2+), validate each ticker against the universe criteria:

```excel
' Cell B2 — Market Cap (millions USD)
=BDP(A2&" US Equity","CUR_MKT_CAP")

' Cell C2 — Exchange Code
=BDP(A2&" US Equity","EXCH_CODE")

' Cell D2 — Last Price
=BDP(A2&" US Equity","PX_LAST")

' Cell E2 — 20-Day Average Volume (shares)
=BDP(A2&" US Equity","VOLUME_AVG_20D")

' Cell F2 — Dollar Volume (calculated)
=D2*E2

' Cell G2 — Pass/Fail Universe Filter
=AND(B2>=50, B2<=10000, OR(C2="NAS",C2="NYS",C2="ASE"), D2>=2, F2>=500000)
```

Copy these formulas down for all tickers. Filter Column G to TRUE to get the final universe.

---

## 3. Data Field Specifications

### Field 1: Price Data (OHLCV) — 15 Months Daily

**Why 15 months:** 252 trading days for the 52-week high lookback, plus 126 trading days for the 6-month relative strength calculation. Fifteen calendar months provides comfortable headroom.

**Bloomberg function:** BDH (historical data)

**Excel formula (single ticker):**

```excel
=BDH("AAPL US Equity","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME","01/01/2024","03/31/2025","Days=A","Fill=P","CshAdjNormal=Y","CshAdjAbnormal=Y")
```

**Fields:**

| Bloomberg Field | Description |
|----------------|-------------|
| `PX_OPEN` | Opening price |
| `PX_HIGH` | Intraday high |
| `PX_LOW` | Intraday low |
| `PX_LAST` | Closing price |
| `VOLUME` | Daily share volume |

**Parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `Days=A` | Actual trading days only | Excludes weekends and holidays |
| `Fill=P` | Fill with previous value | Fills gaps (holidays, halts) with last known price |
| `CshAdjNormal=Y` | Adjust for regular dividends | Ensures RS calculation reflects total return |
| `CshAdjAbnormal=Y` | Adjust for splits and special dividends | Prevents false 52-week highs from pre-split prices |

**Date range:** Set the start date to 15 months before today. For a March 2025 run, use `01/01/2024` to `03/31/2025`. For dynamic dates in Excel:

```excel
=BDH("AAPL US Equity","PX_OPEN,PX_HIGH,PX_LOW,PX_LAST,VOLUME",TEXT(EDATE(TODAY(),-15),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days=A","Fill=P","CshAdjNormal=Y","CshAdjAbnormal=Y")
```

**Alternative fields if primary fails:**

| Situation | Alternative |
|-----------|-------------|
| `PX_LAST` returns #N/A | Try `LAST_PRICE` or `PX_CLOSE_1D` |
| Need unadjusted prices | Omit `CshAdjNormal` and `CshAdjAbnormal` parameters |
| Need total-return adjusted | Use `TOT_RETURN_INDEX_GROSS_DVDS` instead of `PX_LAST` |

**Gotchas:**

- Bloomberg returns **unadjusted** prices by default. For the RS calculation and 52-week high derivation, you **must** use adjusted prices. Always include `CshAdjNormal=Y` and `CshAdjAbnormal=Y`.
- For the current price filter ($2.00 minimum), use the **unadjusted** `PX_LAST` from BDP, not the adjusted historical series.
- `Fill=P` is important: without it, tickers halted for a day will have blank rows that break time-alignment across the universe.
- BDH returns dates in Column 1 by default. If you need dates suppressed (data only), add `Header=N` and `Dates=H` parameters.
- For 2,000 tickers at 315 rows each, this is 630,000 data points per field. Pull in batches (see Section 4).

---

### Field 2: Market Capitalization

**Bloomberg function:** BDP (current) or BDH (historical for backtesting)

**Excel formula — current snapshot:**

```excel
=BDP("AAPL US Equity","CUR_MKT_CAP")
```

**Excel formula — historical series (for backtesting):**

```excel
=BDH("AAPL US Equity","CUR_MKT_CAP","01/01/2024","03/31/2025","Days=A","Fill=P")
```

**Unit:** Millions USD (Bloomberg default for US equities).

**Filter logic:** `CUR_MKT_CAP BETWEEN 50 AND 10000`

**Alternative fields:**

| Alternative | When to Use |
|-------------|------------|
| `HISTORICAL_MARKET_CAP` | Point-in-time historical (more accurate for backtesting) |
| `EQY_SH_OUT * PX_LAST` | Calculate manually from shares outstanding and price |
| `MARKET_CAPITALIZATION_INTRADAY` | Real-time intraday market cap |
| `CUR_MKT_CAP_CRNCY` | If you need to verify the currency of the reported value |

**Gotchas:**

- Companies with multiple share classes (e.g., GOOG/GOOGL) may report separate market caps per class. Use `CUR_MKT_CAP` which typically reflects total market cap, but verify for dual-class names.
- Some ADRs or foreign-listed tickers may report market cap in local currency. Check `CRNCY` field if values look suspicious (e.g., a "small cap" showing 500,000 could be in JPY).
- For monthly screening, pull market cap as of the last trading day of the prior month for consistency.

---

### Field 3: Average Daily Volume

**Bloomberg function:** BDP

**Excel formula — share volume:**

```excel
=BDP("AAPL US Equity","VOLUME_AVG_20D")
```

**Excel formula — dollar volume (what the strategy requires):**

```excel
=BDP("AAPL US Equity","VOLUME_AVG_20D") * BDP("AAPL US Equity","PX_LAST")
```

Or, more efficiently, if you already have price in column D:

```excel
=BDP(A2&" US Equity","VOLUME_AVG_20D") * D2
```

**Filter:** Dollar volume >= $500,000 per day.

**Alternative fields:**

| Alternative | Description |
|-------------|-------------|
| `VOLUME_AVG_30D` | 30-day average volume in shares (smoother, less sensitive to recent spikes) |
| `TURNOVER_AVG_20D` | 20-day average turnover in local currency (already in dollar terms if available) |
| `EQY_SH_OUT_REAL_TIME` | Real-time shares outstanding (for float-adjusted calculations) |
| Manual BDH | Pull 20 days of `VOLUME` via BDH, compute average in Excel |

**Manual approach (when BDP alternatives fail):**

```excel
=AVERAGE(BDH("AAPL US Equity","VOLUME",TEXT(TODAY()-30,"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days=A"))
```

**Gotchas:**

- Bloomberg `VOLUME` is in **shares**, not dollars. You must multiply by price to get dollar volume.
- Volume can spike around earnings announcements, index rebalances, or news events. The 20-day average smooths single-day spikes, but a stock that just had earnings will have an inflated average.
- Some small-cap stocks have zero-volume days. These zeros are included in the 20-day average and drag it down, which is actually desirable for our liquidity filter.
- If `VOLUME_AVG_20D` returns zero or #N/A, the stock is likely too illiquid for the strategy. Exclude it.

---

### Field 4: EPS (Quarterly) — Last 8 Quarters

**Bloomberg function:** BDH with quarterly periodicity

**Excel formula:**

```excel
=BDH("AAPL US Equity","IS_DILUTED_EPS","01/01/2023","03/31/2025","Per=Q","Days=A","Fill=P")
```

**Primary field:** `IS_DILUTED_EPS` (diluted earnings per share, as reported quarterly)

**Parameters:**

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `Per=Q` | Quarterly periodicity | Returns one value per fiscal quarter |
| `Days=A` | Actual | Aligns to fiscal period end dates |
| `Fill=P` | Previous fill | Fills gaps if a quarter is delayed |

**Date range:** 8 quarters back from current date (~2 years). For a March 2025 screen, use start date `01/01/2023`.

**Alternative fields:**

| Alternative | When to Use |
|-------------|------------|
| `IS_EPS` | Basic (undiluted) EPS — use if diluted not available |
| `TRAIL_12M_DILUTED_EPS` | Trailing 12-month EPS — use only if quarterly breakout unavailable |
| `IS_OPER_INC / EQY_SH_OUT` | Operating EPS — excludes one-time charges |
| `BEST_EPS` | Consensus estimate — **do NOT use** for this strategy (forward-looking) |

**YoY Growth Calculation:**

Once you have 8 quarters of EPS in a column (Q1 through Q8, most recent first):

```excel
' Assume Q1 (most recent) is in cell H2, Q5 (same quarter last year) is in H6
' EPS Growth % = (Current Quarter EPS - Year-Ago Quarter EPS) / ABS(Year-Ago Quarter EPS) * 100

=IF(H6=0, IF(H2>0, 999, 0), (H2 - H6) / ABS(H6) * 100)
```

For the composite score, cap at 100%:

```excel
=MIN((H2-H6)/ABS(H6)*100, 100)
```

**Gotchas:**

- **Fiscal vs. calendar quarters (CRITICAL):** Bloomberg reports EPS on the company's fiscal year basis. A company with a January fiscal year-end has Q1 = Feb--Apr, not Jan--Mar. When computing YoY growth, always compare the **same fiscal quarter** (Q vs. Q-4), not calendar-aligned quarters. Bloomberg handles this correctly when you use `Per=Q` — just compare row N to row N+4.
- **Earnings restatements:** Bloomberg updates historical data when companies restate. For true point-in-time data (backtesting), use the `EHST <GO>` function or Bloomberg's `REVISION_DATE` fields.
- **One-time charges:** Restructuring charges, write-downs, and legal settlements can distort quarterly EPS. Consider using `IS_OPER_INC` (operating income) divided by diluted shares for a cleaner signal.
- **Turnaround stocks:** If prior-year EPS was negative and current EPS is positive, the percentage change is mathematically large. The strategy handles this by capping growth at 100% in the composite score. Assign 999% internally for sorting, but cap at 100 for the weighted score.
- **Missing quarters:** Some companies (especially foreign filers or REITs) report semi-annually. If fewer than 8 quarters are returned, flag the ticker for manual review. Check `ANNOUNCEMENT_DT` to see when the last earnings were reported.

---

### Field 5: Revenue (Quarterly) — Last 8 Quarters

**Bloomberg function:** BDH with quarterly periodicity

**Excel formula:**

```excel
=BDH("AAPL US Equity","SALES_REV_TURN","01/01/2023","03/31/2025","Per=Q","Days=A","Fill=P")
```

**Primary field:** `SALES_REV_TURN` (total revenue / net sales / turnover)

**Alternative fields:**

| Alternative | When to Use |
|-------------|------------|
| `IS_COMP_SALES` | Comparable / reported sales (may differ from SALES_REV_TURN for some sectors) |
| `NET_REV` | Net revenue after returns/allowances |
| `TOTAL_REVENUE` | May include non-operating revenue — use with caution |
| `CF_SALES` | Cash flow statement sales (cross-check) |

**Date range:** 8 quarters back from current date (~2 years).

**YoY Growth Calculation:**

```excel
' Assume Q1 (most recent) revenue in cell J2, Q5 (year-ago) in J6
' Revenue Growth % = (Current - Year-Ago) / Year-Ago * 100

=IF(J6<=0, IF(J2>0, 999, 0), (J2 - J6) / J6 * 100)
```

For the composite score, cap at 100%:

```excel
=MIN((J2-J6)/J6*100, 100)
```

**Gotchas:**

- **Same fiscal vs. calendar quarter issue as EPS.** See Field 4 notes.
- **Revenue units:** Bloomberg typically reports revenue in millions for US equities, but check the `SCALING_FACTOR` or `FUND_CRNCY` fields. A revenue figure of "50" could be $50M or $50K depending on the company's reporting scale.
- **Pre-revenue companies:** Biotech, clinical-stage pharma, and pre-launch tech companies may report zero or null revenue for all 8 quarters. These will have undefined growth. Exclude them from the revenue growth component or assign 0%.
- **M&A distortion:** A company that acquired a competitor mid-year will show a large revenue jump that is not organic. Bloomberg does not automatically adjust for this. If a revenue growth figure exceeds 200%, consider flagging for manual review.
- **Negative revenue:** Rare but possible (e.g., insurance companies reporting net premiums, or companies with large return allowances). Exclude these from the revenue growth calculation entirely.

---

### Field 6: Exchange Listing

**Bloomberg function:** BDP

**Excel formula:**

```excel
=BDP("AAPL US Equity","EXCH_CODE")
```

**Expected return values and their meaning:**

| Code | Exchange |
|------|----------|
| `NAS` | NASDAQ (all tiers: Global Select, Global, Capital) |
| `NYS` | New York Stock Exchange |
| `ASE` | NYSE American (formerly AMEX / NYSE MKT) |

**Filter:** Only include tickers where `EXCH_CODE` is one of: NAS, NYS, ASE.

**Alternative fields:**

| Alternative | Return Value Example | Notes |
|-------------|---------------------|-------|
| `ID_MIC_PRIM_EXCH` | XNAS, XNYS, XASE | ISO MIC code format |
| `EQY_PRIM_EXCH` | "NASDAQ", "New York" | Full text name |
| `MARKET_SECTOR_DES` | "Equity" | Broader — not exchange-specific |
| `COUNTRY_ISO` | US | Use as supplementary filter |

**Gotchas:**

- Some OTC-traded stocks can return `NAS` if they were formerly NASDAQ-listed or if Bloomberg maps them to the NASDAQ OTC tier. Cross-check with `MARKET_STATUS` = "ACTV" and `SECURITY_TYP` = "Common Stock".
- ADRs listed on NYSE (e.g., TSM, BABA) will show `NYS`. If you want to exclude foreign companies, add a filter on `COUNTRY_ISO` = "US" or `CNTRY_OF_INCORPORATION` = "US".
- SPACs and blank-check companies will list on NYSE/NASDAQ. Consider adding `INDUSTRY_GROUP` != "Blank Checks" or checking `IS_SPAC` = "N".

---

### Field 7: Current Share Price

**Bloomberg function:** BDP

**Excel formula:**

```excel
=BDP("AAPL US Equity","PX_LAST")
```

**Filter:** `PX_LAST` >= 2.00

**Alternative fields:**

| Alternative | When to Use |
|-------------|------------|
| `LAST_PRICE` | Real-time last traded price (intraday) |
| `PX_CLOSE_1D` | Previous trading day's official close |
| `PX_MID` | Midpoint of bid/ask (useful for illiquid stocks where last trade may be stale) |
| `PX_SETTLE_LAST_DT_RT` | Last settlement price with real-time date |

**Gotchas:**

- For screening consistency, always use **end-of-day** close prices. If running the screen during market hours, use `PX_CLOSE_1D` (yesterday's close) rather than the live `PX_LAST`.
- The $2.00 filter uses **unadjusted** prices. A stock that split 2:1 and now trades at $1.50 should be excluded, even though its adjusted historical price would show $3.00 pre-split. The BDP `PX_LAST` field returns the current unadjusted price, which is what you want here.
- Stocks halted from trading will show their last traded price. Check `TRADING_DAY_STATUS` if you want to exclude halted names.

---

### Field 8: 52-Week High

**Bloomberg function:** BDP (direct) or BDH (derive from history)

**Excel formula — direct pull:**

```excel
=BDP("AAPL US Equity","HIGH_52WEEK")
```

**Excel formula — derive from 252-day price history:**

```excel
=MAX(BDH("AAPL US Equity","PX_HIGH",TEXT(TODAY()-365,"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days=A","CshAdjNormal=Y","CshAdjAbnormal=Y"))
```

**Price vs. 52-Week High (for composite score):**

```excel
' Direct from BDP fields
=BDP("AAPL US Equity","PX_LAST") / BDP("AAPL US Equity","HIGH_52WEEK") * 100

' Or using cell references (more efficient)
=D2 / L2 * 100
```

Where D2 = current price and L2 = 52-week high.

**Alternative approaches:**

| Approach | Formula | Notes |
|----------|---------|-------|
| Direct BDP field | `HIGH_52WEEK` | Quick but may use calendar days, not trading days |
| Max of 252 trading days | `MAX(BDH(...PX_HIGH...))` | Precise, uses your chosen adjustment method |
| Percentage from high | `PCT_CHG_52WEEK_HIGH` | May exist as a direct field — returns negative % |
| Adjusted close max | `MAX(BDH(...PX_LAST...adjusted))` | Use adjusted close instead of intraday high |

**Gotchas:**

- Bloomberg's `HIGH_52WEEK` may use **calendar days** (365 days) rather than **trading days** (252 days). For strategy consistency, derive the 52-week high from 252 trading days of adjusted close prices using BDH.
- Decide whether to use the intraday high (`PX_HIGH`) or the closing high (`PX_LAST`). The strategy document uses closing prices for consistency — use `MAX(PX_LAST over 252 days)`.
- If using adjusted prices for the 52-week high derivation, the "Price vs. High" ratio should also use the adjusted current price. However, since adjusted and unadjusted are identical for the most recent day (no future adjustments), `PX_LAST` from BDP is fine for the numerator.
- A stock at its 52-week high will score 100% on this component. A stock at 50% of its high scores 50%. The composite score weights this at 0.20.

---

## 4. Pulling the Full Universe from Bloomberg

### Method 1: EQS Screen to Excel Export (Recommended for First-Time Setup)

1. Run the EQS screen described in Section 2.1.
2. Export the ticker list to Excel.
3. In a new workbook, paste tickers in Column A.
4. Add BDP formulas (Section 2.3) in Columns B--G for universe validation.
5. Filter to passing tickers.
6. Use the filtered ticker list as input for the historical BDH pulls.

### Method 2: Bloomberg Excel Add-in Bulk Pull (Recommended for Monthly Refresh)

For pulling BDH data across the full universe, you must batch requests to avoid hitting Bloomberg's data limits.

**Step 1 — Prepare ticker list (Sheet: Universe)**

Place all ~2,000 tickers in Column A of the Universe sheet.

**Step 2 — Pull price data in batches (Sheet: Price Data)**

Bloomberg Excel add-in can handle roughly 50--100 simultaneous BDH requests. Structure the Price Data sheet as follows:

```excel
' Row 1: Headers
' Row 2: BDH formula for first ticker
' Repeat for tickers in batches of 50

' For ticker in cell Universe!A2:
=BDH(Universe!A2&" US Equity","PX_LAST",TEXT(EDATE(TODAY(),-15),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Days=A","Fill=P","CshAdjNormal=Y","CshAdjAbnormal=Y","Header=N","Dates=H")
```

Alternatively, use a **single BDH with multiple securities** (Bloomberg supports this in newer add-in versions):

```excel
=BDH("AAPL US Equity,MSFT US Equity,GOOG US Equity","PX_LAST","01/01/2024","03/31/2025","Days=A","Fill=P","CshAdjNormal=Y","CshAdjAbnormal=Y")
```

**Step 3 — Pull fundamental data in batches (Sheet: Fundamentals)**

```excel
' EPS — quarterly
=BDH(Universe!A2&" US Equity","IS_DILUTED_EPS",TEXT(EDATE(TODAY(),-24),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Per=Q","Days=A","Fill=P")

' Revenue — quarterly
=BDH(Universe!A2&" US Equity","SALES_REV_TURN",TEXT(EDATE(TODAY(),-24),"MM/DD/YYYY"),TEXT(TODAY(),"MM/DD/YYYY"),"Per=Q","Days=A","Fill=P")
```

### Method 3: Bloomberg Query Language (BQL) — Programmatic Access

For users with Bloomberg's Python API or BQL access:

```python
import bql

bq = bql.Service()

# Define universe
universe = bq.univ.screen(
    "CUR_MKT_CAP BETWEEN 50 AND 10000 AND "
    "EXCH_CODE IN ('NAS','NYS','ASE') AND "
    "PX_LAST >= 2"
)

# Pull current data
request = bql.Request(
    universe,
    {
        'Market Cap': bq.data.cur_mkt_cap(),
        'Price': bq.data.px_last(),
        'Volume 20D': bq.data.volume_avg_20d(),
        'Exchange': bq.data.exch_code(),
        '52W High': bq.data.high_52week(),
    }
)
response = bq.execute(request)

# Pull historical price data
hist_request = bql.Request(
    universe,
    {
        'Close': bq.data.px_last(
            dates=bq.func.range('-15M', '0D'),
            frq='D',
            fill='prev',
            currency='USD'
        ),
    }
)
hist_response = bq.execute(hist_request)
```

BQL is significantly faster than the Excel add-in for large universes and is the preferred method if you have programmatic Bloomberg access.

---

## 5. Excel Template Structure

Organize the workbook into the following sheets:

### Sheet 1: Universe

| Column | Field | Source |
|--------|-------|--------|
| A | Ticker | EQS export or index members |
| B | Company Name | `=BDP(A2&" US Equity","NAME")` |
| C | Market Cap ($M) | `=BDP(A2&" US Equity","CUR_MKT_CAP")` |
| D | Exchange | `=BDP(A2&" US Equity","EXCH_CODE")` |
| E | Last Price | `=BDP(A2&" US Equity","PX_LAST")` |
| F | Avg Volume 20D | `=BDP(A2&" US Equity","VOLUME_AVG_20D")` |
| G | Dollar Volume | `=E2*F2` |
| H | 52-Week High | `=BDP(A2&" US Equity","HIGH_52WEEK")` |
| I | Pass Filter? | `=AND(C2>=50,C2<=10000,OR(D2="NAS",D2="NYS",D2="ASE"),E2>=2,G2>=500000)` |

### Sheet 2: Price Data

- One sub-section per ticker (or use a pivot-friendly long format).
- BDH pulls 15 months of daily adjusted OHLCV.
- For the RS calculation, only the adjusted close (`PX_LAST` with `CshAdj` flags) is needed.
- For the 52-week high derivation, use the adjusted close series.

### Sheet 3: Fundamentals

| Column | Field | Source |
|--------|-------|--------|
| A | Ticker | Link to Universe sheet |
| B--I | EPS Q1 through Q8 | BDH quarterly `IS_DILUTED_EPS` |
| J--Q | Revenue Q1 through Q8 | BDH quarterly `SALES_REV_TURN` |
| R | EPS Growth (%) | `=IF(F2=0,IF(B2>0,999,0),(B2-F2)/ABS(F2)*100)` |
| S | Revenue Growth (%) | `=IF(N2<=0,IF(J2>0,999,0),(J2-N2)/N2*100)` |

(Where B2 = most recent quarter, F2 = same quarter one year ago for EPS; J2 and N2 similarly for revenue.)

### Sheet 4: Factor Calculations

| Column | Field | Formula |
|--------|-------|---------|
| A | Ticker | Link |
| B | 6-Month Return | `=(CurrentClose - Close126DaysAgo) / Close126DaysAgo * 100` |
| C | RS Percentile | `=PERCENTRANK.INC(B:B, B2) * 100` |
| D | EPS Growth (capped) | `=MIN(Fundamentals!R2, 100)` |
| E | Revenue Growth (capped) | `=MIN(Fundamentals!S2, 100)` |
| F | Price / 52-Week High | `=Universe!E2 / Universe!H2 * 100` |
| G | Composite Score | `=0.40*C2 + 0.20*D2 + 0.20*E2 + 0.20*F2` |

### Sheet 5: Quality Filters

Boolean pass/fail gates applied after composite scoring:

| Column | Filter | Formula |
|--------|--------|---------|
| A | Ticker | Link |
| B | Market Cap Pass | `=AND(Universe!C2>=50, Universe!C2<=10000)` |
| C | Exchange Pass | `=OR(Universe!D2="NAS",Universe!D2="NYS",Universe!D2="ASE")` |
| D | Price Pass | `=Universe!E2>=2` |
| E | Liquidity Pass | `=Universe!G2>=500000` |
| F | EPS Growth Positive | `=Fundamentals!R2>0` |
| G | Revenue Growth Positive | `=Fundamentals!S2>0` |
| H | All Pass | `=AND(B2:G2)` |

### Sheet 6: Composite Scores

| Column | Field | Formula |
|--------|-------|---------|
| A | Rank | `=RANK(FactorCalc!G2, FactorCalc!G:G, 0)` |
| B | Ticker | Link |
| C | Company Name | Link |
| D | Composite Score | Link to Factor Calculations |
| E | RS Percentile | Link |
| F | EPS Growth | Link |
| G | Rev Growth | Link |
| H | Price/High % | Link |
| I | Market Cap | Link |

Sort by Column A (Rank) ascending. Top 25 rows are the portfolio.

### Sheet 7: Signals

Compare this month's top 25 to last month's top 25:

| Column | Field | Logic |
|--------|-------|-------|
| A | Ticker | All tickers in current or prior top 25 |
| B | Current Rank | This month's rank (blank if not in top 25) |
| C | Prior Rank | Last month's rank (blank if not in top 25) |
| D | Signal | `=IF(AND(B2<>"",C2=""),"BUY",IF(AND(B2="",C2<>""),"SELL",IF(AND(B2<>"",C2<>""),"HOLD","")))` |

### Sheet 8: Portfolio

| Column | Field | Notes |
|--------|-------|-------|
| A | Ticker | Current holdings |
| B | Shares | Position size |
| C | Entry Price | Purchase price |
| D | Current Price | `=BDP(A2&" US Equity","PX_LAST")` |
| E | P&L ($) | `=(D2-C2)*B2` |
| F | P&L (%) | `=(D2-C2)/C2*100` |
| G | Weight (%) | `=D2*B2/SUM($D$2:$D$26*$B$2:$B$26)*100` |

---

## 6. Monthly Refresh Workflow

Execute on the **first trading day of each month**:

### Step 1: Open the Workbook

Open the Bloomberg Excel workbook. Ensure the Bloomberg add-in is loaded (check for the Bloomberg ribbon tab in Excel).

### Step 2: Update Date Ranges

If using hardcoded dates in BDH formulas, update:
- Price data start date: 15 months before today
- Price data end date: last trading day of prior month
- Fundamentals start date: 24 months before today

If using dynamic dates (`EDATE(TODAY(),...)` and `TODAY()`), no manual update is needed.

### Step 3: Refresh All Bloomberg Data

Option A — Keyboard shortcut:
```
Ctrl + Shift + R
```

Option B — Bloomberg ribbon:
```
Bloomberg tab → Refresh Workbook
```

Option C — Right-click any Bloomberg formula cell:
```
Right-click → Bloomberg → Refresh Selected
```

### Step 4: Wait for Data Population

- With ~2,000 tickers, a full refresh takes **5--15 minutes** depending on data volume and Bloomberg server load.
- Watch the Bloomberg status bar in the lower-left corner of Excel. It will show "Requesting data..." and a progress count.
- Do not interact with the workbook until all requests complete.

### Step 5: Verify Data Completeness

Run these checks:

```excel
' Count tickers with #N/A in market cap (should be 0 or very few)
=COUNTIF(Universe!C:C,"#N/A")

' Count tickers with #N/A in EPS (some expected for pre-revenue companies)
=COUNTIF(Fundamentals!B:B,"#N/A")

' Count tickers passing all filters
=COUNTIF(QualityFilters!H:H,TRUE)
```

If more than 10% of tickers show #N/A for a given field, there may be a Bloomberg connectivity issue. Try refreshing again.

### Step 6: Review Factor Calculations

Verify the factor distributions look reasonable:
- RS Percentile: should range 0--100 with roughly uniform distribution
- EPS Growth: expect a wide range, heavy right tail (capped at 100)
- Revenue Growth: similar to EPS but typically less volatile
- Price/High: most stocks should be 50--100% of their 52-week high

### Step 7: Generate Signals

Compare this month's top 25 to last month's saved top 25. The Signals sheet should automatically populate BUY, SELL, and HOLD signals.

### Step 8: Save Snapshot

```
File → Save As → "EmergingGrowth_YYYY-MM.xlsx"
```

Always save a dated copy for records and backtesting validation. The prior month's file provides the "last month's top 25" for signal generation.

---

## 7. Common Bloomberg Gotchas — Summary Reference

| # | Issue | Impact | Solution |
|---|-------|--------|----------|
| 1 | **Adjusted vs. unadjusted prices** | False 52-week highs from pre-split prices; incorrect RS calculation | Use `CshAdjNormal=Y` and `CshAdjAbnormal=Y` in BDH for historical data. Use unadjusted `PX_LAST` for current price filter only. |
| 2 | **Fiscal vs. calendar quarters** | Comparing wrong quarters YoY yields meaningless growth rates | Always compare same fiscal quarter (Q vs. Q-4 in the BDH output). Bloomberg's `Per=Q` aligns to fiscal quarters automatically. |
| 3 | **Data limits** | Bloomberg Excel add-in caps simultaneous requests at ~500 cells | Pull data in batches of 50--100 tickers. Use separate sheets per batch if needed. Refresh one batch at a time. |
| 4 | **Stale fundamental data** | Small-cap companies may not update financials promptly | Check `LATEST_PERIOD_END_DT_FULL_RECORD` to verify the most recent reporting period. If it is more than 6 months old, flag for review. |
| 5 | **Currency mismatches** | Market cap or revenue in non-USD currency produces incorrect filters | Add `=BDP(A2&" US Equity","CRNCY")` check column. Should return "USD" for all US-listed equities. |
| 6 | **Ticker changes** | Mergers, name changes, and re-listings break BDH continuity | Bloomberg usually maps old tickers to new ones, but verify. Use `ID_BB_GLOBAL` (FIGI) as a stable identifier if tracking over time. |
| 7 | **Delisted securities** | Pulling data for a delisted ticker returns #N/A or stale data | Check `MARKET_STATUS` field — should be "ACTV". For backtesting survivorship-bias-free data, use `EHST <GO>`. |
| 8 | **API rate limits** | Too many requests too fast causes timeouts or partial data | Space out batch refreshes. Wait for each batch to complete before starting the next. Avoid refreshing the entire 2,000-ticker workbook at once. |
| 9 | **BDH date alignment** | Different tickers may have different trading calendars (halts, IPO dates) | Use `Fill=P` to forward-fill missing dates. Check that all tickers have the same number of rows before computing cross-sectional RS percentile. |
| 10 | **Excel formula limits** | Large BDH arrays can exceed Excel's row/column limits | For 2,000 tickers x 315 days x 5 fields, consider splitting into multiple workbooks or using BQL/Python instead. |

---

## 8. Troubleshooting

### #N/A Errors

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| #N/A for all fields | Ticker format wrong | Ensure format is `"TICKER US Equity"` (include the "US Equity" yellow key) |
| #N/A for `IS_DILUTED_EPS` | Company does not report diluted EPS | Try `IS_EPS` (basic EPS) or `TRAIL_12M_DILUTED_EPS` |
| #N/A for `SALES_REV_TURN` | Pre-revenue company or different field name | Try `IS_COMP_SALES` or `NET_REV` |
| #N/A for `HIGH_52WEEK` | Recently IPO'd (less than 52 weeks of history) | Derive from available price history: `=MAX(BDH(...available date range...))` |
| #N/A for `CUR_MKT_CAP` | Delisted or OTC security | Check `MARKET_STATUS`; remove from universe |

### #NAME? Errors

The Bloomberg Excel add-in is not loaded. To fix:

1. Close Excel completely.
2. Open Bloomberg Terminal (must be running).
3. Type `DAPI <GO>` on the terminal to verify API access is enabled.
4. Reopen Excel — the Bloomberg add-in should auto-load.
5. If not, go to **File → Options → Add-Ins → Manage COM Add-ins → Go** and check "Bloomberg Excel Tools".

### Slow Refresh / Timeouts

- **Reduce batch size:** Pull 25--50 tickers at a time instead of 100.
- **Simplify formulas:** Use BDP for current data (fast) and BDH only for historical series (slow).
- **Off-peak hours:** Bloomberg servers are less loaded before 7 AM ET and after 6 PM ET.
- **Use BDS for bulk data:** `=BDS("screen_name","MEMBERS_DATA")` can pull multiple fields for a full screen in one request.
- **Check Bloomberg status:** Type `HMON <GO>` to view Bloomberg system health.

### Missing Quarters in Fundamentals

- Some companies report semi-annually (common for foreign filers even if US-listed).
- Check `ANNOUNCEMENT_FREQUENCY` field: should return "Quarterly" for US companies.
- If a company only has 4 data points instead of 8 for the 2-year window, it may be semi-annual. Either exclude or interpolate.

### Negative Revenue

- Possible for insurance companies (net premium adjustments), companies with large return provisions, or data errors.
- Exclude tickers with any negative quarterly revenue from the revenue growth calculation.
- Formula: `=IF(MIN(J2:Q2)<0, "EXCLUDE", revenue_growth_formula)`

### Data Discrepancies vs. Sharadar

If Bloomberg and Sharadar data disagree:

- **Price data:** Minor differences are normal due to adjustment methodology. Both should use split-adjusted prices.
- **Fundamentals:** Check reporting date — Sharadar uses `datekey` (filing date) while Bloomberg uses `ANNOUNCEMENT_DT`. Timing differences of 1--5 days are common.
- **Market cap:** Sharadar uses `marketcap` from its own calculation; Bloomberg uses `CUR_MKT_CAP`. Small differences (< 5%) are normal.
- **Resolution:** When in doubt, Bloomberg is the authoritative source for live trading decisions. Use Sharadar for backtesting (longer history, easier programmatic access).
