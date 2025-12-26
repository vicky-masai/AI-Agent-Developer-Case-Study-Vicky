"""
Extraction prompts for CSRD sustainability indicators.
Provides indicator-specific prompts for LLM extraction.
"""

from typing import Dict


class ExtractionPrompts:
    """Manages extraction prompts for different indicators."""
    
    BASE_PROMPT_TEMPLATE = """You are extracting sustainability data from a CSRD report.

**Indicator**: {indicator_name}
**Unit**: {unit}
**Description**: {description}

**Instructions**:
1. Extract the EXACT value for this indicator from the context below
2. Only use information explicitly stated in the context
3. If the value is in a table, extract it carefully
4. If you find multiple values, use the most recent or aggregate value
5. If the indicator is not found, respond with "NOT_FOUND"

**Response Format** (JSON):
{{
    "value": "extracted value or NOT_FOUND",
    "confidence": 0.0-1.0 (how confident you are),
    "source_page": page number where found (if available),
    "source_section": section name where found,
    "notes": "any relevant notes or clarifications"
}}

**Confidence Scoring Guidelines**:
- 1.0: Exact value found in clear table or explicit statement
- 0.8-0.9: Value found but requires minor interpretation
- 0.6-0.7: Value found but context is ambiguous
- 0.4-0.5: Estimated or calculated from related data
- 0.0-0.3: Very uncertain or not found

Extract the value now:"""
    
    # Indicator-specific guidance
    INDICATOR_GUIDANCE = {
        "Total Scope 1 GHG Emissions": {
            "keywords": ["scope 1", "direct emissions", "GHG", "greenhouse gas", "CO2", "tCO2e"],
            "notes": "Look for direct emissions from owned/controlled sources. May be in emissions table.",
        },
        "Total Scope 2 GHG Emissions": {
            "keywords": ["scope 2", "indirect emissions", "purchased energy", "electricity", "tCO2e"],
            "notes": "Look for emissions from purchased electricity/energy. Check for location-based vs market-based.",
        },
        "Total Scope 3 GHG Emissions": {
            "keywords": ["scope 3", "value chain", "indirect emissions", "tCO2e"],
            "notes": "Look for value chain emissions. May be broken down by category.",
        },
        "GHG Emissions Intensity": {
            "keywords": ["emissions intensity", "tCO2e per", "revenue", "intensity ratio"],
            "notes": "May need to calculate from total emissions and revenue if not explicitly stated.",
        },
        "Total Energy Consumption": {
            "keywords": ["energy consumption", "MWh", "GJ", "total energy"],
            "notes": "Look for total energy use. May include renewable and non-renewable breakdown.",
        },
        "Renewable Energy Percentage": {
            "keywords": ["renewable energy", "renewable %", "green energy", "clean energy"],
            "notes": "Percentage of energy from renewable sources.",
        },
        "Net Zero Target Year": {
            "keywords": ["net zero", "carbon neutral", "target year", "2030", "2040", "2050"],
            "notes": "Look for commitment year for net zero emissions.",
        },
        "Green Financing Volume": {
            "keywords": ["green financing", "sustainable finance", "green loans", "ESG financing", "€", "million"],
            "notes": "Total volume of green/sustainable financing. May be called 'sustainable finance volume'.",
        },
        "Total Employees": {
            "keywords": ["employees", "workforce", "FTE", "headcount", "staff"],
            "notes": "Look for total FTE (Full-Time Equivalent) employees.",
        },
        "Female Employees": {
            "keywords": ["female", "women", "gender", "diversity", "%"],
            "notes": "Percentage of female employees in total workforce.",
        },
        "Gender Pay Gap": {
            "keywords": ["gender pay gap", "pay gap", "wage gap", "%"],
            "notes": "Percentage difference in pay between genders.",
        },
        "Training Hours per Employee": {
            "keywords": ["training", "hours", "learning", "development", "per employee"],
            "notes": "Average training hours per employee per year.",
        },
        "Employee Turnover Rate": {
            "keywords": ["turnover", "attrition", "retention", "%"],
            "notes": "Annual employee turnover rate as percentage.",
        },
        "Work-Related Accidents": {
            "keywords": ["accidents", "injuries", "workplace safety", "incidents"],
            "notes": "Number of work-related accidents or injuries.",
        },
        "Collective Bargaining Coverage": {
            "keywords": ["collective bargaining", "union", "coverage", "%"],
            "notes": "Percentage of employees covered by collective bargaining agreements.",
        },
        "Board Female Representation": {
            "keywords": ["board", "female", "women", "diversity", "directors", "%"],
            "notes": "Percentage of female members on the board of directors.",
        },
        "Board Meetings": {
            "keywords": ["board meetings", "meetings", "sessions"],
            "notes": "Number of board meetings held per year.",
        },
        "Corruption Incidents": {
            "keywords": ["corruption", "bribery", "fraud", "incidents", "cases"],
            "notes": "Number of confirmed corruption incidents.",
        },
        "Avg Payment Period to Suppliers": {
            "keywords": ["payment period", "payment terms", "suppliers", "days", "DPO"],
            "notes": "Average number of days to pay suppliers.",
        },
        "Suppliers Screened for ESG": {
            "keywords": ["suppliers", "ESG", "screening", "assessment", "%"],
            "notes": "Percentage of suppliers screened for ESG criteria.",
        },
    }
    
    @classmethod
    def get_extraction_prompt(
        cls,
        indicator_name: str,
        unit: str,
        description: str = "",
    ) -> str:
        """
        Get extraction prompt for a specific indicator.
        
        Args:
            indicator_name: Name of the indicator
            unit: Unit of measurement
            description: Description of the indicator
            
        Returns:
            Formatted extraction prompt
        """
        # Add indicator-specific guidance if available
        guidance = cls.INDICATOR_GUIDANCE.get(indicator_name, {})
        
        if guidance:
            description += f"\n\nGuidance: {guidance.get('notes', '')}"
            description += f"\nKeywords to look for: {', '.join(guidance.get('keywords', []))}"
        
        prompt = cls.BASE_PROMPT_TEMPLATE.format(
            indicator_name=indicator_name,
            unit=unit,
            description=description,
        )
        
        return prompt
    
    @classmethod
    def get_search_keywords(cls, indicator_name: str) -> list:
        """
        Get search keywords for an indicator.
        
        Args:
            indicator_name: Name of the indicator
            
        Returns:
            List of keywords
        """
        guidance = cls.INDICATOR_GUIDANCE.get(indicator_name, {})
        return guidance.get('keywords', [])
