"""
Command-line interface for CSRD extraction system.
Provides interactive commands for processing reports and managing data.
"""

import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from src.config import get_settings
from src.services import ExtractionPipeline
from src.models import get_db
from src.models.seed_data import seed_database
from src.utils import get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """
    CSRD AI Data Extraction System
    
    Enterprise-grade tool for extracting sustainability data from CSRD reports.
    """
    pass


@cli.command()
@click.option(
    "--pdf",
    "-p",
    type=click.Path(exists=True),
    required=True,
    help="Path to PDF report file"
)
@click.option(
    "--company",
    "-c",
    type=str,
    required=True,
    help="Company name (must match database entry)"
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reprocessing even if data exists"
)
def process_report(pdf: str, company: str, force: bool):
    """Process a single CSRD report."""
    console.print(f"\n[bold blue]Processing Report[/bold blue]")
    console.print(f"PDF: {pdf}")
    console.print(f"Company: {company}\n")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing report...", total=None)
            
            pipeline = ExtractionPipeline()
            result = pipeline.process_report(
                pdf_path=pdf,
                company_name=company,
                force_reprocess=force,
            )
            
            progress.update(task, completed=True)
        
        # Display results
        if result["status"] == "completed":
            console.print("\n[bold green]✓ Processing completed successfully![/bold green]\n")
            
            table = Table(title="Extraction Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")
            
            table.add_row("Total Indicators", str(result["total_indicators"]))
            table.add_row("Successful Extractions", str(result["successful_extractions"]))
            table.add_row("High Confidence (≥0.7)", str(result["high_confidence_count"]))
            table.add_row("Processing Time", f"{result['processing_time_seconds']}s")
            table.add_row("API Cost", f"${result['cost_summary']['total_cost_usd']:.4f}")
            
            console.print(table)
        elif result["status"] == "skipped":
            console.print(f"\n[yellow]⚠ Skipped: {result['reason']}[/yellow]")
            console.print(f"Existing data points: {result.get('existing_count', 0)}")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error processing report: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--dir",
    "-d",
    type=click.Path(exists=True),
    help="Directory containing PDF reports (default: data/reports)"
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force reprocessing even if data exists"
)
def process_all(dir: Optional[str], force: bool):
    """Process all reports in the reports directory."""
    console.print("\n[bold blue]Processing All Reports[/bold blue]\n")
    
    try:
        pipeline = ExtractionPipeline()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Processing all reports...", total=None)
            
            results = pipeline.process_all_reports(
                reports_dir=dir,
                force_reprocess=force,
            )
            
            progress.update(task, completed=True)
        
        # Display results
        console.print(f"\n[bold green]✓ Processed {len(results)} reports[/bold green]\n")
        
        for result in results:
            if result["status"] == "completed":
                console.print(
                    f"[green]✓[/green] {result['company']}: "
                    f"{result['successful_extractions']}/{result['total_indicators']} extracted"
                )
            elif result["status"] == "error":
                console.print(f"[red]✗[/red] {result['company']}: {result.get('error', 'Unknown error')}")
            else:
                console.print(f"[yellow]⚠[/yellow] {result['company']}: {result.get('reason', 'Skipped')}")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error processing reports: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output CSV file path (default: data/output/csrd_extracted_data.csv)"
)
def export_csv(output: Optional[str]):
    """Export extracted data to CSV."""
    console.print("\n[bold blue]Exporting Data to CSV[/bold blue]\n")
    
    try:
        pipeline = ExtractionPipeline()
        csv_path = pipeline.export_to_csv(output_path=output)
        
        if csv_path:
            console.print(f"[bold green]✓ Data exported successfully![/bold green]")
            console.print(f"File: {csv_path}\n")
        else:
            console.print("[yellow]⚠ No data to export[/yellow]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error exporting CSV: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def stats():
    """Show extraction statistics."""
    console.print("\n[bold blue]Extraction Statistics[/bold blue]\n")
    
    try:
        pipeline = ExtractionPipeline()
        stats = pipeline.get_extraction_stats()
        
        # Overall stats table
        table = Table(title="Overall Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Extractions", str(stats["total_extractions"]))
        table.add_row("With Values", str(stats["with_values"]))
        table.add_row("High Confidence (≥0.7)", str(stats["high_confidence"]))
        table.add_row("Average Confidence", f"{stats['average_confidence']:.3f}")
        
        console.print(table)
        
        # By company table
        if stats.get("by_company"):
            console.print()
            company_table = Table(title="By Company")
            company_table.add_column("Company", style="cyan")
            company_table.add_column("Extractions", style="green")
            
            for company, count in stats["by_company"].items():
                company_table.add_row(company, str(count))
            
            console.print(company_table)
        
        # Cost summary
        cost = stats.get("cost_summary", {})
        if cost:
            console.print()
            cost_table = Table(title="Cost Summary")
            cost_table.add_column("Metric", style="cyan")
            cost_table.add_column("Value", style="green")
            
            cost_table.add_row("Total Tokens", f"{cost.get('total_tokens', 0):,}")
            cost_table.add_row("Total Cost", f"${cost.get('total_cost_usd', 0):.4f}")
            cost_table.add_row("Budget Used", f"{cost.get('cost_percentage', 0):.1f}%")
            
            console.print(cost_table)
        
        console.print()
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error getting stats: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def seed():
    """Seed the database with initial data."""
    console.print("\n[bold blue]Seeding Database[/bold blue]\n")
    
    try:
        db = get_db()
        seed_database(db)
        
        console.print("[bold green]✓ Database seeded successfully![/bold green]")
        console.print("- 20 sustainability indicators")
        console.print("- 3 bank companies\n")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error seeding database: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def init():
    """Initialize the system (create directories, seed database)."""
    console.print("\n[bold blue]Initializing CSRD Extraction System[/bold blue]\n")
    
    try:
        settings = get_settings()
        
        # Create directories
        console.print("Creating directories...")
        settings.ensure_directories()
        console.print("[green]✓[/green] Directories created")
        
        # Initialize database
        console.print("Initializing database...")
        db = get_db()
        console.print("[green]✓[/green] Database initialized")
        
        # Seed database
        console.print("Seeding database...")
        seed_database(db)
        console.print("[green]✓[/green] Database seeded")
        
        console.print("\n[bold green]✓ System initialized successfully![/bold green]")
        console.print("\nNext steps:")
        console.print("1. Copy your .env.example to .env and add your OpenAI API key")
        console.print("2. Place PDF reports in data/reports/")
        console.print("3. Run: python src/main.py process-all\n")
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error initializing system: {e}", exc_info=True)
        sys.exit(1)


@cli.command()
def info():
    """Show system information."""
    console.print("\n[bold blue]System Information[/bold blue]\n")
    
    try:
        settings = get_settings()
        
        table = Table()
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Project Root", str(settings.project_root))
        table.add_row("Database URL", settings.database_url)
        table.add_row("Reports Directory", str(settings.reports_dir))
        table.add_row("Output Directory", str(settings.output_dir))
        table.add_row("Primary Model", settings.openai_model_primary)
        table.add_row("Fallback Model", settings.openai_model_fallback)
        table.add_row("Max API Cost", f"${settings.max_api_cost_usd}")
        table.add_row("Caching Enabled", str(settings.enable_caching))
        
        console.print(table)
        console.print()
        
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]")
        logger.error(f"Error getting system info: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()
