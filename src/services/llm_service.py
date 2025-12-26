"""
LLM service for CSRD data extraction.
Handles OpenAI API integration, prompt management, and response caching.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from openai import OpenAI
import tiktoken

from src.config import get_settings
from src.utils import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractionResult:
    """Result from LLM extraction."""
    value: Optional[str]
    confidence: float
    source_page: Optional[int]
    source_section: Optional[str]
    raw_text: Optional[str]
    notes: Optional[str]
    model_used: str
    tokens_used: int
    cost_usd: float


class LLMService:
    """
    Service for interacting with OpenAI LLMs.
    Handles API calls, caching, retries, and cost tracking.
    """
    
    # Token costs per 1K tokens (as of 2024)
    TOKEN_COSTS = {
        "gpt-4-turbo-preview": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
    }
    
    def __init__(self):
        """Initialize LLM service."""
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key)
        
        # Initialize cache
        self.cache_dir = self.settings.get_absolute_path(self.settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Cost tracking
        self.total_cost = 0.0
        self.total_tokens = 0
        
        logger.info(f"Initialized LLM service with model: {self.settings.openai_model_primary}")
    
    def _get_cache_key(self, prompt: str, model: str) -> str:
        """Generate cache key for prompt."""
        content = f"{model}:{prompt}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Retrieve response from cache."""
        if not self.settings.enable_caching:
            return None
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_data
            except Exception as e:
                logger.warning(f"Error reading cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: Dict) -> None:
        """Save response to cache."""
        if not self.settings.enable_caching:
            return
        
        cache_file = self.cache_dir / f"{cache_key}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved to cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Error saving to cache: {e}")
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost."""
        costs = self.TOKEN_COSTS.get(model, self.TOKEN_COSTS["gpt-3.5-turbo"])
        
        input_cost = (input_tokens / 1000) * costs["input"]
        output_cost = (output_tokens / 1000) * costs["output"]
        
        return input_cost + output_cost
    
    def _count_tokens(self, text: str, model: str) -> int:
        """Count tokens in text."""
        try:
            encoding = tiktoken.encoding_for_model(model)
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimate
            return len(text) // 4
    
    def extract_with_llm(
        self,
        prompt: str,
        context: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Extract data using LLM.
        
        Args:
            prompt: Extraction prompt
            context: Context text from document
            model: Model to use (uses primary model if not specified)
            temperature: Temperature for generation
            max_tokens: Maximum tokens in response
            use_cache: Whether to use caching
            
        Returns:
            Dictionary with extraction results
        """
        model = model or self.settings.openai_model_primary
        temperature = temperature if temperature is not None else self.settings.openai_temperature
        max_tokens = max_tokens or self.settings.openai_max_tokens
        
        # Create full prompt
        full_prompt = f"{prompt}\n\nContext:\n{context}"
        
        # Check cache
        cache_key = self._get_cache_key(full_prompt, model)
        if use_cache:
            cached_response = self._get_from_cache(cache_key)
            if cached_response:
                logger.info("Using cached LLM response")
                return cached_response
        
        # Make API call with retry logic
        for attempt in range(self.settings.retry_attempts):
            try:
                logger.info(f"Calling LLM API (model={model}, attempt={attempt+1})")
                
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at extracting structured sustainability data from corporate reports. Provide accurate, precise answers based only on the given context."
                        },
                        {
                            "role": "user",
                            "content": full_prompt
                        }
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                
                # Extract response
                content = response.choices[0].message.content
                
                # Calculate cost
                input_tokens = response.usage.prompt_tokens
                output_tokens = response.usage.completion_tokens
                cost = self._calculate_cost(model, input_tokens, output_tokens)
                
                # Update tracking
                self.total_tokens += input_tokens + output_tokens
                self.total_cost += cost
                
                result = {
                    "content": content,
                    "model": model,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "cost_usd": cost,
                }
                
                # Save to cache
                if use_cache:
                    self._save_to_cache(cache_key, result)
                
                logger.info(
                    f"LLM call successful (tokens={result['total_tokens']}, "
                    f"cost=${cost:.4f}, total_cost=${self.total_cost:.4f})"
                )
                
                return result
                
            except Exception as e:
                logger.error(f"LLM API error (attempt {attempt+1}): {e}")
                
                if attempt < self.settings.retry_attempts - 1:
                    # Try fallback model if configured
                    if self.settings.use_fallback_model and model == self.settings.openai_model_primary:
                        logger.info(f"Switching to fallback model: {self.settings.openai_model_fallback}")
                        model = self.settings.openai_model_fallback
                    
                    # Wait before retry
                    wait_time = self.settings.retry_delay * (2 ** attempt)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise
        
        raise RuntimeError("LLM extraction failed after all retries")
    
    def parse_extraction_response(self, response_content: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format.
        
        Args:
            response_content: Raw LLM response
            
        Returns:
            Parsed extraction data
        """
        # Try to parse as JSON first
        try:
            # Look for JSON in response
            json_match = response_content.strip()
            if json_match.startswith('{') and json_match.endswith('}'):
                return json.loads(json_match)
        except json.JSONDecodeError:
            pass
        
        # Fallback: parse structured text response
        result = {
            "value": None,
            "confidence": 0.0,
            "source_page": None,
            "source_section": None,
            "notes": None,
        }
        
        lines = response_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip()
                
                if 'value' in key:
                    result['value'] = value
                elif 'confidence' in key:
                    try:
                        result['confidence'] = float(value.replace('%', '')) / 100
                    except ValueError:
                        pass
                elif 'page' in key:
                    try:
                        result['source_page'] = int(value)
                    except ValueError:
                        pass
                elif 'section' in key:
                    result['source_section'] = value
                elif 'note' in key:
                    result['notes'] = value
        
        return result
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Get cost and usage summary."""
        return {
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "max_cost_usd": self.settings.max_api_cost_usd,
            "cost_percentage": round((self.total_cost / self.settings.max_api_cost_usd) * 100, 2),
        }
