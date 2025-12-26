#!/usr/bin/env python3
"""
CSRD AI Data Extraction System - Main Entry Point

Enterprise-grade AI-powered system for extracting structured sustainability data
from CSRD (Corporate Sustainability Reporting Directive) reports.

Usage:
    python main.py init                    # Initialize system
    python main.py process-report -p <pdf> -c <company>  # Process single report
    python main.py process-all             # Process all reports
    python main.py export-csv              # Export to CSV
    python main.py stats                   # Show statistics
    python main.py info                    # Show system info
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.main import cli

if __name__ == "__main__":
    cli()
