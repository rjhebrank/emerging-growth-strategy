"""Bloomberg Excel workbook loader for the Emerging Growth Strategy engine.

Reads 5-sheet Bloomberg template workbooks and returns clean DataFrames.
Handles Bloomberg quirks: #N/A strings, empty cells, inconsistent formatting.

Sheet structure:
  1. Universe   - ticker list with market cap, exchange, volume, price
  2. Price History - block layout, 320-row spacing, 315 days OHLCV per ticker
  3. Fundamentals  - block layout, 10-row spacing, 8 quarters EPS + revenue
  4-5. (computed by engine, not read here)
"""

import logging
from pathlib import Path

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

# Bloomberg exports these strings for missing / error values
_BLOOMBERG_NA_VALUES = {"#N/A", "#N/A N/A", "#N/A Field Not Applicable", "#NA", "N/A", "n/a", ""}

# ---------------------------------------------------------------------------
# Sheet 1 - Universe
# ---------------------------------------------------------------------------

_UNIVERSE_COLUMNS = {
    0: "ticker",
    1: "market_cap",
    2: "exchange",
    3: "avg_volume",
    4: "price",
    5: "dollar_volume",
}

_NUMERIC_UNIVERSE_COLS = ["market_cap", "avg_volume", "price", "dollar_volume"]


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert a series to float, treating Bloomberg #N/A strings as NaN."""
    replaced = series.replace(_BLOOMBERG_NA_VALUES, np.nan)
    return pd.to_numeric(replaced, errors="coerce")


def load_universe(filepath: str | Path) -> pd.DataFrame:
    """Read Sheet 1 'Universe', return DataFrame with columns:
    ticker, market_cap, exchange, avg_volume, price, dollar_volume

    - Reads only columns A-F
    - Renames to snake_case column names
    - Drops rows where ticker is NaN or empty
    - Converts numeric columns to float, coercing errors to NaN
    - Handles Bloomberg #N/A values (treat as NaN)
    """
    filepath = Path(filepath)
    logger.info("Loading universe from %s", filepath)

    df = pd.read_excel(
        filepath,
        sheet_name="Universe",
        engine="openpyxl",
        header=0,
        usecols="A:F",
        dtype=str,  # read everything as string first for uniform cleaning
    )

    # Rename columns by position (header text may vary across templates)
    df.columns = [_UNIVERSE_COLUMNS[i] for i in range(len(df.columns))]

    # Strip whitespace from ticker and exchange
    df["ticker"] = df["ticker"].astype(str).str.strip()
    df["exchange"] = df["exchange"].astype(str).str.strip()

    # Drop rows with no ticker
    df = df[df["ticker"].notna() & (df["ticker"] != "") & (df["ticker"] != "nan")]
    df = df.reset_index(drop=True)

    # Coerce numeric columns
    for col in _NUMERIC_UNIVERSE_COLS:
        df[col] = _coerce_numeric(df[col])

    logger.info("Loaded %d tickers from universe sheet", len(df))
    return df


# ---------------------------------------------------------------------------
# Sheet 2 - Price History (block layout, 320-row spacing)
# ---------------------------------------------------------------------------

_PRICE_BLOCK_SIZE = 320
_PRICE_DATA_COLS = ["date", "open", "high", "low", "close", "volume"]


def load_price_history(filepath: str | Path) -> dict[str, pd.DataFrame]:
    """Read Sheet 2 'Price History', parse block layout.

    Returns dict: ticker -> DataFrame(date, open, high, low, close, volume)

    Block parsing logic:
    - Reads all rows from the sheet (no header)
    - Blocks are 320 rows apart (row 0, 320, 640, ...)
    - First row of each block has the ticker in column A
    - Rows 1-315 (approx) have price data in columns B-G
    - Parses dates from column B
    - Converts OHLCV to numeric
    - Handles #N/A values, skips tickers with no valid data
    """
    filepath = Path(filepath)
    logger.info("Loading price history from %s", filepath)

    # Read raw - no header, all columns, everything as object for uniform parsing
    raw = pd.read_excel(
        filepath,
        sheet_name="Price History",
        engine="openpyxl",
        header=None,
        dtype=object,
    )

    n_rows = len(raw)
    n_blocks = (n_rows + _PRICE_BLOCK_SIZE - 1) // _PRICE_BLOCK_SIZE
    logger.info("Price history sheet: %d rows, up to %d blocks", n_rows, n_blocks)

    result: dict[str, pd.DataFrame] = {}

    for block_idx in range(n_blocks):
        start_row = block_idx * _PRICE_BLOCK_SIZE

        if start_row >= n_rows:
            break

        # Ticker is in column A of the first row of the block
        ticker_raw = raw.iloc[start_row, 0]
        if pd.isna(ticker_raw) or str(ticker_raw).strip() == "":
            continue
        ticker = str(ticker_raw).strip()

        # Data rows: from start_row+1 up to the next block (or end of sheet)
        data_end = min(start_row + _PRICE_BLOCK_SIZE, n_rows)
        block = raw.iloc[start_row + 1 : data_end, 1:7].copy()  # columns B-G
        block.columns = _PRICE_DATA_COLS

        # Drop fully-empty rows (blank padding at end of block)
        block = block.dropna(how="all")

        # Replace Bloomberg #N/A strings
        block = block.replace(_BLOOMBERG_NA_VALUES, np.nan)

        if block.empty:
            logger.debug("Skipping ticker %s - no valid price data", ticker)
            continue

        # Parse dates
        block["date"] = pd.to_datetime(block["date"], errors="coerce")

        # Coerce OHLCV to numeric
        for col in ["open", "high", "low", "close", "volume"]:
            block[col] = pd.to_numeric(block[col], errors="coerce")

        # Drop rows where date is NaT (unparseable date = garbage row)
        block = block.dropna(subset=["date"])

        if block.empty:
            logger.debug("Skipping ticker %s - no parseable dates", ticker)
            continue

        block = block.reset_index(drop=True)
        result[ticker] = block
        logger.debug("Loaded %d price rows for %s", len(block), ticker)

    logger.info("Loaded price history for %d tickers", len(result))
    return result


