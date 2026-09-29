"""
CLI entry point for the BIS Standards Data Collector.
Uses openpyxl directly (no pandas) for Excel I/O.

Usage:
    python scripts/run_collector.py --input data/input/<file>.xlsx --department ETD
    python scripts/run_collector.py --input data/input/<file>.xlsx --department ETD --output-dir data/processed/ETD
    python scripts/run_collector.py --input data/input/<file>.xlsx --department AYUSH --pilot
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.collector import Collector


def setup_logging(log_dir: str = "data/logs", department: str = "run"):
    """Configure logging to both console and file."""
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{department}_{timestamp}.log"
    
    # Root logger config
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    
    # Quiet down noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    
    return log_file


def main():
    parser = argparse.ArgumentParser(
        description="BIS Standards Data Collector — Fetches Scope/Notes/References from BSB Edge preview pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to the BIS department Excel file (e.g., data/input/ETD_standards.xlsx)",
    )
    parser.add_argument(
        "--department", "-d",
        required=True,
        help="Department abbreviation (e.g., ETD, AYUSH). Used for output file naming.",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=None,
        help="Output directory (default: data/processed/<department>)",
    )
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="Run in pilot mode (output goes to data/processed/pilot_<department>/)",
    )
    parser.add_argument(
        "--spot-check", "-s",
        type=int,
        default=0,
        help="Generate a spot-check sample CSV with this many rows after the run",
    )
    parser.add_argument(
        "--parse-cache",
        action="store_true",
        help="Run parser exclusively on cached HTML files without making network requests",
    )
    parser.add_argument(
        "--force-reparse",
        action="store_true",
        help="Force re-parsing of all records, invalidating cached parsed output",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Incremental mode: append/merge with prior runs instead of strict input workbook snapshot",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: Input file not found: {input_path}")
        sys.exit(1)
    
    department = args.department.upper()
    
    if args.pilot:
        output_dir = Path(f"data/processed/pilot_{department.lower()}")
    elif args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path(f"data/processed/{department}")
    
    # Setup logging
    log_file = setup_logging(department=department)
    logger = logging.getLogger(__name__)
    logger.info(f"Log file: {log_file}")
    
    # Run collector
    collector = Collector(
        input_excel=input_path,
        department=department,
        output_dir=output_dir,
        parse_cache_only=args.parse_cache,
        force_reparse=args.force_reparse,
        incremental=args.incremental,
    )
    
    try:
        report = collector.run()
        
        # Print summary
        stds = report.get("standards", {})
        cnt = report.get("content", {})
        refs = report.get("references", {})
        print("\n" + "=" * 60)
        print("COLLECTION COMPLETE (V1.2 Frozen Data Contract)")
        print("=" * 60)
        print(f"  Input rows:            {report['input_rows']}")
        print(f"  Standards processed:   {stds.get('processed', 0)}")
        print(f"  Success:               {stds.get('success', 0)}")
        print(f"  Partial success:       {stds.get('partial_success', 0)}")
        print(f"  Review required:       {stds.get('review_required', 0)}")
        print(f"  Failed:                {stds.get('failed', 0)}")
        print(f"  Scope found:           {cnt.get('scope_found', 0)}")
        print(f"  Foreword found:        {cnt.get('foreword_found', 0)}")
        print(f"  Total references:      {refs.get('total_reference_records', 0)}")
        print(f"  Formal ref rows:       {refs.get('formal_reference_rows', 0)}")
        print(f"  Dual-numbered:         {refs.get('dual_numbered_references', 0)}")
        print(f"  Continuation resolved: {refs.get('continuation_resolved', 0)}")
        print(f"  Int'l references:      {refs.get('international_references', 0)}")
        print(f"  SP references:         {refs.get('sp_references', 0)}")
        print(f"  Enriched Excel:        {report['output_paths']['enriched_excel']}")
        print("=" * 60)
        
        # Generate spot-check sample if requested
        if args.spot_check > 0:
            sample_path = collector.generate_spot_check_sample(n=args.spot_check)
            print(f"  Spot-check sample: {sample_path}")
        
    except KeyboardInterrupt:
        logger.info("Interrupted by user — state has been saved. Restart to resume.")
        print("\n⚠ Interrupted. State saved — restart the same command to resume.")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
