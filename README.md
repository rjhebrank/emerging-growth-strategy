# Emerging Growth Strategy

Quantitative small-cap stock screening engine using a four-factor composite scoring model.

## Setup

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Generate mock data (for testing without Bloomberg)

```bash
python -m src.main mock --output data/mock_data.xlsx
```

### 2. Run the monthly screening pipeline

```bash
python -m src.main run --input data/mock_data.xlsx --output reports/
```

### 3. With prior month comparison (for BUY/SELL/HOLD signals)

```bash
python -m src.main run --input data/bloomberg_export.xlsx --prior reports/top25_2026-02-01.csv --output reports/
```

## Bloomberg Integration

Export data from Bloomberg Terminal using the Excel Add-in following the template in `docs/06-bloomberg-data-pull.md`. The engine reads the 5-sheet workbook format directly.

## Strategy Overview

- **Universe:** ~2,000 US small-cap stocks ($50M-$10B market cap)
- **Factors:** RS Percentile (40%), EPS Growth (20%), Revenue Growth (20%), Price vs 52-Week High (20%)
- **Quality filters:** EPS growth ≥ 5%, Revenue growth ≥ 5%, Price ≥ 75% of 52-week high
- **Output:** Top 25 stocks, equal-weighted at 4% each, with monthly BUY/SELL/HOLD signals

See `STRATEGY.md` for the full specification and `docs/` for implementation guides.

## Project Structure

```
src/
├── main.py          # CLI entry point
├── data_loader.py   # Bloomberg Excel ingestion
├── mock_data.py     # Mock data generator
├── screener.py      # Universe filtering
├── factors.py       # 4 factor calculations
├── scoring.py       # Quality filters, composite score, signals
└── portfolio.py     # Position sizing, rebalancing
```
