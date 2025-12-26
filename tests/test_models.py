"""Tests for database models and operations."""

import pytest
from src.models import get_db, Company, Indicator, ExtractedData, IndicatorCategory
from src.models.seed_data import seed_database


@pytest.fixture
def db():
    """Get database instance for testing."""
    return get_db()


def test_database_initialization(db):
    """Test database initialization."""
    assert db is not None
    assert db.engine is not None


def test_seed_database(db):
    """Test database seeding."""
    seed_database(db)
    
    # Check indicators
    indicators = db.get_all_indicators()
    assert len(indicators) == 20
    
    # Check companies
    aib = db.get_company_by_name("Allied Irish Banks (AIB)")
    assert aib is not None
    assert aib.country == "Ireland"


def test_create_company(db):
    """Test company creation."""
    company = db.create_company(
        name="Test Company",
        country="Test Country",
        report_year=2024,
    )
    
    assert company.id is not None
    assert company.name == "Test Company"


def test_create_indicator(db):
    """Test indicator creation."""
    indicator = db.create_indicator(
        name="Test Indicator",
        category=IndicatorCategory.ENVIRONMENTAL,
        unit="test_unit",
        indicator_number=99,
    )
    
    assert indicator.id is not None
    assert indicator.name == "Test Indicator"


def test_create_extracted_data(db):
    """Test extracted data creation."""
    # Create test company and indicator
    company = db.get_or_create_company(
        name="Test Company 2",
        country="Test",
        report_year=2024,
    )
    
    indicator = db.get_indicator_by_name("Total Scope 1 GHG Emissions")
    
    # Create extracted data
    data = db.create_extracted_data(
        company_id=company.id,
        indicator_id=indicator.id,
        value="1000",
        numeric_value=1000.0,
        confidence=0.9,
        source_page=10,
    )
    
    assert data.id is not None
    assert data.value == "1000"
    assert data.confidence == 0.9