# ---------------------------------------------------------------------------
# Sheet 3 - Fundamentals (block layout, 10-row spacing)
# ---------------------------------------------------------------------------

_FUND_BLOCK_SIZE = 10


def load_fundamentals(filepath: str | Path) -> dict[str, dict]:
    """Read Sheet 3 'Fundamentals', parse block layout.

    Returns dict: ticker -> {
        'eps': DataFrame(date, eps),        # up to 8 quarters
        'revenue': DataFrame(date, revenue) # up to 8 quarters
    }

    Block parsing logic:
    - Blocks are 10 rows apart (row 0, 10, 20, ...)
    - First row of each block has the ticker in column A
    - Rows 1-8 have quarterly data
    - EPS in columns B-C (date, eps value)
    - Revenue in columns E-F (date, revenue value)
    - Parses dates, converts values to numeric
    - Handles #N/A, missing quarters
    """
    filepath = Path(filepath)
    logger.info("Loading fundamentals from %s", filepath)

    raw = pd.read_excel(
        filepath,
        sheet_name="Fundamentals",
        engine="openpyxl",
        header=None,
        dtype=object,
    )

    n_rows = len(raw)
    n_blocks = (n_rows + _FUND_BLOCK_SIZE - 1) // _FUND_BLOCK_SIZE
    logger.info("Fundamentals sheet: %d rows, up to %d blocks", n_rows, n_blocks)

    result: dict[str, dict] = {}

    for block_idx in range(n_blocks):
        start_row = block_idx * _FUND_BLOCK_SIZE

        if start_row >= n_rows:
            break

        # Ticker in column A of first row
        ticker_raw = raw.iloc[start_row, 0]
        if pd.isna(ticker_raw) or str(ticker_raw).strip() == "":
            continue
        ticker = str(ticker_raw).strip()

        # Data rows: up to 8 quarters starting at start_row + 1
        data_end = min(start_row + _FUND_BLOCK_SIZE, n_rows)
        block = raw.iloc[start_row + 1 : data_end].copy()

        # --- EPS: columns B (idx 1) and C (idx 2) ---
        eps_df = block.iloc[:, 1:3].copy()
        eps_df.columns = ["date", "eps"]
        eps_df = eps_df.replace(_BLOOMBERG_NA_VALUES, np.nan)
        eps_df = eps_df.dropna(how="all")
        eps_df["date"] = pd.to_datetime(eps_df["date"], errors="coerce")
        eps_df["eps"] = pd.to_numeric(eps_df["eps"], errors="coerce")
        eps_df = eps_df.dropna(subset=["date"])
        eps_df = eps_df.reset_index(drop=True)

        # --- Revenue: columns E (idx 4) and F (idx 5) ---
        # Guard against sheets with fewer than 6 columns
        if raw.shape[1] >= 6:
            rev_df = block.iloc[:, 4:6].copy()
            rev_df.columns = ["date", "revenue"]
            rev_df = rev_df.replace(_BLOOMBERG_NA_VALUES, np.nan)
            rev_df = rev_df.dropna(how="all")
            rev_df["date"] = pd.to_datetime(rev_df["date"], errors="coerce")
            rev_df["revenue"] = pd.to_numeric(rev_df["revenue"], errors="coerce")
            rev_df = rev_df.dropna(subset=["date"])
            rev_df = rev_df.reset_index(drop=True)
        else:
            rev_df = pd.DataFrame(columns=["date", "revenue"])

        # Only include ticker if at least one of EPS/revenue has data
        if eps_df.empty and rev_df.empty:
            logger.debug("Skipping ticker %s - no fundamental data", ticker)
            continue

        result[ticker] = {"eps": eps_df, "revenue": rev_df}
        logger.debug(
            "Loaded fundamentals for %s: %d eps quarters, %d revenue quarters",
            ticker,
            len(eps_df),
            len(rev_df),
        )

    logger.info("Loaded fundamentals for %d tickers", len(result))
    return result


# ---------------------------------------------------------------------------
# Convenience: load everything at once
# ---------------------------------------------------------------------------


def load_workbook(filepath: str | Path) -> dict:
    """Load all three data sheets from a Bloomberg workbook.

    Returns dict with keys:
        'universe':      pd.DataFrame
        'price_history': dict[str, pd.DataFrame]
        'fundamentals':  dict[str, dict]
    """
    filepath = Path(filepath)
    return {
        "universe": load_universe(filepath),
        "price_history": load_price_history(filepath),
        "fundamentals": load_fundamentals(filepath),
    }
