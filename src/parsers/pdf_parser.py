"""
PDF parsing module for CSRD reports.
Handles text extraction, table detection, and document structure analysis.
"""

import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

import fitz  # PyMuPDF
import pdfplumber

from src.utils import get_logger

logger = get_logger(__name__)


@dataclass
class PageContent:
    """Represents content from a single PDF page."""
    page_number: int
    text: str
    tables: List[List[List[str]]]
    section: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class DocumentSection:
    """Represents a section of the document."""
    title: str
    start_page: int
    end_page: Optional[int] = None
    content: str = ""


class PDFParser:
    """
    Multi-strategy PDF parser for CSRD sustainability reports.
    Uses PyMuPDF for text extraction and pdfplumber for tables.
    """
    
    def __init__(self, pdf_path: str):
        """
        Initialize PDF parser.
        
        Args:
            pdf_path: Path to PDF file
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        self.doc = None
        self.pdf_plumber = None
        self.pages: List[PageContent] = []
        self.sections: List[DocumentSection] = []
        
        logger.info(f"Initialized PDF parser for: {self.pdf_path.name}")
    
    def __enter__(self):
        """Context manager entry."""
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def open(self) -> None:
        """Open PDF document."""
        self.doc = fitz.open(self.pdf_path)
        self.pdf_plumber = pdfplumber.open(self.pdf_path)
        logger.info(f"Opened PDF: {self.pdf_path.name} ({len(self.doc)} pages)")
    
    def close(self) -> None:
        """Close PDF document."""
        if self.doc:
            self.doc.close()
        if self.pdf_plumber:
            self.pdf_plumber.close()
        logger.info(f"Closed PDF: {self.pdf_path.name}")
    
    def extract_text_from_page(self, page_number: int) -> str:
        """
        Extract text from a specific page using PyMuPDF.
        
        Args:
            page_number: Page number (0-indexed)
            
        Returns:
            Extracted text
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened")
        
        if page_number >= len(self.doc):
            raise ValueError(f"Page number {page_number} out of range")
        
        page = self.doc[page_number]
        text = page.get_text("text")
        return text
    
    def extract_tables_from_page(self, page_number: int) -> List[List[List[str]]]:
        """
        Extract tables from a specific page using pdfplumber.
        
        Args:
            page_number: Page number (0-indexed)
            
        Returns:
            List of tables (each table is a list of rows, each row is a list of cells)
        """
        if not self.pdf_plumber:
            raise RuntimeError("PDF document not opened")
        
        if page_number >= len(self.pdf_plumber.pages):
            raise ValueError(f"Page number {page_number} out of range")
        
        page = self.pdf_plumber.pages[page_number]
        tables = page.extract_tables()
        
        # Clean and filter tables
        cleaned_tables = []
        for table in tables or []:
            if table and len(table) > 1:  # At least header + 1 row
                cleaned_tables.append(table)
        
        return cleaned_tables
    
    def parse_all_pages(self) -> List[PageContent]:
        """
        Parse all pages in the document.
        
        Returns:
            List of PageContent objects
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened")
        
        self.pages = []
        total_pages = len(self.doc)
        
        logger.info(f"Parsing {total_pages} pages...")
        
        for page_num in range(total_pages):
            try:
                text = self.extract_text_from_page(page_num)
                tables = self.extract_tables_from_page(page_num)
                
                page_content = PageContent(
                    page_number=page_num + 1,  # 1-indexed for user display
                    text=text,
                    tables=tables,
                )
                
                self.pages.append(page_content)
                
                if (page_num + 1) % 50 == 0:
                    logger.info(f"Parsed {page_num + 1}/{total_pages} pages")
                    
            except Exception as e:
                logger.error(f"Error parsing page {page_num + 1}: {e}")
                # Add empty page content to maintain page numbering
                self.pages.append(PageContent(
                    page_number=page_num + 1,
                    text="",
                    tables=[],
                ))
        
        logger.info(f"Successfully parsed {len(self.pages)} pages")
        return self.pages
    
    def detect_sections(self) -> List[DocumentSection]:
        """
        Detect document sections based on headings and structure.
        
        Returns:
            List of DocumentSection objects
        """
        if not self.pages:
            self.parse_all_pages()
        
        sections = []
        current_section = None
        
        # Common CSRD section patterns
        section_patterns = [
            r'^(?:ESRS\s+[EGS]\d+)',  # ESRS E1, ESRS S1, etc.
            r'^(?:\d+\.?\s+[A-Z][a-zA-Z\s]+)$',  # Numbered sections
            r'^(?:[A-Z][A-Z\s]{10,})$',  # ALL CAPS headings
            r'(?i)sustainability|environmental|social|governance|climate|emissions|workforce',
        ]
        
        for page in self.pages:
            lines = page.text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if line matches section pattern
                is_section = any(re.search(pattern, line) for pattern in section_patterns)
                
                if is_section and len(line) < 100:  # Likely a heading
                    # Save previous section
                    if current_section:
                        current_section.end_page = page.page_number - 1
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = DocumentSection(
                        title=line,
                        start_page=page.page_number,
                    )
                    logger.debug(f"Detected section: {line} (page {page.page_number})")
                
                elif current_section:
                    current_section.content += line + "\n"
        
        # Save last section
        if current_section:
            current_section.end_page = self.pages[-1].page_number
            sections.append(current_section)
        
        self.sections = sections
        logger.info(f"Detected {len(sections)} sections")
        return sections
    
    def search_text(self, query: str, case_sensitive: bool = False) -> List[Tuple[int, str]]:
        """
        Search for text across all pages.
        
        Args:
            query: Search query
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            List of (page_number, context) tuples
        """
        if not self.pages:
            self.parse_all_pages()
        
        results = []
        flags = 0 if case_sensitive else re.IGNORECASE
        
        for page in self.pages:
            if re.search(query, page.text, flags):
                # Extract context around match
                lines = page.text.split('\n')
                for i, line in enumerate(lines):
                    if re.search(query, line, flags):
                        # Get context (3 lines before and after)
                        start = max(0, i - 3)
                        end = min(len(lines), i + 4)
                        context = '\n'.join(lines[start:end])
                        results.append((page.page_number, context))
        
        logger.info(f"Found {len(results)} matches for query: {query}")
        return results
    
    def get_page_range(self, start_page: int, end_page: int) -> str:
        """
        Get combined text from a range of pages.
        
        Args:
            start_page: Start page number (1-indexed)
            end_page: End page number (1-indexed, inclusive)
            
        Returns:
            Combined text
        """
        if not self.pages:
            self.parse_all_pages()
        
        text_parts = []
        for page in self.pages:
            if start_page <= page.page_number <= end_page:
                text_parts.append(page.text)
        
        return '\n\n'.join(text_parts)
    
    def get_metadata(self) -> Dict:
        """
        Get PDF metadata.
        
        Returns:
            Dictionary of metadata
        """
        if not self.doc:
            raise RuntimeError("PDF document not opened")
        
        metadata = {
            "title": self.doc.metadata.get("title", ""),
            "author": self.doc.metadata.get("author", ""),
            "subject": self.doc.metadata.get("subject", ""),
            "creator": self.doc.metadata.get("creator", ""),
            "producer": self.doc.metadata.get("producer", ""),
            "creation_date": self.doc.metadata.get("creationDate", ""),
            "modification_date": self.doc.metadata.get("modDate", ""),
            "page_count": len(self.doc),
            "file_size": self.pdf_path.stat().st_size,
        }
        
        return metadata
