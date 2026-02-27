# 05 — Live Portfolio Management: Operational Guide

> **Purpose:** Step-by-step operational guide for executing the Emerging Growth Strategy in a live portfolio. Covers everything from receiving the monthly signal output to trade execution, position sizing, risk controls, and record keeping.
>
> **Key Principle:** This strategy is 100% systematic with zero discretionary intervention. The only exception is the -25% max drawdown override, which requires a documented decision.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Monthly Execution Timeline](#2-monthly-execution-timeline)
3. [Position Sizing](#3-position-sizing)
4. [Trade Execution Order](#4-trade-execution-order)
5. [Winner Trimming Rule](#5-winner-trimming-rule)
6. [Sector Concentration Limit](#6-sector-concentration-limit)
7. [Risk Controls](#7-risk-controls)
8. [Rebalancing Mechanics — Detailed](#8-rebalancing-mechanics--detailed)
9. [Signal Interpretation Guide](#9-signal-interpretation-guide)
10. [Record Keeping](#10-record-keeping)
11. [Tax Considerations](#11-tax-considerations)
12. [Common Operational Scenarios](#12-common-operational-scenarios)
13. [Monthly Implementation Checklist](#13-monthly-implementation-checklist)

---

## 1. Overview

This document is the operational manual for managing a live portfolio using the Emerging Growth Strategy. It assumes the screening pipeline (docs 01-03) has already been run and has produced a ranked list of the top 25 stocks with BUY/SELL/HOLD signals.

**What this guide covers:**

- Receiving the monthly signal output and verifying its correctness
- Calculating position sizes for your specific portfolio value
- Executing trades in the correct sequence (SELL, then BUY, then REBALANCE)
- Enforcing risk limits (winner trimming, sector caps, drawdown threshold)
- Maintaining accurate records for performance tracking and tax reporting

**What this guide does NOT cover:**

- How to run the screening pipeline (see `01-universe-screening.md`)
- How to calculate factor scores (see `02-factor-calculations.md`)
- How to generate signals (see `03-quality-filters-and-scoring.md`)
- How to backtest or validate changes (see `04-backtesting-framework.md`)

**Core operating rules:**

1. Follow the signals exactly as generated. Do not override, second-guess, or selectively implement.
2. Execute in the prescribed order: SELLs first, BUYs second, REBALANCE third.
3. Complete all execution within the Day 1-3 window.
4. Do not trade between monthly rebalances.
5. Document everything.

---

## 2. Monthly Execution Timeline

| When | Action | Details |
|------|--------|---------|
| **Day 1 (Pre-market)** | Run ranking pipeline | Execute screening, scoring, and signal generation. Verify data freshness (price data through prior close, fundamentals from most recent quarter). |
| **Day 1 (Market Open)** | Review signals | Verify BUY/SELL/HOLD list against last month's portfolio. Check for obvious errors (delisted stocks, missing data, unusual scores). |
| **Day 1 (Morning)** | Distribute report | Send the monthly report (PDF + CSV) to all subscribers. Include signal list, composite scores, sector breakdown, and execution guidance. |
| **Day 1-3** | Execute trades | Sell exits first, then buy new positions, then rebalance existing holds. See Section 4 for detailed execution order. |
| **Day 3 (Close)** | Confirm execution | Verify all trades filled. Record execution prices. Calculate actual vs. target weights. |
| **Rest of Month** | Hold | No trading until next rebalance. Monitor drawdown weekly (Section 7). |

### Why Day 1-3 (not a single day)?

- **Liquidity:** Small-cap stocks ($50M-$10B market cap) may have limited daily volume. Spreading execution over 2-3 days reduces market impact and slippage.
- **Operational safety:** Gives time to verify signals, handle any data issues, and execute methodically rather than rushing.
- **Error recovery:** If a trade fails to fill or an error is discovered on Day 1, there is time to correct on Day 2.

### Why NOT month-end execution?

- Institutional funds engage in "window dressing" at month-end, buying recent winners and selling losers to improve reported holdings. This creates artificial price pressure.
- Executing at month-start avoids this distortion and aligns with the signal generation timing.
- Backtest assumes execution at month-start closing prices, so Day 1-3 execution most closely matches backtest assumptions.

---

## 3. Position Sizing

### Approach 1: Full Replication (25 stocks, $25,000+ portfolios)

Each position receives an equal 4% weight (1/25 of total portfolio value).

**Step-by-step calculation:**

```
1. Determine total portfolio value (cash + holdings at current market prices)
2. Per-position allocation = Total portfolio value / 25
3. For each stock: Shares = floor(Allocation / Current price)
4. Invested amount = Shares x Current price
5. Cash remainder = Allocation - Invested amount
```

**Worked example ($100,000 portfolio):**

| Stock | Price | Allocation (4%) | Shares (floor) | Invested | Remainder |
|-------|-------|-----------------|-----------------|----------|-----------|
| RIOT  | $12.50 | $4,000 | 320 | $4,000.00 | $0.00 |
| ABAT  | $7.80 | $4,000 | 512 | $3,993.60 | $6.40 |
| AMSC  | $28.35 | $4,000 | 141 | $3,997.35 | $2.65 |
| NUVB  | $4.15 | $4,000 | 963 | $3,996.45 | $3.55 |
| SIGA  | $9.20 | $4,000 | 434 | $3,992.80 | $7.20 |
| ... (20 more) | ... | ... | ... | ... | ... |

Total remainder from rounding: typically $50-$200 on a $100K portfolio. This sits in cash and is acceptable.

### Approach 2: Concentrated (Top 10, $10,000-$25,000 portfolios)

Each position receives an equal 10% weight (1/10 of total portfolio value).

**Step-by-step calculation:**

```
1. Determine total portfolio value
2. Per-position allocation = Total portfolio value / 10
3. For each stock: Shares = floor(Allocation / Current price)
4. Invested amount = Shares x Current price
5. Cash remainder = Allocation - Invested amount
```

**Worked example ($15,000 portfolio):**

| Stock | Price | Allocation (10%) | Shares (floor) | Invested | Remainder |
|-------|-------|-------------------|-----------------|----------|-----------|
| RIOT  | $12.50 | $1,500 | 120 | $1,500.00 | $0.00 |
| ABAT  | $7.80 | $1,500 | 192 | $1,497.60 | $2.40 |
| AMSC  | $28.35 | $1,500 | 52 | $1,474.20 | $25.80 |
| ... (7 more) | ... | ... | ... | ... | ... |

**Trade-offs of concentrated approach:**

- Higher volatility (fewer positions = less diversification)
- Potentially higher returns (top 10 scores are highest-conviction picks)
- Lower transaction costs (10 trades vs. 25 per rebalance)
- Larger rounding error as a percentage (especially with higher-priced stocks)
- Results will diverge more from the 25-stock backtest

### Position Sizing Worksheet

Use this template each month:

```
Date: ____________
Total Portfolio Value: $____________

Number of positions: ____ (25 or 10)
Per-position allocation: $____________ / ____ = $____________

Stock    Price    Shares=floor(Alloc/Price)    Invested    Remainder
-----    -----    -------------------------    --------    ---------
1. ____  $____    ____                         $____       $____
2. ____  $____    ____                         $____       $____
3. ____  $____    ____                         $____       $____
...
25. ___  $____    ____                         $____       $____

Total Invested: $____________
Total Cash Remainder: $____________
Cash as % of Portfolio: ____%
```

---

## 4. Trade Execution Order

**The sequence matters.** Execute in this exact order:

### Step 1: SELL first — Exit all SELL-signal positions

- Liquidate every position with a SELL signal (stocks that dropped out of the top 25).
- Sell the entire position, not a partial amount.
- Use **market orders** for small-cap stocks. Rationale: liquidity priority over price improvement. Limit orders in small-caps risk non-fills, leaving you stuck in a position the model wants to exit.
- For positions larger than 20% of the stock's average daily volume, consider splitting across Day 1 and Day 2 to minimize impact.
- Record: ticker, shares sold, execution price, total proceeds, gain/loss.

**Why sell first?**

1. Generates the cash needed to fund new BUY positions.
2. Immediately removes exposure to deteriorating names.
3. Avoids the need to sell existing holds to raise cash for new buys (which would distort HOLD weights).

### Step 2: BUY second — Enter all BUY-signal positions

- After SELL proceeds settle (most brokers allow same-day use of proceeds), allocate cash to new BUY positions.
- Target weight: 4% of total portfolio value for each new position (recalculate total portfolio value after sells).
- Use **market orders** for the same liquidity reasons.
- If a stock has very low volume (< $500K daily), consider using a limit order at the ask price to prevent excessive slippage, but be prepared to chase if it moves away.
- Record: ticker, shares bought, execution price, total cost, target weight.

**Handling insufficient cash:**

If SELL proceeds do not cover all BUY allocations, see Section 12 ("What if you don't have enough cash for all BUY signals?").

### Step 3: REBALANCE third — Adjust HOLD positions

- For each HOLD position, calculate current weight: `position_value / total_portfolio_value`.
- If weight > 6%: trim to 4% (see Section 5, Winner Trimming).
- If weight < 3.5%: consider adding to bring closer to 4% (if cash available).
- **Minimum trade threshold:** Do not rebalance if drift is less than 0.5% (saves transaction costs). A position at 3.7% or 4.3% is close enough.
- Net rebalancing orders where possible. If trimming Stock A generates $500 and Stock B needs $500 added, execute both.
- Record: ticker, action (TRIM/ADD), shares, execution price, new weight.

**Example rebalancing calculation:**

```
Portfolio value after SELLs and BUYs: $102,000
Target weight: 4.0% = $4,080

Stock X: 200 shares @ $25 = $5,000 → Weight = 4.90%
  Drift = +0.90% → Above 0.5% threshold → TRIM
  Sell: ($5,000 - $4,080) / $25 = 36 shares → Sell 36 shares

Stock Y: 150 shares @ $22 = $3,300 → Weight = 3.24%
  Drift = -0.76% → Above 0.5% threshold → ADD
  Buy: ($4,080 - $3,300) / $22 = 35 shares → Buy 35 shares

Stock Z: 180 shares @ $22.50 = $4,050 → Weight = 3.97%
  Drift = -0.03% → Below 0.5% threshold → SKIP (no trade)
```

---

## 5. Winner Trimming Rule

### Rule

If any position grows to more than 6% of total portfolio value, trim it back to 4% at the monthly rebalance.

### Rationale

- **Prevents single-stock dominance:** A runaway winner can quickly dominate a 25-stock portfolio if unchecked.
- **Locks in gains:** Selling partial winners converts paper profits to realized gains.
- **Maintains diversification:** Keeping all positions near 4% preserves the equal-weight risk profile that was validated in the backtest.
- **Avoids momentum traps:** Stocks that have run up significantly are at higher risk of mean reversion.

### Mechanics

```
1. At each monthly rebalance, calculate current weight for every HOLD position
2. If weight > 6.0%:
   a. Calculate trim amount: (current_value - target_value)
      where target_value = 0.04 * total_portfolio_value
   b. Shares to sell = floor(trim_amount / current_price)
   c. Execute sell order
   d. Redeploy cash to underweight positions or new BUYs
```

### Worked Example

```
Portfolio value: $110,000
Stock ABC: Bought at $20 (200 shares, $4,000 = 4% of $100K original)
Stock ABC now: $42.50 (200 shares = $8,500)
Current weight: $8,500 / $110,000 = 7.73%  → Exceeds 6% threshold

Target value: 0.04 * $110,000 = $4,400
Trim amount: $8,500 - $4,400 = $4,100
Shares to sell: floor($4,100 / $42.50) = 96 shares
Remaining: 104 shares * $42.50 = $4,420 (4.02% weight)
```

### Important Notes

- Winner trimming occurs ONLY at the monthly rebalance, not intra-month.
- If a stock is a SELL signal (dropped out of top 25), sell the entire position. Do not trim.
- The 6% threshold applies to portfolio weight, not price appreciation. A stock can double in price but still be under 6% if the overall portfolio grew.

---

## 6. Sector Concentration Limit

### Rule

Maximum 40% of the portfolio may be allocated to any single GICS sector.

### GICS Sector Classification

Use the 11 standard GICS sectors:

| Sector | Typical Small-Cap Presence |
|--------|---------------------------|
| Information Technology | High (often the largest sector in top 25) |
| Healthcare | High (biotech, medical devices) |
| Industrials | Moderate |
| Consumer Discretionary | Moderate |
| Consumer Staples | Low |
| Energy | Variable (cycle-dependent) |
| Materials | Moderate |
| Financials | Moderate |
| Real Estate | Low |
| Utilities | Low |
| Communication Services | Low |

**Data source for sector classification:** Use GICS codes from the Sharadar database (`sector` field), or look up via Bloomberg terminal (GICS_SECTOR_NAME field). Cross-reference against the stock's primary business if the classification seems incorrect.

### Enforcement Process

At each monthly rebalance, after generating the top 25 list:

```
1. Assign each stock its GICS sector
2. Sum weights by sector:
   Sector weight = (number of stocks in sector / 25) * 100%
3. If any sector > 40% (i.e., more than 10 stocks from one sector):
   a. Identify the lowest-ranked stock(s) in the over-concentrated sector
   b. Remove them from the top 25
   c. Replace with the next-highest-scoring stock(s) from a DIFFERENT sector
      (pull from rank 26, 27, etc. that passes all quality filters)
   d. Repeat until no sector exceeds 40%
```

### Worked Example

```
Initial top 25 ranking:
  Technology: 12 stocks (48%) → EXCEEDS 40% cap
  Healthcare: 5 stocks (20%)
  Industrials: 4 stocks (16%)
  Materials: 2 stocks (8%)
  Energy: 2 stocks (8%)

Action:
  Remove Tech stocks ranked #23, #24 (lowest composite scores in Tech)
  Replace with:
    Rank #26: Consumer Discretionary stock (score: 82.1) → ADD
    Rank #27: Financials stock (score: 81.5) → ADD

Adjusted top 25:
  Technology: 10 stocks (40%) → At limit, acceptable
  Healthcare: 5 stocks (20%)
  Industrials: 4 stocks (16%)
  Consumer Discretionary: 1 stock (4%)
  Materials: 2 stocks (8%)
  Energy: 2 stocks (8%)
  Financials: 1 stock (4%)
```

### Edge Cases

- If the replacement candidates also come from over-concentrated sectors, keep going down the ranked list until a different sector is found.
- If applying the 40% cap forces dropping more than 5 stocks from the top 25, this indicates extreme sector concentration. Document the situation and consider whether a market regime shift is occurring.
- Sector assignments rarely change for a given stock. If a company restructures and changes sector, update the classification.

---

## 7. Risk Controls

### 7.1 Max Drawdown Threshold: -25%

**Definition:**

```
Drawdown = (Current Portfolio Value - Peak Portfolio Value) / Peak Portfolio Value
```

Where "Peak Portfolio Value" is the highest value the portfolio has ever reached (high-water mark).

**Monitoring cadence:** Weekly at minimum. Daily during volatile markets.

**Tracking example:**

```
Month 1: Portfolio = $100,000 → Peak = $100,000 → Drawdown = 0%
Month 3: Portfolio = $112,000 → Peak = $112,000 → Drawdown = 0%
Month 5: Portfolio = $104,000 → Peak = $112,000 → Drawdown = -7.14%
Month 7: Portfolio = $95,000  → Peak = $112,000 → Drawdown = -15.18%
Month 9: Portfolio = $84,500  → Peak = $112,000 → Drawdown = -24.55%
  → APPROACHING THRESHOLD — heighten monitoring to daily
Month 10: Portfolio = $83,000 → Peak = $112,000 → Drawdown = -25.89%
  → THRESHOLD BREACHED — trigger action protocol
```

**Action protocol when drawdown exceeds -25%:**

This is the **one discretionary override** in the entire system. The portfolio manager must choose one of the following:

| Option | Action | When to Use |
|--------|--------|-------------|
| **A: Reduce exposure** | Sell 50% of all positions, hold cash until next rebalance | Prolonged market decline, systematic risk concerns |
| **B: Full liquidation** | Sell all positions, move to 100% cash | Extreme crisis, liquidity concerns, personal risk tolerance exceeded |
| **C: Continue with heightened monitoring** | Maintain all positions, monitor daily, reassess at next rebalance | Believe the drawdown is temporary, confident in recovery |

**Critical requirements:**

1. Document the decision in writing with date and rationale.
2. If Option A or B is chosen, the re-entry rule is: resume full position sizing at the next monthly rebalance after the portfolio has recovered above the -15% drawdown level (relative to the same peak).
3. Do NOT partially reduce exposure in an ad hoc manner. Either reduce 50%, liquidate fully, or hold. Half-measures create tracking error without meaningfully reducing risk.

**Historical context:** The backtest maximum drawdown was -22.68%. The -25% threshold provides a small buffer above the worst observed drawdown. Breaching this level would represent behavior outside historical norms and warrants intervention.

### 7.2 Position-Level Stop Loss

**The strategy does NOT use individual stop losses.**

Positions are held until the next monthly rebalance regardless of individual performance. If a single stock drops 30% or even 50% intra-month, it is still held.

**Rationale:**

- Monthly rebalancing naturally exits losers that fall out of the top 25 (their momentum score degrades, triggering a SELL signal).
- Individual stop losses in small-cap stocks frequently trigger on noise (wide bid-ask spreads, low liquidity intraday moves) and then the stock recovers.
- The backtest was validated without individual stop losses. Adding them would change the strategy's risk-return profile in untested ways.
- Losing trades average -13.12% and are held for an average of 34 days. The monthly rebalance cycle naturally limits loss duration.

**Exception:** If a stock is halted, delisted, or subject to a material corporate event (acquisition, bankruptcy), see Section 12 for handling procedures.

### 7.3 No Intra-Month Trading

Between monthly rebalances, the portfolio is frozen. No trading occurs regardless of:

- Market crashes or rallies
- Individual stock news (earnings surprises, analyst upgrades/downgrades)
- Macro events (Fed decisions, geopolitical events)
- Emotional impulse (fear or greed)

The only exception is the -25% drawdown override described in Section 7.1.

---

## 8. Rebalancing Mechanics — Detailed

### Full Rebalancing Process

At each monthly rebalance, perform these calculations for every existing HOLD position:

```
Step 1: Calculate total portfolio value
  total_value = sum(shares_i * price_i for all positions) + cash_balance

Step 2: Calculate current weight for each position
  weight_i = (shares_i * price_i) / total_value

Step 3: Calculate target weight
  target_weight = 1 / number_of_positions  (0.04 for 25 stocks, 0.10 for 10 stocks)

Step 4: Calculate drift for each position
  drift_i = weight_i - target_weight

Step 5: Apply minimum trade threshold
  if abs(drift_i) < 0.005 (0.5%):
    action = SKIP (no trade needed)
  elif drift_i > 0.005:
    action = TRIM
    trim_value = drift_i * total_value
    shares_to_sell = floor(trim_value / price_i)
  elif drift_i < -0.005:
    action = ADD
    add_value = abs(drift_i) * total_value
    shares_to_buy = floor(add_value / price_i)
```

### Minimum Trade Threshold: 0.5% Drift

**Why 0.5%?** Transaction costs are approximately 10 bps (0.10%) per trade. A rebalancing trade on a 0.3% drift generates a $30 trade on a $100K portfolio to correct a $300 misallocation. After transaction costs, the benefit is negligible. The 0.5% threshold ensures rebalancing trades are large enough to be worth the cost.

**Practical impact:** On a $100K portfolio, 0.5% = $500. Positions within $500 of their target allocation are left alone.

### Net Rebalancing

Where possible, combine rebalancing flows:

```
Example:
  Stock A: Over-weight by $800 → SELL $800 worth
  Stock B: Under-weight by $600 → BUY $600 worth
  Stock C: Under-weight by $200 → Below threshold, SKIP

  Net cash from rebalancing: $800 - $600 = $200 retained as cash
  Total rebalancing trades: 2 (not 3)
```

### Rebalancing Priority

When cash is limited (not enough to bring all underweight positions to target):

1. **First:** Trim all positions above 6% (winner trimming is mandatory).
2. **Second:** Use trim proceeds + available cash to add to the most underweight positions first.
3. **Third:** If cash is still insufficient, accept slight underweights for the least-drifted positions.

---

## 9. Signal Interpretation Guide

### Signal Definitions

| Signal | Meaning | Action | Typical Count |
|--------|---------|--------|---------------|
| **BUY** | Stock entered the top 25 this month. It was not in the portfolio last month. Strong composite score across all 4 factors, passes all quality filters. | Initiate a new 4% position. | ~7 per month |
| **SELL** | Stock dropped out of the top 25. Either momentum faded, fundamentals deteriorated, or better candidates emerged. | Exit the entire position. Sell all shares. | ~7 per month |
| **HOLD** | Stock remains in the top 25. Fundamentals and momentum still strong. | Keep position. Rebalance to 4% if drifted beyond threshold. | ~18 per month |

### Expected Monthly Turnover

- **Historical average turnover:** ~28% per month (about 7 positions change each month).
- **Range:** 3-12 changes per month is normal. Fewer than 3 suggests a very stable ranking period. More than 12 suggests a regime shift or high market volatility.
- **Annual trades:** ~139 trades per year (from backtest statistics).

### Signal Validation Checks

Before executing trades, verify:

1. **SELL count + HOLD count = last month's position count.** If not, a stock was missed or double-counted.
2. **BUY count + HOLD count = 25** (or your target number of positions). This confirms the new portfolio is fully populated.
3. **No stock appears in both BUY and SELL lists.** If it does, there is a data or logic error.
4. **No stock appears in both BUY and HOLD lists.** A BUY must be a new entry, not an existing hold.
5. **All BUY stocks pass quality filters.** Spot-check: EPS growth >= 5%, revenue growth >= 5%, price >= 75% of 52-week high.
6. **All SELL stocks actually fell below rank 25.** Cross-reference with the full ranked list.

If any check fails, halt execution and investigate the pipeline output before trading.

---

## 10. Record Keeping

### Trade-Level Records

For every trade executed, record:

| Field | Example |
|-------|---------|
| Date | 2026-03-03 |
| Ticker | RIOT |
| Signal | BUY |
| Action | BUY |
| Shares | 320 |
| Price | $12.50 |
| Total Value | $4,000.00 |
| Commission/Fees | $0.40 (estimated) |
| Target Weight | 4.00% |
| Actual Weight | 3.98% |
| Notes | New position, market order filled at open |

### Position-Level Tracking

Maintain a running ledger for each position:

```
Ticker: RIOT
Entry date: 2026-03-03
Entry price: $12.50
Entry shares: 320
Cost basis: $4,000.00

Monthly updates:
  2026-04-01: Price $14.20, Value $4,544, Weight 4.3%, Action: HOLD
  2026-05-01: Price $11.80, Value $3,776, Weight 3.6%, Action: HOLD, ADD 20 shares
  2026-06-01: Price $9.50, Value $3,230, Weight 3.1%, Action: SELL (dropped from top 25)

Exit date: 2026-06-02
Exit price: $9.45
Exit shares: 340
Exit proceeds: $3,213.00
P&L: $3,213.00 - $4,236.00 = -$1,023.00 (-24.1%)
Holding period: 91 days
```

### Portfolio-Level Metrics (Update Weekly)

| Metric | How to Calculate | Frequency |
|--------|------------------|-----------|
| NAV (Net Asset Value) | Sum of all position values + cash | Weekly |
| Portfolio Return (period) | (Current NAV - Start NAV) / Start NAV | Weekly |
| Return vs. SPY | Portfolio return - SPY return (same period) | Monthly |
| Return vs. IJR | Portfolio return - IJR return (same period) | Monthly |
| Current Drawdown | (Current NAV - Peak NAV) / Peak NAV | Weekly |
| Peak NAV (high-water mark) | max(all historical NAVs) | Updated when new peak reached |
| Sector Weights | Sum of position values per sector / Total NAV | Monthly |
| Cash Balance | Uninvested cash as % of NAV | Monthly |
| Number of Positions | Count of open positions | Monthly |

### Monthly Report Fields

At the end of each month, compile:

```
Monthly Report — [Month Year]
================================
Portfolio Value (start):  $______
Portfolio Value (end):    $______
Monthly Return:           _____%
YTD Return:               _____%
Since Inception Return:   _____%

Benchmark Comparison:
  SPY (month):            _____%
  IJR (month):            _____%
  Alpha vs SPY:           _____%
  Alpha vs IJR:           _____%

Risk Metrics:
  Current Drawdown:       _____%
  Peak Value:             $______
  Peak Date:              ______

Trades Executed:
  Sells: ____ trades, $______ proceeds
  Buys:  ____ trades, $______ invested
  Rebalances: ____ trades
  Total commissions: $______

Sector Weights:
  Technology:     _____%
  Healthcare:     _____%
  Industrials:    _____%
  [etc.]

Positions (25):
  [Ranked list with ticker, weight, month return, total return, days held]
```

---

## 11. Tax Considerations

### Short-Term Capital Gains

Monthly rebalancing generates frequent short-term capital gains (positions held less than 1 year are taxed at ordinary income rates).

**Key statistics from backtest:**

- Average holding period: **44 days** (well under the 1-year long-term threshold)
- Winners average: **56 days** held
- Losers average: **34 days** held
- Monthly turnover: **28%** (about 7 positions change per month)

Virtually all gains will be taxed as short-term. Plan accordingly.

### Cost Basis Methods

Choose one method and apply it consistently:

| Method | Description | Best For |
|--------|-------------|----------|
| **FIFO (First In, First Out)** | Oldest shares sold first | Simple, default for most brokers |
| **Specific Identification** | Choose which lots to sell | Tax optimization (sell highest-cost lots first to minimize gains) |
| **Average Cost** | Average cost of all shares | Simple for positions with many add-on purchases |

**Recommendation:** Use specific identification if your broker supports it. This allows selling higher-cost lots first when trimming winners, reducing the taxable gain.

### Tax-Loss Harvesting Opportunities

- At year-end (December rebalance), review positions with unrealized losses.
- If a stock is a HOLD signal but has a significant unrealized loss, consider selling it for the tax loss and immediately repurchasing (note: wash sale rule applies if repurchased within 30 days of the same or "substantially identical" security).
- Because the strategy naturally rotates positions monthly, many losing positions will already be sold (SELL signal) before year-end, generating realized losses organically.
- Net short-term losses can offset short-term gains dollar for dollar, plus up to $3,000 of ordinary income per year.

### Tax Record Requirements

Maintain for each tax year:

- Complete list of all trades with dates, shares, prices, and cost basis
- Realized gain/loss per trade (short-term vs. long-term classification)
- Summary of total realized gains and losses by category
- Wash sale adjustments (if any)
- 1099-B reconciliation with broker statements

### Consult a Tax Professional

This guide provides general awareness, not tax advice. Individual circumstances vary significantly. Consult a qualified tax advisor for:

- Estimated tax payments (to avoid underpayment penalties)
- State tax implications (vary by state)
- Tax-advantaged account usage (IRA, 401k) to shelter short-term gains
- Entity structure considerations for larger portfolios

---

## 12. Common Operational Scenarios

### Scenario 1: A portfolio stock gets acquired mid-month

**Situation:** Company XYZ receives a buyout offer at $35/share. Stock jumps to $34.50 and trading is halted pending deal closure.

**Action:**

1. If the stock is still trading (deal announced but not closed): **Do nothing.** Hold until next monthly rebalance. The acquisition premium is already priced in. At the next rebalance, the stock will likely receive a SELL signal (momentum calculation disrupted, or it may exceed the $10B market cap filter).
2. If trading is halted and shares are converted to cash: Record the forced sale at the conversion price. Treat proceeds as cash until the next monthly rebalance, then allocate to new BUY signals.
3. If the deal is a stock-for-stock merger: You will receive shares of the acquirer. If the acquirer is outside the small-cap universe ($50M-$10B), sell the acquirer shares at next rebalance and reallocate.

**Do NOT** try to front-run the acquisition or make discretionary trades. Let the monthly rebalance handle it.

### Scenario 2: A stock gets halted

**Situation:** Stock ABC is halted by the exchange (SEC investigation, pending news, volatility circuit breaker).

**Action:**

1. **Short-term halt (hours to days):** Wait. Most halts resolve within the same trading day or within a few days. If the halt occurs during your Day 1-3 execution window, execute all other trades and wait for the halt to lift before executing the ABC trade.
2. **Extended halt (weeks):** If the stock is halted beyond your execution window:
   - If it is a SELL signal: Place a sell order to execute whenever trading resumes. Allocate the expected proceeds to cash until then.
   - If it is a HOLD signal: Leave the position as-is. Do not attempt to sell in an OTC or grey market.
   - If it is a BUY signal: Skip this stock and either hold cash or add the allocation to the next-highest-ranked stock not already in the portfolio.
3. **Permanent delist:** Write off the position value. Record a realized loss of the full cost basis. At next rebalance, the slot will be filled by the next qualifying stock.

### Scenario 3: You miss the Day 1-3 execution window

**Situation:** You were unable to execute trades during the first three trading days of the month (travel, illness, technical issue).

**Action:**

1. **Day 4-5:** Execute as soon as possible. The signal is still valid. Performance will deviate slightly from the idealized backtest due to price drift, but one month's delayed execution has minimal long-term impact.
2. **Day 6-10:** Execute but with awareness that prices have moved. Calculate position sizes using current prices (not Day 1 prices). Accept that this month's entry/exit prices will differ from model assumptions.
3. **After Day 10:** Skip this month's rebalance entirely. Hold current positions until the next monthly rebalance. A skipped month is far better than trading on stale signals. Document the skip.

**Prevention:** Set a calendar reminder for the first trading day of every month. Have a backup person or process in case of unavailability.

### Scenario 4: Insufficient cash for all BUY signals

**Situation:** The monthly rebalance generates 8 SELL signals and 8 BUY signals, but after selling, available cash only covers 6 of the 8 new BUY positions.

**Action:**

1. First, check whether HOLD positions can be trimmed (above 6% or above 4.5%) to generate additional cash.
2. If still insufficient, prioritize BUYs by composite score rank. Buy the highest-ranked new signals first.
3. For the remaining unfunded BUY signals, either:
   - **(Preferred)** Slightly underweight all new positions proportionally so every BUY gets some allocation. Example: if you have $28,000 for 8 buys, allocate $3,500 each instead of $4,000.
   - **(Alternative)** Fund the top 6 at full 4% weight and skip the bottom 2. Add them at the next rebalance if they remain in the top 25.
4. Document which positions were underfunded and why.

**Root cause investigation:** Persistent cash shortages suggest the portfolio has accumulated losses (total value declining) or the position sizing is miscalculated. Recheck total portfolio value.

### Scenario 5: Fewer than 25 qualified stocks

**Situation:** The screening pipeline produces only 22 stocks that pass all quality filters and rank in the top 25.

**Action:**

1. This is extremely rare. The universe of ~2,000 small-caps typically produces 350-400 qualified candidates after filtering.
2. If it occurs, hold only the qualified stocks (22 in this example) at roughly equal weight (4.55% each for 22 positions).
3. Hold the remaining cash (3 positions' worth = ~12%) uninvested until the next rebalance.
4. Document the situation. If it persists for multiple months, it may indicate the quality filters are too restrictive given current market conditions — but do NOT relax filters without formal methodology review.

### Scenario 6: Market crisis (circuit breaker day)

**Situation:** The market drops 7%+ intra-day, triggering a Level 1 circuit breaker (15-minute halt), or a Level 2 halt (13% drop), on one of your execution days.

**Action:**

1. **Do not panic trade.** If you have not yet started executing, wait until the next trading day. Circuit breaker days often see wild intraday swings that reverse.
2. If you have partially executed (some SELLs done, BUYs pending), pause. Complete remaining trades on Day 2 or Day 3 when volatility subsides.
3. Check the -25% drawdown threshold (Section 7.1). If the portfolio breaches -25% on this day, invoke the drawdown action protocol.
4. If the month-start falls on a multi-day crash (e.g., 3+ consecutive large down days), it is acceptable to delay the full execution window to Day 3-5. The signals remain valid; you are only adjusting execution timing for prudent risk management.

### Scenario 7: A BUY signal stock has earnings the same week

**Situation:** One of your BUY signal stocks reports quarterly earnings on Day 2 of the month, right in your execution window.

**Action:**

1. Execute the BUY as planned. The strategy is systematic and does not account for earnings timing.
2. The composite score already incorporates the most recent available EPS and revenue data. The upcoming earnings release will be reflected in next month's signal.
3. Do NOT delay the purchase to "wait and see" the earnings result. This is discretionary intervention and violates the systematic approach.
4. If you are uncomfortable, recognize this as a feature of small-cap investing. Approximately 4-5 of your 25 positions will have earnings in any given month.

### Scenario 8: Broker issues prevent order execution

**Situation:** Your broker platform is down, or orders are rejected due to a technical issue.

**Action:**

1. Contact your broker immediately to resolve the issue.
2. If resolution takes more than a day, use a backup brokerage account (if available) or place orders by phone.
3. If execution is delayed beyond Day 3, follow the guidance in Scenario 3.
4. Document the broker issue, any price discrepancy from the intended execution, and the resolution.

---

## 13. Monthly Implementation Checklist

Print this checklist and complete it each month. File with your monthly records.

```
EMERGING GROWTH STRATEGY — MONTHLY EXECUTION CHECKLIST
=======================================================
Month: ____________  Year: ____________

PRE-EXECUTION (Day 1, Pre-Market)
---------------------------------
[ ] Run screening pipeline (universe filter → factor calc → quality filter → scoring → ranking)
[ ] Verify data freshness:
    [ ] Price data current through prior trading day close
    [ ] Fundamental data reflects most recent quarterly filings
    [ ] No stale or missing data for any stocks in the top 50
[ ] Generate BUY/SELL/HOLD signal list
[ ] Verify signal counts:
    SELL count: ____  +  HOLD count: ____  =  Last month's positions: ____  (must match)
    BUY count:  ____  +  HOLD count: ____  =  25  (must equal target)

SIGNAL REVIEW (Day 1, Market Open)
-----------------------------------
[ ] Cross-check: No stock in both BUY and SELL, or BUY and HOLD
[ ] Spot-check 3-5 BUY stocks: confirm quality filters pass (EPS>=5%, Rev>=5%, Price>=75% of high)
[ ] Review for obvious errors:
    [ ] No delisted or halted stocks in BUY list
    [ ] No extremely low-volume stocks (< $200K avg daily volume)
    [ ] Composite scores look reasonable (no extreme outliers suggesting data errors)
[ ] Check sector concentration: No sector > 40% of 25 positions
    If exceeded, apply replacement procedure (Section 6)
    Sector adjustments made: ____________________________________________

POSITION SIZING (Day 1)
------------------------
[ ] Record total portfolio value: $____________
[ ] Calculate per-position allocation: $____________ / 25 = $____________
[ ] Calculate shares for each BUY stock
[ ] Calculate trim/add amounts for each HOLD stock
[ ] Verify sufficient cash for all planned trades (after SELLs fund BUYs)

REPORT DISTRIBUTION (Day 1, Morning)
--------------------------------------
[ ] Prepare monthly report (PDF + CSV)
[ ] Distribute to all subscribers
[ ] Include: signal list, composite scores, sector breakdown, execution guidance

TRADE EXECUTION
---------------
Step 1 — SELLs (Day 1-2):
[ ] Execute all SELL orders
    Total SELL trades: ____
    Total proceeds: $____________
    All fills confirmed: [ ] Yes  [ ] Partial (explain: _________________)

Step 2 — BUYs (Day 1-3):
[ ] Execute all BUY orders
    Total BUY trades: ____
    Total invested: $____________
    All fills confirmed: [ ] Yes  [ ] Partial (explain: _________________)

Step 3 — REBALANCE (Day 2-3):
[ ] Check all HOLD positions for weight drift
[ ] Trim positions above 6% weight
    Stocks trimmed: ____________________________________________
[ ] Add to positions below 3.5% weight (if cash available)
    Stocks added to: ____________________________________________
[ ] Positions skipped (drift < 0.5%): ____

POST-EXECUTION VERIFICATION (Day 3)
-------------------------------------
[ ] All trades recorded in trade log
[ ] Current portfolio matches target (25 positions near 4% each)
[ ] No sector exceeds 40%
[ ] Cash balance: $____________ (____________% of portfolio)
[ ] Updated portfolio tracker with new positions and weights
[ ] Calculate current performance metrics:
    Month-to-date return:    _____%
    Year-to-date return:     _____%
    Current drawdown:        _____% (from peak of $____________)

RISK CHECK
----------
[ ] Drawdown within -25% threshold: [ ] Yes  [ ] No → invoke action protocol
[ ] No single position > 6% weight
[ ] No sector > 40% concentration

SIGN-OFF
--------
Executed by: ________________________
Date completed: ____________
Notes: ________________________________________________________________
_______________________________________________________________________
```

---

## Appendix A: Quick Reference Card

Keep this summary accessible during execution:

```
EMERGING GROWTH STRATEGY — QUICK REFERENCE
============================================
Positions:       25 stocks, equal weight (4% each)
Rebalance:       Monthly, Day 1-3
Signal types:    BUY (new entry) | SELL (full exit) | HOLD (keep, rebalance)
Execution order: SELL → BUY → REBALANCE
Order type:      Market orders (small-cap liquidity priority)
Winner trim:     Cut back to 4% if any position exceeds 6%
Sector cap:      Max 40% in any single GICS sector
Drawdown limit:  -25% triggers discretionary override
Rebalance skip:  Don't trade if drift < 0.5%
Turnover:        ~28%/month (~7 changes)
Cost assumption: ~10 bps per trade
Intra-month:     NO TRADING (hold until next rebalance)
```

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **NAV** | Net Asset Value. Total portfolio value including cash. |
| **Drawdown** | Decline from peak portfolio value, expressed as a negative percentage. |
| **High-water mark** | The highest NAV ever achieved. Used to calculate drawdown. |
| **Drift** | Difference between a position's current weight and its target weight. |
| **GICS** | Global Industry Classification Standard. The standard sector taxonomy used by MSCI and S&P. |
| **Turnover** | Percentage of the portfolio that changes in a given period. 28% monthly means ~7 of 25 positions rotate. |
| **Slippage** | The difference between expected execution price and actual fill price. More common in small-cap stocks. |
| **Wash sale** | IRS rule: if you sell a security at a loss and repurchase the same or substantially identical security within 30 days, the loss is disallowed for tax purposes. |
| **Cost basis** | The original purchase price of a security, used to calculate gain/loss on sale. |
| **Circuit breaker** | Exchange-mandated trading halt triggered by large market declines (7%, 13%, or 20% drops in S&P 500). |
| **Window dressing** | Practice of institutional funds buying recent winners and selling losers near quarter/month-end to improve reported holdings. |
| **Alpha** | Portfolio return in excess of the benchmark return. |
| **Profit factor** | Ratio of gross profits to gross losses across all trades. Values above 1.0 indicate a profitable system. |
