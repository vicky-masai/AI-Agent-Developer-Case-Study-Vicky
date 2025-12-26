"""
Indicator extractor for CSRD sustainability data.
Orchestrates extraction for individual indicators using LLM and document context.
"""

from typing import Optional, Dict, List, Any

from src.models import Indicator
from src.parsers import PageContent, DocumentPreprocessor
from src.services import LLMService
from src.utils import get_logger
from .extraction_prompts import ExtractionPrompts

logger = get_logger(__name__)


class IndicatorExtractor:
    """
    Extracts specific sustainability indicators from documents.
    Uses LLM with relevant context to extract and validate data.
    """
    
    def __init__(
        self,
        llm_service: LLMService,
        preprocessor: DocumentPreprocessor,
    ):
        """
        Initialize indicator extractor.
        
        Args:
            llm_service: LLM service instance
            preprocessor: Document preprocessor instance
        """
        self.llm_service = llm_service
        self.preprocessor = preprocessor
        self.prompts = ExtractionPrompts()
        
        logger.info("Initialized IndicatorExtractor")
    
    def extract_indicator(
        self,
        indicator: Indicator,
        pages: List[PageContent],
        company_name: str = "",
    ) -> Dict[str, Any]:
        """
        Extract a specific indicator from document pages.
        
        Args:
            indicator: Indicator to extract
            pages: List of document pages
            company_name: Name of the company (for context)
            
        Returns:
            Dictionary with extraction results
        """
        logger.info(f"Extracting indicator: {indicator.name}")
        
        try:
            # Step 1: Find relevant contexts
            contexts = self.preprocessor.create_context_for_indicator(
                indicator_name=indicator.name,
                pages=pages,
                max_contexts=5,
            )
            
            if not contexts:
                logger.warning(f"No relevant context found for: {indicator.name}")
                return self._create_not_found_result(indicator, "No relevant context found in document")
            
            # Step 2: Try extraction with top contexts
            best_result = None
            best_confidence = 0.0
            
            for i, context in enumerate(contexts[:3]):  # Try top 3 contexts
                logger.info(
                    f"Attempting extraction with context {i+1} "
                    f"(page {context['page_number']}, relevance={context['relevance_score']})"
                )
                
                result = self._extract_from_context(
                    indicator=indicator,
                    context=context,
                    company_name=company_name,
                )
                
                if result and result.get('confidence', 0) > best_confidence:
                    best_result = result
                    best_confidence = result.get('confidence', 0)
                
                # If we found a high-confidence result, stop searching
                if best_confidence >= 0.8:
                    logger.info(f"High confidence result found ({best_confidence:.2f}), stopping search")
                    break
            
            if not best_result or best_result.get('value') == 'NOT_FOUND':
                return self._create_not_found_result(
                    indicator,
                    f"Indicator not found after checking {len(contexts)} contexts"
                )
            
            # Step 3: Post-process and validate result
            processed_result = self._post_process_result(best_result, indicator)
            
            logger.info(
                f"Successfully extracted {indicator.name}: "
                f"value={processed_result.get('value')}, "
                f"confidence={processed_result.get('confidence'):.2f}"
            )
            
            return processed_result
            
        except Exception as e:
            logger.error(f"Error extracting indicator {indicator.name}: {e}")
            return self._create_error_result(indicator, str(e))
    
    def _extract_from_context(
        self,
        indicator: Indicator,
        context: Dict,
        company_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Extract indicator from a specific context using LLM.
        
        Args:
            indicator: Indicator to extract
            context: Context dictionary with text and metadata
            company_name: Company name
            
        Returns:
            Extraction result dictionary
        """
        try:
            # Get extraction prompt
            prompt = self.prompts.get_extraction_prompt(
                indicator_name=indicator.name,
                unit=indicator.unit,
                description=indicator.description or "",
            )
            
            # Add company context
            if company_name:
                prompt = f"Company: {company_name}\n\n" + prompt
            
            # Call LLM
            llm_response = self.llm_service.extract_with_llm(
                prompt=prompt,
                context=context['text'],
                use_cache=True,
            )
            
            # Parse response
            parsed_result = self.llm_service.parse_extraction_response(
                llm_response['content']
            )
            
            # Add metadata
            parsed_result['model_used'] = llm_response['model']
            parsed_result['tokens_used'] = llm_response['total_tokens']
            parsed_result['cost_usd'] = llm_response['cost_usd']
            parsed_result['raw_text'] = context['text'][:500]  # Store snippet
            
            # Use context page if not specified in response
            if not parsed_result.get('source_page'):
                parsed_result['source_page'] = context['page_number']
            
            return parsed_result
            
        except Exception as e:
            logger.error(f"Error in LLM extraction: {e}")
            return None
    
    def _post_process_result(
        self,
        result: Dict[str, Any],
        indicator: Indicator,
    ) -> Dict[str, Any]:
        """
        Post-process extraction result.
        
        Args:
            result: Raw extraction result
            indicator: Indicator definition
            
        Returns:
            Processed result
        """
        # Try to normalize numeric value
        value_str = result.get('value', '')
        numeric_value = self.preprocessor.normalize_value(value_str)
        
        result['numeric_value'] = numeric_value
        result['unit'] = indicator.unit
        
        # Validate confidence
        confidence = result.get('confidence', 0.0)
        if not isinstance(confidence, (int, float)):
            confidence = 0.5
        result['confidence'] = max(0.0, min(1.0, float(confidence)))
        
        # Add extraction method
        if not result.get('extraction_method'):
            if 'table' in result.get('raw_text', '').lower()[:200]:
                result['extraction_method'] = 'table'
            else:
                result['extraction_method'] = 'direct'
        
        return result
    
    def _create_not_found_result(
        self,
        indicator: Indicator,
        reason: str,
    ) -> Dict[str, Any]:
        """Create result for indicator not found."""
        return {
            'value': None,
            'numeric_value': None,
            'unit': indicator.unit,
            'confidence': 0.0,
            'source_page': None,
            'source_section': None,
            'raw_text': None,
            'notes': f"Not found: {reason}",
            'model_used': None,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'extraction_method': 'not_found',
        }
    
    def _create_error_result(
        self,
        indicator: Indicator,
        error_message: str,
    ) -> Dict[str, Any]:
        """Create result for extraction error."""
        return {
            'value': None,
            'numeric_value': None,
            'unit': indicator.unit,
            'confidence': 0.0,
            'source_page': None,
            'source_section': None,
            'raw_text': None,
            'notes': f"Extraction error: {error_message}",
            'model_used': None,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'extraction_method': 'error',
        }
    
    def batch_extract_indicators(
        self,
        indicators: List[Indicator],
        pages: List[PageContent],
        company_name: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Extract multiple indicators from document.
        
        Args:
            indicators: List of indicators to extract
            pages: Document pages
            company_name: Company name
            
        Returns:
            List of extraction results
        """
        results = []
        
        logger.info(f"Starting batch extraction of {len(indicators)} indicators")
        
        for i, indicator in enumerate(indicators, 1):
            logger.info(f"Processing indicator {i}/{len(indicators)}: {indicator.name}")
            
            result = self.extract_indicator(
                indicator=indicator,
                pages=pages,
                company_name=company_name,
            )
            
            result['indicator_id'] = indicator.id
            result['indicator_name'] = indicator.name
            results.append(result)
        
        logger.info(f"Completed batch extraction: {len(results)} results")
        
        return results
