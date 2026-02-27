# Emerging Growth Strategy — Complete Specification

> **A Quantitative Approach to Small-Cap Momentum Investing**
> Presented by: AlgoGators Investment Fund
>
> Student-managed research with institutional-grade validation, delivering systematic small-cap stock selection through a proven four-factor methodology combining momentum, growth fundamentals, and technical strength indicators.

**Headline Metrics:** 11 Years Backtested (2014-2024) | 428% Total Return | 1,535 Trades Analyzed | 16.66% CAGR

---

## Table of Contents

1. [Research Overview](#1-research-overview)
2. [Universe Definition](#2-universe-definition)
3. [Data Collection](#3-data-collection)
4. [Four-Factor Composite Scoring Model](#4-four-factor-composite-scoring-model)
5. [Quality Filters](#5-quality-filters)
6. [Portfolio Construction](#6-portfolio-construction)
7. [Monthly Research Process](#7-monthly-research-process)
8. [Eleven-Year Performance Results](#8-eleven-year-performance-results)
9. [Year-by-Year Performance Analysis](#9-year-by-year-performance-analysis)
10. [Statistical Validation Framework](#10-statistical-validation-framework)
11. [Trade Statistics](#11-trade-statistics)
12. [Validation Methodology](#12-validation-methodology)
13. [Strategy Comparisons](#13-strategy-comparisons)
14. [Academic and Industry Context](#14-academic-and-industry-context)
15. [Implementation Guidance](#15-implementation-guidance)
16. [Research Deliverables](#16-research-deliverables)
17. [Risk Disclosure and Limitations](#17-risk-disclosure-and-limitations)
18. [Data and Technology Infrastructure](#18-data-and-technology-infrastructure)
19. [Current Portfolio Snapshot](#19-current-portfolio-snapshot)
20. [Continuous Improvement and Monitoring](#20-continuous-improvement-and-monitoring)
21. [Questions and Discussion](#21-questions-and-discussion)
22. [Statistical Appendix](#22-statistical-appendix)

---

## 1. Research Overview

### Study Objective

To develop and validate a systematic small-cap stock selection methodology that combines momentum factors with fundamental growth metrics, technical strength indicators, and rigorous quality filters to generate consistent alpha across diverse market regimes.

The research framework integrates: relative strength analysis, earnings acceleration, revenue growth validation, and proximity to 52-week highs into a unified composite scoring system.

### Research Questions

1. Can momentum and growth factors be synergistically combined to generate statistically significant alpha in small-cap equities?
2. Does the methodology demonstrate robust performance across different market regimes including bull markets, corrections, and bear markets?
3. Does the strategy provide risk-adjusted returns superior to established benchmarks while maintaining acceptable drawdown characteristics?

---

## 2. Universe Definition

Start with approximately **2,000 US small-cap stocks**. Apply these filters:

| Filter | Threshold |
|---|---|
| Market Capitalization | $50M — $10B |
| Exchanges | NASDAQ, NYSE, NYSE American |
| Average Daily Volume | Minimum $500K |
| Share Price | Minimum $2.00 (excludes penny stocks) |

**Rationale:** Provides exposure to emerging growth opportunities with institutional-quality standards while maintaining sufficient liquidity for implementation.

---

## 3. Data Collection

| Data Type | Lookback | Source |
|---|---|---|
| OHLC price data | 15 months (for 52-week high calculations) | Sharadar |
| Quarterly fundamental reports (EPS + revenue) | 2 years | Sharadar |

**Sharadar institutional-grade database** ensures point-in-time accuracy, eliminating look-ahead bias and survivorship bias for robust backtesting validation.

---

## 4. Four-Factor Composite Scoring Model

### Formula

```
Composite Score = 0.40 × RS Percentile
               + 0.20 × min(EPS Growth, 100)
               + 0.20 × min(Revenue Growth, 100)
               + 0.20 × Price vs 52-Week High
```

### Factor 1: Relative Strength Percentile — Weight: 40%

- **Calculation:** Six-month price momentum ranked against the entire investable universe on a 0-100 scale.
- **Interpretation:** A score of 100 = strongest momentum relative to all peers.
- **Rationale:** Captures market leadership and institutional accumulation patterns. Stocks with sustained upward price trends often persist for 3-12 additional months per momentum persistence research.
- **Academic basis:** Jegadeesh & Titman (1993-2001) momentum effect.

### Factor 2: EPS Growth Year-over-Year — Weight: 20%

- **Calculation:** Compare most recent quarterly EPS against same quarter four periods prior.
- **Special turnaround scoring:** Assigns 999% to companies transitioning from negative to positive earnings, capturing inflection points that often precede substantial price appreciation.
- **Minimum threshold:** 5% ensures quality.
- **Rationale:** Reveals earnings acceleration trends.
- **Academic basis:** Chan, Jegadeesh & Lakonishok (1996) earnings momentum.

### Factor 3: Revenue Growth Year-over-Year — Weight: 20%

- **Calculation:** Top-line sales growth comparison year-over-year.
- **Requirement:** Positive revenue base required.
- **Rationale:** Less volatile fundamental validation than earnings alone. Confirms genuine business expansion rather than accounting-driven earnings manipulation. Validates earnings growth stems from organic business strength rather than cost-cutting or financial engineering.

### Factor 4: Price vs 52-Week High — Weight: 20%

- **Calculation:** Current price as percentage of highest price over trailing 252 trading days.
- **Interpretation:** Stocks trading at 90-100% of highs demonstrate technical leadership. Proximity to 52-week highs signals institutional accumulation and breakout potential.
- **Minimum threshold:** 75% filter ensures we avoid deeply depressed securities.
- **Academic basis:** George & Hwang (2004) 52-week high effect.

---

## 5. Quality Filters

**All criteria must pass simultaneously:**

| Filter | Threshold |
|---|---|
| EPS Growth YoY | >= 5% |
| Revenue Growth YoY | >= 5% |
| Price vs 52-Week High | >= 75% |

**Effect:** Reduces universe from ~2,000 stocks to **350-400 qualified candidates**, ensuring only high-quality emerging growth stocks with confirmed momentum reach the final ranking stage.

---

## 6. Portfolio Construction

- Select **top 25 stocks** by composite score (descending order).
- **Equal weighting** at 4% per position.
- **Monthly rebalancing** — disciplined systematic approach with zero discretionary intervention.
- Generate BUY signals for new stocks entering top 25, SELL signals for stocks dropped, HOLD for continuing positions.
- Include rebalancing guidance to maintain 4% equal weights.

---

## 7. Monthly Research Process

### Step-by-Step Pipeline

1. **Universe Definition** — Start with ~2,000 US small-cap stocks, apply market cap / exchange / volume / price filters.
2. **Data Collection** — Extract 15 months OHLC price data + 2 years quarterly fundamentals from Sharadar.
3. **Calculate Metrics** — Compute RS Percentile (6-month momentum), EPS Growth (latest quarter vs year ago), Revenue Growth YoY, Price vs 252-day High.
4. **Apply Quality Filters** — Remove stocks failing any of: EPS growth <5%, revenue growth <5%, price <75% of 52-week high. Result: ~350-400 qualified stocks.
5. **Composite Score** — Calculate weighted score: 40% RS + 20% min(EPS,100) + 20% min(Rev,100) + 20% Price vs High.
6. **Rank and Select** — Sort descending, select top 25, apply equal 4% weighting.
7. **Generate Report** — BUY/SELL/HOLD signals with rebalancing guidance.

### Implementation Timeline

| When | Action |
|---|---|
| Day 1 (Market Open) | Run ranking calculations and quality checks |
| Day 1 (Morning) | Distribute monthly report to all subscribers |
| Day 1-3 | Subscribers execute trades during optimal window |
| Rest of Month | Hold positions unchanged until next rebalance |

This process is **100% systematic** with zero discretionary intervention.

---

## 8. Eleven-Year Performance Results

### Validated Backtest Performance (2014-2024)

| Metric | Strategy | S&P 500 (SPY) | Small-Cap (IJR) |
|---|---|---|---|
| Total Return | **428.84%** | 200.33% | ~180% |
| CAGR | **16.66%** | 11.18% | ~10% |
| Sharpe Ratio | **1.054** | 0.89 | ~0.75 |
| Sortino Ratio | **1.788** | 1.21 | ~1.10 |
| Maximum Drawdown | **-22.68%** | -33.72% | ~-35% |
| Calmar Ratio | **0.73** | 0.33 | -0.28 |
| Profitable Years | **11/11 (100%)** | 9/11 (82%) | 8/11 (73%) |

### Key Highlights

- **2.14x Outperformance** — More than double the S&P 500 return over full 11-year period.
- **Superior Risk Protection** — Lower max drawdown than both benchmarks.
- **Perfect Win Record** — Positive returns in all 11 calendar years including 2022 bear market.
- **Consistent Alpha Generation** — Risk-adjusted metrics exceed benchmarks across Sharpe, Sortino, and Calmar.

---

## 9. Year-by-Year Performance Analysis

| Year | Return | Sharpe | Market Regime | Performance Notes |
|---|---|---|---|---|
| 2024 | 15.30% | 0.91 | Bull Market Recovery | Solid performance in normalized conditions |
| 2023 | 9.10% | 0.73 | Post-Bear Recovery | Federal Reserve pivot catalyst |
| 2022 | **6.37%** | 0.42 | **Bear Market** | **Positive while SPY fell -18%** |
| 2021 | 26.90% | 1.24 | Post-COVID Bull | Strong momentum environment |
| 2020 | 23.26% | 1.05 | COVID Crash/Recovery | Resilient through volatility |
| 2019 | **29.53%** | **2.50** | Low Volatility Bull | **Best absolute performance year** |
| 2018 | 20.16% | 1.31 | Market Correction | Strong relative performance |
| 2017 | 25.30% | 2.03 | Tax Reform Bull | Excellent risk-adjusted returns |
| 2016 | 6.90% | 0.77 | Election Uncertainty | Defensive positioning effective |
| 2015 | 9.52% | 0.82 | Oil Price Crash | Steady through commodity crisis |
| 2014 | 11.18% | 0.84 | Backtest Base Year | Solid initial performance |

### Summary Stats

- **100% Yearly Win Rate** — Positive returns all 11 years
- **25% Bull Market Capture** — Average return in strong market years
- **8% Bear Market Defense** — Average return during challenging years

The 2022 performance is particularly notable: +6.37% while S&P 500 declined -18%. This defensive characteristic during bear markets, combined with 25-30% returns during bull markets, creates a powerful asymmetric return profile that compounds wealth over time.

---

## 10. Statistical Validation Framework

### Sample Characteristics

| Metric | Value |
|---|---|
| Total Trades | 1,535 |
| Annual Average | 139 trades |
| Monthly Rebalances | 132 events |
| Avg Duration | 44 days |
| Win Rate | 50.36% |
| Profit Factor | 1.80 |

### Sharpe Ratio T-Test

- **Null Hypothesis (H0):** Sharpe ratio = 0 (no skill, random returns)
- **Alternative Hypothesis (H1):** Sharpe ratio > 0 (skill-based returns)
- **Test Statistic:** t = 55.69 (extraordinarily significant)
- **Degrees of Freedom:** 2,788 trading days
- **P-value:** < 0.000001 (essentially zero probability)
- **Conclusion:** Reject null hypothesis with 99.9999% confidence level

### Bootstrap Confidence Intervals (10,000 iterations)

| Metric | 95% Confidence Interval |
|---|---|
| Sharpe Ratio | [0.460, 1.651] — lower bound excludes zero |
| Total Return | [92.6%, 1,316.2%] — wide range but consistently positive |
| Sortino Ratio | [0.593, 2.287] — strong downside protection validated |

### Subperiod Consistency Analysis

| Period | Sharpe Ratio | Total Return |
|---|---|---|
| 2014-2019 | 1.269 | 125.51% |
| 2019-2024 | 0.943 | 134.51% |

Both subperiods demonstrate Sharpe ratios above 0.9, confirming consistent performance across different market regimes rather than period-specific luck.

### Statistical Conclusion

The probability that these results occurred by random chance is less than **0.0001%**. This demonstrates skill-based alpha generation through systematic factor selection, not statistical noise or data mining. The strategy exhibits genuine predictive power validated through multiple independent statistical frameworks.

---

## 11. Trade Statistics

| Metric | Winners | Losers |
|---|---|---|
| Number of Trades | 773 (50.36%) | 762 (49.64%) |
| Average Return | +25.06% | -13.12% |
| Average Hold Period | 56 days | 34 days |
| Best/Worst Trade | +492.97% | -85.59% |
| Expectancy per Trade | +$279 average | — |

**Key insight:** Win rate is only ~50%, but winners are nearly 2x the size of losers (+25% vs -13%), and winners are held longer (56 vs 34 days). The edge comes from asymmetric payoffs, not prediction accuracy.

---

## 12. Validation Methodology

### What We Did RIGHT

1. **Large Sample Size** — 1,535 total trades across 11 years. Average of 139 trades per year ensures consistent activity rather than sporadic cherry-picked examples.

2. **Out-of-Sample Parameters** — Factor weights and thresholds derived from separate 2025 overlap study. No re-optimization during backtest period. Fixed methodology applied consistently across entire 11-year timeframe.

3. **Point-in-Time Data Integrity** — Sharadar database ensures no look-ahead bias with proper fundamental data lags. No survivorship bias as universe updates monthly. Transaction costs of 10 basis points included per trade.

4. **Multiple Statistical Tests** — T-test validates statistical significance. Bootstrap resampling confirms robustness. Subperiod analysis proves consistency. Multiple market regime validation.

5. **Simple Transparent Model** — Only four core factors reduces overfitting risk. Clear economic rationale aligns with academic research. Fully disclosed methodology enables reproducibility and peer review.

### What We AVOIDED

1. **Overfitting** — Did NOT test hundreds of parameter combinations and select the best result. Used fixed parameters from independent prior research to prevent curve-fitting to historical data.

2. **Data Snooping** — Did NOT repeatedly test the same dataset until finding favorable results. Conducted single comprehensive backtest with pre-defined methodology and parameters.

3. **Cherry-Picking Time Periods** — Did NOT select only favorable market conditions or exclude difficult periods. Used complete 11-year span including 2022 bear market and various regime types.

4. **Unrealistic Assumptions** — Did NOT assume zero transaction costs, perfect execution, or unlimited liquidity. Included realistic 10 bps trading costs and acknowledged slippage considerations.

---

## 13. Strategy Comparisons

### vs. S&P 500 Index

**Performance Advantages:**

1. **2.14x Superior Returns** — 428% total return vs 200% for S&P 500.
2. **Higher Annual Growth** — 16.66% CAGR vs 11.18% compounds significantly over time.
3. **Better Downside Protection** — Max drawdown -22.68% vs -33.72% for SPY.
4. **Bear Market Resilience** — Positive 6.37% in 2022 while S&P 500 fell -18%.

**Implementation Considerations:**

1. **Higher Active Management** — Monthly rebalancing required vs passive buy-and-hold.
2. **Transaction Costs** — Regular trading generates costs (built into backtest at 10 bps). Tax implications from short-term capital gains.
3. **Small-Cap Exposure** — Less liquid than large-cap. Wider spreads and execution challenges for very large accounts.

**Optimal Use Case:** Best deployed as tactical growth allocation within diversified portfolio. Complements large-cap core holdings for investors seeking enhanced returns with acceptable additional volatility.

### vs. Small-Cap Indexes (IJR)

| Metric | Strategy | IJR |
|---|---|---|
| Return Multiple | **2.38x** — 428% vs ~180% | Baseline |
| Sharpe Improvement | **40% better** — 1.054 vs ~0.75 | Baseline |
| Drawdown Improvement | **35% lower** — -22.68% vs ~-35% | Baseline |

**Key Differences:**
- **Concentration:** 25 carefully selected stocks vs 600+ in IJR — focused exposure to highest-quality names
- **Rebalancing:** Monthly systematic updates vs quarterly/semi-annual index reconstitution
- **Factor Exposure:** Explicit momentum and growth factors vs market-cap weighted passive allocation
- **Quality Filters:** Minimum 5% EPS and revenue growth thresholds exclude struggling companies

**Strategic Application:** Excellent replacement for passive small-cap index allocations within diversified portfolios. Systematic quality and momentum screens have historically produced superior risk-adjusted returns.

### vs. Active Funds and Momentum ETFs

**vs. Actively Managed Small-Cap Funds:**

| Advantage | Detail |
|---|---|
| Transparency | Fully disclosed methodology vs opaque manager discretion |
| Cost Efficiency | No management fees (1-2% typical for active funds) |
| Performance Validation | Comprehensive 11-year backtest with statistical validation |
| Educational Mission | Student-managed, academic rigor, faculty oversight |
| **Trade-off** | Self-execution required. No customization or tax-loss harvesting. |

**vs. Momentum ETFs (MTUM, etc.):**

| Advantage | Detail |
|---|---|
| Small-Cap Focus | Most momentum ETFs concentrate on large/mid-cap. Our small-cap focus captures size premium. |
| Multi-Factor Enhancement | Combines momentum with fundamental growth filters. ETFs use price momentum only. |
| Superior Historical Returns | 428% over 11 years vs ~250% for broad momentum ETFs |
| Enhanced Downside Protection | Fundamental growth filters reduce exposure to pure momentum crashes |
| **Trade-off** | Less diversified (25 stocks vs 125+ in ETFs). Monthly self-management required. |

### Comprehensive Comparison Table

| Feature | This Strategy | SPY | IJR | Active Fund | Momentum ETF |
|---|---|---|---|---|---|
| 11-Year Return | **428%** | 200% | 180% | Varies | ~250% |
| Sharpe Ratio | **1.054** | 0.89 | 0.75 | ~0.6 | ~0.8 |
| Maximum Drawdown | **-22.68%** | -33.72% | -35% | -30% | -28% |
| Annual Fees | **0%** | 0.03% | 0.04% | 1-2% | 0.15% |
| Rebalancing | Monthly | Annual | Quarterly | Varies | Quarterly |
| Transparency | **Full** | Full | Full | Low | Medium |
| Execution | Self-Directed | Passive | Passive | Managed | Passive |

---

## 14. Academic and Industry Context

### Research Citations and Alignment

| # | Year | Research | Finding | Strategy Alignment |
|---|---|---|---|---|
| 1 | 1993-2001 | Jegadeesh & Titman — Momentum Effect | Stocks with strong 3-12 month returns continue outperforming | 6-month momentum RS calculation directly aligned |
| 2 | 1993 | Fama & French — Small-Cap Premium | Small-cap stocks outperform large-caps long-term | $50M-$10B focus captures premium with sufficient liquidity |
| 3 | 1996 | Chan, Jegadeesh & Lakonishok — Earnings Momentum | Stocks with rising earnings outperform | EPS growth >=5% with turnaround bonus scoring |
| 4 | 2004 | George & Hwang — 52-Week High Effect | Proximity to 52-week highs predicts future returns | 75% minimum threshold leverages this indicator |

### Multi-Factor Diversification

Modern Portfolio Theory emphasizes combining uncorrelated factors to reduce risk while maintaining returns. Four complementary factors:

- **Price Momentum (RS):** Behavioral/technical
- **Earnings Growth:** Fundamental quality
- **Revenue Growth:** Business validation
- **Technical Strength (Price vs High):** Institutional accumulation

Diversification across factor types provides robustness when individual factors underperform temporarily.

### Industry Best Practices Alignment

- **Hedge funds:** Commonly use momentum + fundamental screens
- **Institutional investors:** Combine multiple factors for diversification
- **Quantitative managers:** Monthly rebalancing standard for small-caps
- **Academic programs:** Student-managed funds provide real-world learning

---

## 15. Implementation Guidance

### Approach 1: Full Replication — $25,000+ Portfolios (Recommended)

- **Method:** Invest in all 25 stocks with equal 4% weighting. Execute all monthly trades (SELL → BUY → HOLD). Rebalance monthly to maintain equal weights.
- **Best For:** Investors seeking exact backtest replication, comfortable with monthly activity, portfolios above $25,000, maximum diversification benefits.
- **Expected Results:** Closest match to historical 428.84% performance, full factor diversification, maximum statistical alignment with validation studies.

### Approach 2: Top 10 Concentrated — $10,000-$25,000 Portfolios

- **Method:** Invest in top 10 highest-scoring stocks at 10% each. Higher concentration increases potential volatility. Lower transaction costs due to fewer positions.
- **Best For:** Smaller portfolios ($10k-$25k), higher risk tolerance, those seeking outsized returns, reduced trading complexity.
- **Trade-offs:** Potentially higher returns but increased volatility, reduced diversification, results will differ from backtest statistics.

### Approach 3: Research Ideas — Discretionary Integration

- **Method:** Use rankings as starting point for personal analysis. Cherry-pick names based on additional criteria. Combine signals with existing strategies.
- **Best For:** Active traders with established systems, stock screening ideas, discretionary investors, portfolio enhancement.
- **Considerations:** Results will significantly differ from backtest, no statistical performance guarantees, requires substantial additional research and due diligence.

### Implementation Best Practices

**Timing Optimization:**
- Execute trades within first 3 trading days of each month
- Use market orders for small-caps (liquidity priority)
- Avoid month-end execution (window dressing effects)

**Position Sizing Discipline:**
- Start with equal 4% weight for all 25 stocks
- Rebalance quarterly minimum (monthly ideal)
- Trim winners exceeding 6% to prevent momentum traps

**Transaction Cost Planning:**
- Budget 0.10-0.15% per trade (included in backtest)
- Most brokers offer $0 commissions but ECN fees apply
- Consider tax implications of short-term capital gains

**Portfolio Risk Controls:**
- Set maximum drawdown threshold at -25% for risk management
- Diversify across sectors (max 40% per sector)
- Maintain 3-5 year investment horizon minimum
- Avoid panic selling during temporary drawdowns

---

## 16. Research Deliverables

### Monthly Portfolio Report
Professional PDF and Excel-compatible CSV containing top 25 stocks ranked by composite score. Includes individual metric breakdowns (RS, EPS, Revenue, Price/High), current scores and percentile rankings, sector distribution analysis, and market capitalization distribution.

### Trade Execution Guide
Actionable PDF with BUY list (new positions with entry guidance), SELL list (exits with performance attribution), HOLD list (continuing positions with rebalancing needs), position sizing calculator for 4% equal weight, and estimated transaction cost projections.

### Performance Tracking Dashboard
Interactive web-based dashboard: previous month portfolio performance, year-to-date returns vs benchmarks, rolling 12-month statistics, real-time drawdown monitoring, historical equity curve visualization.

### Monthly Commentary
Written analysis (2-3 pages):
- Current market environment assessment and implications
- Notable portfolio changes with quantitative reasoning
- Sector rotation observations and factor performance
- Upcoming earnings calendar for current holdings
- Risk factors and strategic considerations

### Research Archive
Comprehensive historical database:
- All historical rankings (every month available)
- Past trade reports with results and attribution
- Performance attribution by factor and period
- Complete methodology documentation
- Statistical validation reports and updates
- Downloadable in PDF and CSV formats

---

## 17. Risk Disclosure and Limitations

### Performance Disclaimer

**Past performance does not guarantee future results.** The 428.84% return represents historical backtested performance. Future results may differ significantly due to changing market conditions, momentum regime shifts, strategy crowding, black swan events, and execution differences.

### 5 Risk Categories

1. **Volatility Risk** — Max historical drawdown: -22.68%. Expect periodic declines of 15-20% as normal volatility. Recovery periods can extend 6-12 months. Emotional discipline and long-term perspective essential.

2. **Small-Cap Specific Risks** — Lower liquidity creates wider bid-ask spreads and higher price impact. Small companies face greater business risk, competitive threats, and potential bankruptcy exposure.

3. **Momentum Strategy Risks** — Performs poorly in choppy, range-bound markets. Vulnerable to sudden trend reversals and momentum crashes. Strategy correlation with other momentum approaches increases systemic risk during factor rotations.

4. **Concentration Risk** — Only 25 stocks vs 500 in S&P 500. Single stock impacts 4% of portfolio. Potential sector concentration exceeds diversified indexes. US equities only.

5. **Execution Risk** — Monthly rebalancing requires consistent discipline. Transaction costs may exceed 10 bps for larger accounts. Slippage on small-cap trades varies. Missed rebalances materially hurt long-term performance.

### Methodology Limitations

**Backtest Assumptions:**
- Perfect execution at closing prices is unrealistic in practice
- No market impact modeling for larger account sizes
- Sharadar database coverage and quality constraints
- No accounting for broker outages or operational errors

**Model Limitations:**
- Four factors only may miss other important market dynamics
- Equal weighting not optimal for all market conditions
- Fixed parameters provide no regime adaptation
- No explicit tail risk hedging or defensive positioning

### Suitable Investor Profile

**Appropriate For:**
- Portfolios $25,000+ (ideally $100,000+)
- 3-5 year minimum investment horizon
- Tolerance for -20% temporary drawdowns
- Comfortable with monthly rebalancing
- Interest in quantitative systematic strategies

**NOT Appropriate For:**
- Risk-averse or conservative investors
- Short-term traders (less than 1 year)
- Portfolios under $10,000
- Need for income or dividend generation
- Unwilling to tolerate volatility or rebalance

---

## 18. Data and Technology Infrastructure

### Sharadar Fundamental Database

| Property | Detail |
|---|---|
| Coverage | 15,000+ US equities from 1998-present |
| Frequency | Daily price data, quarterly fundamentals |
| Quality | Institutional-grade, point-in-time accuracy |
| Cost | $200/month professional subscription |
| Users | Hedge funds, quant shops, academic researchers |

Provides OHLCV price data, comprehensive fundamental metrics (EPS, revenue, margins, growth rates), corporate action adjustments, and critically important point-in-time data preventing look-ahead bias.

### VectorBT Pro Backtesting

- Professional quantitative analysis platform
- Vectorized computations for rapid performance
- Integrated portfolio simulation engine
- Built-in risk analytics and reporting
- Used by institutional trading firms

### Technology Stack

| Component | Technology |
|---|---|
| Data Storage | PostgreSQL with TimescaleDB (optimized time-series queries) |
| Processing | Python with NumPy and Pandas (numerical computations) |
| Analysis | Custom statistical framework for validation tests |
| Quality Control | Automated validation and integrity checks |

### Quality Assurance

**Data Validation:**
- Automated missing data detection
- Outlier identification with Winsorization at 1%/99% percentiles
- Corporate action adjustments for splits and dividends
- Point-in-time verification to prevent future data leaks
- Price-volume consistency cross-reference checks

**Statistical Rigor:**
- Out-of-sample parameter testing
- Multiple independent validation methods (t-test, bootstrap, subperiod analysis)
- Sensitivity analysis for parameter robustness
- Regime-specific performance evaluation
- Faculty peer review oversight

---

## 19. Current Portfolio Snapshot

> **Note:** The data shown represents example portfolio characteristics. Actual monthly portfolio updated and distributed to subscribers at the beginning of each month.

### Top 5 Holdings by Composite Score

| Rank | Ticker | Score | RS %ile | EPS Growth | Rev Growth |
|---|---|---|---|---|---|
| 1 | RIOT | 95.9 | 93 | 999% | 118% |
| 2 | ABAT | 93.7 | 99 | 380% | 166% |
| 3 | AMSC | 92.5 | 97 | 999% | 80% |
| 4 | NUVB | 92.0 | 89 | 999% | 36% |
| 5 | SIGA | 91.8 | 82 | 750% | 37% |

### Portfolio Statistics

| Metric | Value |
|---|---|
| Average Composite Score | 87.3 |
| Qualified Stocks (passing all filters) | 362 |
| Avg Market Cap (portfolio median) | $1.2B |
| Monthly Turnover | 28% (7 new positions) |

### Sector Distribution

Technology, Healthcare, Industrials, Consumer, Materials, Energy

### Recent Performance Trajectory

| Period | Return |
|---|---|
| Month | +4.2% |
| Quarter | +12.7% |
| Year-to-Date | +18.9% |
| Since Inception (2014) | +428.84% |

---

## 20. Continuous Improvement and Monitoring

### Ongoing R&D Framework

| Cadence | Activities |
|---|---|
| **Monthly** | Track absolute/relative returns, risk metrics, trade statistics, attribution analysis, data integrity validation, execution quality |
| **Quarterly** | Regime analysis, strategy health assessment, parameter stability verification, factor performance breakdown, risk assessment updates |
| **Annually** | Full year performance evaluation, methodology refinement consideration, academic research integration, technology platform upgrades |
| **Ongoing** | Identify potential improvements, research solutions, backtest modifications, faculty review, subscriber communication, post-change monitoring |

### When to Consider Changes (4 Triggers)

1. Underperformance exceeding 2 years versus benchmarks
2. Sharpe ratio drops below 0.5 sustained for 12+ months
3. Statistically significant market regime shift detected
4. Fundamental market structure changes (regulatory, technological)

These thresholds prevent overreaction to short-term variance while ensuring responsiveness to genuine structural changes.

### Disciplined Change Process — What We Explicitly Avoid

1. Parameter tweaking after bad months (overreaction)
2. Strategy abandonment during drawdowns (lack of discipline)
3. Chasing recent winners (recency bias)
4. Over-complication with excess factors (overfitting)

**Change process:** Data-driven issue identification → academically grounded solution research → out-of-sample backtest validation → faculty approval → subscriber notification before implementation → post-change performance monitoring.

---

## 21. Questions and Discussion

### Q: Why does this strategy work?
Combines momentum (behavioral finance — investors under-react to positive news) with fundamental growth analysis (quality validation). Momentum persists because behavioral biases create predictable patterns, while growth filters ensure we're selecting genuinely improving businesses rather than temporary price spikes.

### Q: Will it stop working if too many people use it?
Possible if strategy becomes excessively crowded or market structure fundamentally changes. Small-cap liquidity naturally limits total strategy capacity to approximately **$50-100M across all subscribers**. Currently well below concerning levels.

### Q: What happens during a momentum crash?
Drawdowns of ~20% are statistically normal and have occurred historically. Strategy maintains full investment (no market timing) and typically recovers over 6-12 months. Emotional discipline to hold through drawdowns is critical for capturing long-term compounding benefits.

### Q: How much capital can this strategy handle?
$50-100 million total across all subscribers. Individual accounts: minimum $25,000 for full 25-stock replication, $10,000+ for top 10 concentrated. Very large accounts above $10M may experience execution challenges and price impact.

### Q: Who should NOT use this strategy?
Risk-averse investors unable to tolerate -20% drawdowns, short-term traders (<1 year), portfolios under $10,000, investors requiring income/dividends, those emotionally unable to handle volatility, or investors unwilling to perform monthly rebalancing.

### Q: Can I modify the portfolio construction?
Yes, but results will differ materially from backtest statistics. Top 10 concentration, different weightings, or selective stock picking produce different risk-return profiles. Validation studies apply only to exact methodology (25 stocks, equal weight, monthly rebalance).

### Q: How does this differ from stock picking services?
Systematic quantitative research, not discretionary recommendations. Every decision follows pre-defined rules with no human judgment. Fully transparent, statistically validated over 11 years, and academically grounded. Most stock picking services lack rigorous backtesting and statistical validation.

---

## 22. Statistical Appendix

### Risk Metric Formulas

| Metric | Formula |
|---|---|
| Sharpe Ratio | (Annual Return - Risk-Free Rate) / Annual Volatility |
| Sortino Ratio | (Annual Return - Risk-Free Rate) / Downside Deviation |
| Calmar Ratio | CAGR / Maximum Drawdown |
| Profit Factor | Gross Profits / Gross Losses |

### T-Test Formula

```
t = (Sharpe - 0) / Standard Error = Sharpe / (σ / √n)
```

- Result: t = 55.69, df = 2,788 trading days
- P-value: < 0.000001

### Bootstrap Resampling Methodology

- **Samples:** 10,000 iterations with replacement
- **Method:** Daily returns randomly resampled to create alternative return sequences
- **Metrics calculated:** Sharpe ratio, total return, Sortino ratio for each sample
- **Confidence intervals:** 95% CI derived from 2.5th and 97.5th percentiles
- **Key result:** Sharpe 95% CI of [0.46, 1.85] excludes zero, confirming robustness

### Subperiod Analysis

- **Division:** Split 11-year backtest into two equal 5.5-year periods
- **Period 1 (2014-2019):** Bull market dominant, pre-COVID. Sharpe 1.269, Return 125.51%
- **Period 2 (2019-2024):** COVID crash, bear market, recovery. Sharpe 0.943, Return 134.51%
- **Result:** Both periods Sharpe > 0.9, confirming consistency across regimes
