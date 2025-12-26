"""
Document preprocessing for CSRD reports.
Cleans text, creates chunks, and prepares documents for LLM processing.
"""

import re
from typing import List, Dict, Optional
from dataclasses import dataclass

from src.utils import get_logger
from .pdf_parser import PageContent, DocumentSection

logger = get_logger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text for processing."""
    text: str
    page_number: int
    section: Optional[str] = None
    chunk_index: int = 0
    metadata: Optional[Dict] = None


class DocumentPreprocessor:
    """
    Preprocesses PDF documents for LLM extraction.
    Handles text cleaning, chunking, and section identification.
    """
    
    def __init__(self, max_chunk_size: int = 3000):
        """
        Initialize document preprocessor.
        
        Args:
            max_chunk_size: Maximum characters per chunk
        """
        self.max_chunk_size = max_chunk_size
        logger.info(f"Initialized DocumentPreprocessor (max_chunk_size={max_chunk_size})")
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text from PDF.
        
        Args:
            text: Raw text from PDF
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers (common patterns)
        text = re.sub(r'\b\d+\s*\|\s*Page\b', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\bPage\s*\d+\b', '', text, flags=re.IGNORECASE)
        
        # Remove common PDF artifacts
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        # Normalize quotes and dashes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        text = text.replace('–', '-').replace('—', '-')
        
        # Remove multiple spaces
        text = re.sub(r' +', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def create_chunks(
        self,
        pages: List[PageContent],
        overlap: int = 200
    ) -> List[TextChunk]:
        """
        Create text chunks from pages with overlap.
        
        Args:
            pages: List of PageContent objects
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List of TextChunk objects
        """
        chunks = []
        chunk_index = 0
        
        for page in pages:
            text = self.clean_text(page.text)
            
            if not text:
                continue
            
            # If page text is smaller than max chunk size, create single chunk
            if len(text) <= self.max_chunk_size:
                chunks.append(TextChunk(
                    text=text,
                    page_number=page.page_number,
                    section=page.section,
                    chunk_index=chunk_index,
                ))
                chunk_index += 1
                continue
            
            # Split into multiple chunks with overlap
            start = 0
            while start < len(text):
                end = start + self.max_chunk_size
                
                # Try to break at sentence boundary
                if end < len(text):
                    # Look for sentence end within last 200 chars
                    sentence_end = text.rfind('.', end - 200, end)
                    if sentence_end > start:
                        end = sentence_end + 1
                
                chunk_text = text[start:end].strip()
                
                if chunk_text:
                    chunks.append(TextChunk(
                        text=chunk_text,
                        page_number=page.page_number,
                        section=page.section,
                        chunk_index=chunk_index,
                    ))
                    chunk_index += 1
                
                # Move start position with overlap
                start = end - overlap
        
        logger.info(f"Created {len(chunks)} text chunks from {len(pages)} pages")
        return chunks
    
    def identify_relevant_sections(
        self,
        sections: List[DocumentSection],
        keywords: List[str]
    ) -> List[DocumentSection]:
        """
        Identify sections relevant to specific keywords.
        
        Args:
            sections: List of document sections
            keywords: Keywords to search for
            
        Returns:
            Filtered list of relevant sections
        """
        relevant_sections = []
        
        for section in sections:
            section_text = (section.title + " " + section.content).lower()
            
            # Check if any keyword appears in section
            if any(keyword.lower() in section_text for keyword in keywords):
                relevant_sections.append(section)
                logger.debug(f"Found relevant section: {section.title}")
        
        logger.info(f"Identified {len(relevant_sections)} relevant sections from {len(sections)}")
        return relevant_sections
    
    def extract_tables_as_text(self, tables: List[List[List[str]]]) -> str:
        """
        Convert tables to formatted text.
        
        Args:
            tables: List of tables from PDF
            
        Returns:
            Formatted text representation of tables
        """
        if not tables:
            return ""
        
        table_texts = []
        
        for i, table in enumerate(tables):
            if not table:
                continue
            
            # Format table as text
            table_text = f"\n[Table {i+1}]\n"
            
            for row in table:
                # Clean and join cells
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                table_text += " | ".join(cleaned_row) + "\n"
            
            table_texts.append(table_text)
        
        return "\n".join(table_texts)
    
    def create_context_for_indicator(
        self,
        indicator_name: str,
        pages: List[PageContent],
        max_contexts: int = 5
    ) -> List[Dict]:
        """
        Create relevant contexts for a specific indicator.
        
        Args:
            indicator_name: Name of the indicator
            pages: List of page contents
            max_contexts: Maximum number of contexts to return
            
        Returns:
            List of context dictionaries
        """
        # Extract keywords from indicator name
        keywords = self._extract_keywords(indicator_name)
        
        contexts = []
        
        for page in pages:
            page_text = self.clean_text(page.text).lower()
            
            # Calculate relevance score
            relevance_score = sum(
                page_text.count(keyword.lower()) 
                for keyword in keywords
            )
            
            if relevance_score > 0:
                # Include tables if present
                table_text = self.extract_tables_as_text(page.tables)
                
                full_text = page.text
                if table_text:
                    full_text += "\n\n" + table_text
                
                contexts.append({
                    "page_number": page.page_number,
                    "text": self.clean_text(full_text),
                    "relevance_score": relevance_score,
                    "has_tables": len(page.tables) > 0,
                })
        
        # Sort by relevance and return top contexts
        contexts.sort(key=lambda x: x["relevance_score"], reverse=True)
        top_contexts = contexts[:max_contexts]
        
        logger.info(
            f"Found {len(top_contexts)} relevant contexts for '{indicator_name}' "
            f"from {len(contexts)} candidate pages"
        )
        
        return top_contexts
    
    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Input text
            
        Returns:
            List of keywords
        """
        # Remove common words and extract meaningful terms
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for'}
        
        # Split on non-alphanumeric characters
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter stop words and short words
        keywords = [
            word for word in words 
            if word not in stop_words and len(word) > 2
        ]
        
        return keywords
    
    def normalize_value(self, value: str) -> Optional[float]:
        """
        Normalize extracted values to numeric format.
        
        Args:
            value: String value to normalize
            
        Returns:
            Normalized numeric value or None
        """
        if not value:
            return None
        
        # Remove common formatting
        value = value.replace(',', '').replace(' ', '')
        
        # Handle percentages
        if '%' in value:
            value = value.replace('%', '')
        
        # Handle currency symbols
        value = re.sub(r'[€$£¥]', '', value)
        
        # Extract numeric value
        match = re.search(r'-?\d+\.?\d*', value)
        if match:
            try:
                return float(match.group())
            except ValueError:
                return None
        
        return None
