"""
Emerging Growth Strategy -- Monthly Screening & Scoring Engine

Usage:
    python -m src.main run --input data/bloomberg_export.xlsx --output reports/
    python -m src.main run --input data/bloomberg_export.xlsx --prior data/prior_month.xlsx --output reports/
    python -m src.main mock --output data/mock_data.xlsx
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool = False):
    """Configure logging to stdout."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
        datefmt='%H:%M:%S',
    )


def cmd_mock(args):
    """Generate mock data for testing."""
    from src.mock_data import generate_mock_data

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = generate_mock_data(output_path, n_tickers=args.tickers)
    print(f"Mock data generated: {result}")


def cmd_run(args):
    """Run the full monthly pipeline."""
    from src.data_loader import load_universe, load_price_history, load_fundamentals
    from src.screener import screen_universe, screening_summary
    from src.factors import calculate_all_factors
    from src.scoring import (
        apply_quality_filters, calc_composite_score, select_top_n,
        enforce_sector_cap, generate_signals, format_report,
    )
    from src.portfolio import build_portfolio

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Step 1: Load data
    print("Step 1/7: Loading data...")
    universe = load_universe(input_path)
    price_data = load_price_history(input_path)
    fundamentals = load_fundamentals(input_path)
    print(
        f"  Loaded {len(universe)} tickers, "
        f"{len(price_data)} with prices, "
        f"{len(fundamentals)} with fundamentals"
    )

    # Step 2: Screen universe
    print("Step 2/7: Screening universe...")
    screened = screen_universe(universe)
    screen_stats = screening_summary(universe, screened)
    qualifying_tickers = screened['ticker'].tolist()
    print(f"  {len(qualifying_tickers)} tickers pass all filters")

    # Step 3: Calculate factors
    print("Step 3/7: Calculating factors...")
    factors = calculate_all_factors(price_data, fundamentals, qualifying_tickers)
    print(f"  Factors computed for {len(factors)} tickers")

    # Step 4: Apply quality filters
    print("Step 4/7: Applying quality filters...")
    qualified = apply_quality_filters(factors)
    print(f"  {len(qualified)} tickers pass quality gates")

    # Step 5: Score and rank
    print("Step 5/7: Scoring and ranking...")
    scored = calc_composite_score(qualified)
    top25 = select_top_n(scored, n=25)
    if top25.empty:
        print("  WARNING: No stocks passed all quality gates. Report will be empty.")
    else:
        print(
            f"  Top {len(top25)} selected (score range: "
            f"{top25['composite_score'].min():.1f} - "
            f"{top25['composite_score'].max():.1f})"
        )

    # Step 6: Generate signals
    print("Step 6/7: Generating signals...")
    prior_tickers = None
    if args.prior:
        prior_path = Path(args.prior)
        if prior_path.exists():
            # Load prior month's top 25 from a saved CSV
            prior_df = pd.read_csv(prior_path)
            prior_tickers = (
                prior_df['ticker'].tolist()
                if 'ticker' in prior_df.columns
                else None
            )

    signals = generate_signals(top25, prior_tickers)

    # Step 7: Output
    print("Step 7/7: Generating report...")
    report = format_report(signals, screening_stats=screen_stats)
    print("\n" + report)

    # Save outputs
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime('%Y-%m-%d')

    # Save full ranked list as CSV
    scored.to_csv(output_dir / f'ranked_{today}.csv', index=False)

    # Save top 25 with signals
    signals.to_csv(output_dir / f'signals_{today}.csv', index=False)

    # Save text report
    with open(output_dir / f'report_{today}.txt', 'w') as f:
        f.write(report)

    # Save current top 25 tickers for next month's prior comparison
    top25[['ticker']].to_csv(output_dir / f'top25_{today}.csv', index=False)

    print(f"\nOutputs saved to {output_dir}/")
    print(f"  ranked_{today}.csv -- full scored list")
    print(f"  signals_{today}.csv -- top 25 with signals")
    print(f"  report_{today}.txt -- formatted report")
    print(f"  top25_{today}.csv -- save this for next month's --prior flag")


def main():
    parser = argparse.ArgumentParser(
        description='Emerging Growth Strategy -- Monthly Screening Engine',
    )
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # 'run' command
    run_parser = subparsers.add_parser('run', help='Run monthly screening pipeline')
    run_parser.add_argument(
        '--input', '-i', required=True,
        help='Path to Bloomberg Excel export',
    )
    run_parser.add_argument(
        '--prior', '-p',
        help='Path to prior month top25 CSV (for signal generation)',
    )
    run_parser.add_argument(
        '--output', '-o', default='reports/',
        help='Output directory (default: reports/)',
    )
    run_parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose logging',
    )

    # 'mock' command
    mock_parser = subparsers.add_parser('mock', help='Generate mock data for testing')
    mock_parser.add_argument(
        '--output', '-o', default='data/mock_data.xlsx',
        help='Output Excel file path',
    )
    mock_parser.add_argument(
        '--tickers', '-n', type=int, default=100,
        help='Number of mock tickers',
    )
    mock_parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Verbose logging',
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(getattr(args, 'verbose', False))

    if args.command == 'mock':
        cmd_mock(args)
    elif args.command == 'run':
        cmd_run(args)


if __name__ == '__main__':
    main()
