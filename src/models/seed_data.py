"""
Seed data for CSRD indicators.
Defines the 20 sustainability indicators to be extracted.
"""

from src.models import IndicatorCategory

# 20 CSRD Sustainability Indicators
INDICATORS = [
    # Environmental Indicators (ESRS E1 - Climate Change)
    {
        "number": 1,
        "name": "Total Scope 1 GHG Emissions",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "tCO₂e",
        "description": "Direct greenhouse gas emissions from owned or controlled sources",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 2,
        "name": "Total Scope 2 GHG Emissions",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "tCO₂e",
        "description": "Indirect greenhouse gas emissions from purchased energy",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 3,
        "name": "Total Scope 3 GHG Emissions",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "tCO₂e",
        "description": "All other indirect greenhouse gas emissions in value chain",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 4,
        "name": "GHG Emissions Intensity",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "tCO₂e per €M revenue",
        "description": "Greenhouse gas emissions per million euros of revenue",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 5,
        "name": "Total Energy Consumption",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "MWh or GJ",
        "description": "Total energy consumed from all sources",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 6,
        "name": "Renewable Energy Percentage",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "%",
        "description": "Percentage of energy from renewable sources",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 7,
        "name": "Net Zero Target Year",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "year",
        "description": "Target year for achieving net zero emissions",
        "esrs_reference": "ESRS E1",
    },
    {
        "number": 8,
        "name": "Green Financing Volume",
        "category": IndicatorCategory.ENVIRONMENTAL,
        "unit": "€ millions",
        "description": "Volume of green or sustainable financing provided",
        "esrs_reference": "ESRS E1",
    },
    
    # Social Indicators (ESRS S1 - Own Workforce)
    {
        "number": 9,
        "name": "Total Employees",
        "category": IndicatorCategory.SOCIAL,
        "unit": "FTE",
        "description": "Total number of full-time equivalent employees",
        "esrs_reference": "ESRS S1",
    },
    {
        "number": 10,
        "name": "Female Employees",
        "category": IndicatorCategory.SOCIAL,
        "unit": "%",
        "description": "Percentage of female employees in workforce",
        "esrs_reference": "ESRS S1",
    },
    {
        "number": 11,
        "name": "Gender Pay Gap",
        "category": IndicatorCategory.SOCIAL,
        "unit": "%",
        "description": "Gender pay gap percentage",
        "esrs_reference": "ESRS S1",
    },
    {
        "number": 12,
        "name": "Training Hours per Employee",
        "category": IndicatorCategory.SOCIAL,
        "unit": "hours",
        "description": "Average training hours per employee per year",
        "esrs_reference": "ESRS S1",
    },
    {
        "number": 13,
        "name": "Employee Turnover Rate",
        "category": IndicatorCategory.SOCIAL,
        "unit": "%",
        "description": "Annual employee turnover rate",
        "esrs_reference": "ESRS S1",
    },
    {
        "number": 14,
        "name": "Work-Related Accidents",
        "category": IndicatorCategory.SOCIAL,
        "unit": "count",
        "description": "Number of work-related accidents",
        "esrs_reference": "ESRS S1",
    },
    {
        "number": 15,
        "name": "Collective Bargaining Coverage",
        "category": IndicatorCategory.SOCIAL,
        "unit": "%",
        "description": "Percentage of employees covered by collective bargaining agreements",
        "esrs_reference": "ESRS S1",
    },
    
    # Governance Indicators (ESRS G1 & ESRS 2)
    {
        "number": 16,
        "name": "Board Female Representation",
        "category": IndicatorCategory.GOVERNANCE,
        "unit": "%",
        "description": "Percentage of female board members",
        "esrs_reference": "ESRS G1",
    },
    {
        "number": 17,
        "name": "Board Meetings",
        "category": IndicatorCategory.GOVERNANCE,
        "unit": "count/year",
        "description": "Number of board meetings per year",
        "esrs_reference": "ESRS G1",
    },
    {
        "number": 18,
        "name": "Corruption Incidents",
        "category": IndicatorCategory.GOVERNANCE,
        "unit": "count",
        "description": "Number of confirmed corruption incidents",
        "esrs_reference": "ESRS G1",
    },
    {
        "number": 19,
        "name": "Avg Payment Period to Suppliers",
        "category": IndicatorCategory.GOVERNANCE,
        "unit": "days",
        "description": "Average payment period to suppliers in days",
        "esrs_reference": "ESRS 2",
    },
    {
        "number": 20,
        "name": "Suppliers Screened for ESG",
        "category": IndicatorCategory.GOVERNANCE,
        "unit": "%",
        "description": "Percentage of suppliers screened for ESG criteria",
        "esrs_reference": "ESRS 2",
    },
]


# Company information for the three banks
COMPANIES = [
    {
        "name": "Allied Irish Banks (AIB)",
        "country": "Ireland",
        "sector": "Banking",
        "report_year": 2025,
        "report_url": "https://www.aib.ie",
        "report_filename": "AIB_2024_Annual_Financial_Report.pdf",
    },
    {
        "name": "BBVA",
        "country": "Spain",
        "sector": "Banking",
        "report_year": 2025,
        "report_url": "https://shareholdersandinvestors.bbva.com",
        "report_filename": "BBVA_2024_Consolidated_Management_Report.pdf",
    },
    {
        "name": "Groupe BPCE",
        "country": "France",
        "sector": "Banking",
        "report_year": 2025,
        "report_url": "https://www.groupebpce.com",
        "report_filename": "BPCE_2024_Universal_Registration_Document.pdf",
    },
]


def seed_indicators(db_manager):
    """Seed the database with indicator definitions."""
    from src.utils import get_logger
    
    logger = get_logger(__name__)
    logger.info("Seeding indicators...")
    
    for indicator_data in INDICATORS:
        try:
            # Check if indicator already exists
            existing = db_manager.get_indicator_by_name(indicator_data["name"])
            if existing:
                logger.info(f"Indicator already exists: {indicator_data['name']}")
                continue
            
            # Create new indicator
            db_manager.create_indicator(
                name=indicator_data["name"],
                category=indicator_data["category"],
                unit=indicator_data["unit"],
                indicator_number=indicator_data["number"],
                description=indicator_data.get("description"),
                esrs_reference=indicator_data.get("esrs_reference"),
            )
            logger.info(f"Created indicator: {indicator_data['name']}")
        except Exception as e:
            logger.error(f"Error creating indicator {indicator_data['name']}: {e}")
    
    logger.info(f"Seeded {len(INDICATORS)} indicators")


def seed_companies(db_manager):
    """Seed the database with company information."""
    from src.utils import get_logger
    
    logger = get_logger(__name__)
    logger.info("Seeding companies...")
    
    for company_data in COMPANIES:
        try:
            db_manager.get_or_create_company(
                name=company_data["name"],
                country=company_data["country"],
                report_year=company_data["report_year"],
                sector=company_data.get("sector"),
                report_url=company_data.get("report_url"),
                report_filename=company_data.get("report_filename"),
            )
            logger.info(f"Seeded company: {company_data['name']}")
        except Exception as e:
            logger.error(f"Error seeding company {company_data['name']}: {e}")
    
    logger.info(f"Seeded {len(COMPANIES)} companies")


def seed_database(db_manager):
    """Seed the database with all initial data."""
    seed_indicators(db_manager)
    seed_companies(db_manager)
