"""
Main extraction pipeline for CSRD data extraction.
Orchestrates the entire extraction process from PDF to database.
"""

import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd

from src.config import get_settings
from src.models import get_db, Company, Indicator
from src.models.seed_data import seed_database
from src.parsers import PDFParser, DocumentPreprocessor
from src.services import LLMService
from src.extractors import IndicatorExtractor
from src.utils import get_logger

logger = get_logger(__name__)


class ExtractionPipeline:
    """
    Main pipeline for extracting CSRD sustainability data.
    Coordinates PDF parsing, LLM extraction, and database storage.
    """
    
    def __init__(self):
        """Initialize extraction pipeline."""
        self.settings = get_settings()
        self.db = get_db()
        self.llm_service = LLMService()
        self.preprocessor = DocumentPreprocessor(
            max_chunk_size=self.settings.max_context_length
        )
        self.extractor = IndicatorExtractor(
            llm_service=self.llm_service,
            preprocessor=self.preprocessor,
        )
        
        # Ensure database is seeded
        seed_database(self.db)
        
        logger.info("Initialized ExtractionPipeline")
    
    def process_report(
        self,
        pdf_path: str,
        company_name: str,
        force_reprocess: bool = False,
    ) -> Dict[str, Any]:
        """
        Process a single CSRD report.
        
        Args:
            pdf_path: Path to PDF report
            company_name: Name of the company
            force_reprocess: Whether to reprocess if already exists
            
        Returns:
            Processing results summary
        """
        start_time = time.time()
        
        logger.info(f"Starting report processing: {company_name}")
        logger.info(f"PDF path: {pdf_path}")
        
        # Step 1: Get or create company
        company = self.db.get_company_by_name(company_name)
        if not company:
            logger.error(f"Company not found in database: {company_name}")
            raise ValueError(f"Company '{company_name}' not found. Please seed database first.")
        
        # Check if already processed
        if not force_reprocess:
            existing_data = self.db.get_extracted_data(company_id=company.id)
            if existing_data:
                logger.warning(
                    f"Company {company_name} already has {len(existing_data)} "
                    f"extracted data points. Use force_reprocess=True to reprocess."
                )
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "existing_count": len(existing_data),
                }
        
        # Step 2: Parse PDF
        logger.info("Parsing PDF document...")
        with PDFParser(pdf_path) as parser:
            pages = parser.parse_all_pages()
            sections = parser.detect_sections()
            metadata = parser.get_metadata()
        
        logger.info(f"Parsed {len(pages)} pages, detected {len(sections)} sections")
        
        # Step 3: Get all indicators
        indicators = self.db.get_all_indicators()
        logger.info(f"Extracting {len(indicators)} indicators")
        
        # Step 4: Extract indicators
        extraction_results = self.extractor.batch_extract_indicators(
            indicators=indicators,
            pages=pages,
            company_name=company_name,
        )
        
        # Step 5: Save to database
        logger.info("Saving extraction results to database...")
        saved_count = 0
        
        for result in extraction_results:
            try:
                self.db.create_extracted_data(
                    company_id=company.id,
                    indicator_id=result['indicator_id'],
                    value=result.get('value'),
                    numeric_value=result.get('numeric_value'),
                    unit=result.get('unit'),
                    confidence=result.get('confidence', 0.0),
                    source_page=result.get('source_page'),
                    source_section=result.get('source_section'),
                    raw_text=result.get('raw_text'),
                    notes=result.get('notes'),
                    extraction_method=result.get('extraction_method'),
                    model_used=result.get('model_used'),
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"Error saving result for {result.get('indicator_name')}: {e}")
        
        # Step 6: Generate summary
        elapsed_time = time.time() - start_time
        cost_summary = self.llm_service.get_cost_summary()
        
        # Count successful extractions
        successful = sum(1 for r in extraction_results if r.get('value') and r.get('value') != 'NOT_FOUND')
        high_confidence = sum(1 for r in extraction_results if r.get('confidence', 0) >= 0.7)
        
        summary = {
            "status": "completed",
            "company": company_name,
            "total_indicators": len(indicators),
            "successful_extractions": successful,
            "high_confidence_count": high_confidence,
            "saved_to_db": saved_count,
            "pages_processed": len(pages),
            "sections_detected": len(sections),
            "processing_time_seconds": round(elapsed_time, 2),
            "cost_summary": cost_summary,
        }
        
        logger.info(f"Report processing completed: {summary}")
        
        return summary
    
    def process_all_reports(
        self,
        reports_dir: Optional[str] = None,
        force_reprocess: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Process all reports in the reports directory.
        
        Args:
            reports_dir: Directory containing PDF reports
            force_reprocess: Whether to reprocess existing reports
            
        Returns:
            List of processing summaries
        """
        if not reports_dir:
            reports_dir = self.settings.reports_dir
        else:
            reports_dir = Path(reports_dir)
        
        logger.info(f"Processing all reports in: {reports_dir}")
        
        # Find all PDF files
        pdf_files = list(reports_dir.glob("*.pdf"))
        
        if not pdf_files:
            logger.warning(f"No PDF files found in {reports_dir}")
            return []
        
        logger.info(f"Found {len(pdf_files)} PDF files")
        
        # Get all companies from database
        companies = [
            self.db.get_company_by_name("Allied Irish Banks (AIB)"),
            self.db.get_company_by_name("BBVA"),
            self.db.get_company_by_name("Groupe BPCE"),
        ]
        
        results = []
        
        for pdf_file in pdf_files:
            # Try to match PDF to company
            company = self._match_pdf_to_company(pdf_file.name, companies)
            
            if not company:
                logger.warning(f"Could not match PDF to company: {pdf_file.name}")
                continue
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing: {pdf_file.name} -> {company.name}")
            logger.info(f"{'='*60}\n")
            
            try:
                result = self.process_report(
                    pdf_path=str(pdf_file),
                    company_name=company.name,
                    force_reprocess=force_reprocess,
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Error processing {pdf_file.name}: {e}")
                results.append({
                    "status": "error",
                    "company": company.name,
                    "error": str(e),
                })
        
        return results
    
    def _match_pdf_to_company(
        self,
        filename: str,
        companies: List[Company],
    ) -> Optional[Company]:
        """Match PDF filename to company."""
        filename_lower = filename.lower()
        
        for company in companies:
            if not company:
                continue
            
            # Check if company name or keywords are in filename
            if "aib" in filename_lower or "allied" in filename_lower:
                if "aib" in company.name.lower():
                    return company
            elif "bbva" in filename_lower:
                if "bbva" in company.name.lower():
                    return company
            elif "bpce" in filename_lower or "groupe" in filename_lower:
                if "bpce" in company.name.lower():
                    return company
        
        return None
    
    def export_to_csv(
        self,
        output_path: Optional[str] = None,
    ) -> str:
        """
        Export all extracted data to CSV.
        
        Args:
            output_path: Path for output CSV file
            
        Returns:
            Path to created CSV file
        """
        if not output_path:
            output_path = self.settings.output_dir / "csrd_extracted_data.csv"
        else:
            output_path = Path(output_path)
        
        logger.info(f"Exporting data to CSV: {output_path}")
        
        # Get all extracted data
        all_data = self.db.get_all_extracted_data()
        
        if not all_data:
            logger.warning("No data to export")
            return ""
        
        # Convert to list of dictionaries
        data_dicts = [item.to_dict() for item in all_data]
        
        # Create DataFrame
        df = pd.DataFrame(data_dicts)
        
        # Reorder columns
        column_order = [
            "company",
            "report_year",
            "indicator_name",
            "value",
            "unit",
            "confidence",
            "source_page",
            "source_section",
            "notes",
        ]
        
        df = df[column_order]
        
        # Save to CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)
        
        logger.info(f"Exported {len(df)} data points to {output_path}")
        
        return str(output_path)
    
    def get_extraction_stats(self) -> Dict[str, Any]:
        """Get statistics about extracted data."""
        all_data = self.db.get_all_extracted_data()
        
        if not all_data:
            return {"total_extractions": 0}
        
        total = len(all_data)
        with_values = sum(1 for d in all_data if d.value)
        high_confidence = sum(1 for d in all_data if d.confidence >= 0.7)
        avg_confidence = sum(d.confidence for d in all_data) / total if total > 0 else 0
        
        # Group by company
        by_company = {}
        for data in all_data:
            company_name = data.company.name if data.company else "Unknown"
            if company_name not in by_company:
                by_company[company_name] = 0
            by_company[company_name] += 1
        
        stats = {
            "total_extractions": total,
            "with_values": with_values,
            "high_confidence": high_confidence,
            "average_confidence": round(avg_confidence, 3),
            "by_company": by_company,
            "cost_summary": self.llm_service.get_cost_summary(),
        }
        
        return stats
