"""
Database models for CSRD sustainability data extraction.
Defines the schema for companies, indicators, and extracted data.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Text,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship
import enum


Base = declarative_base()


class IndicatorCategory(str, enum.Enum):
    """Categories for sustainability indicators."""
    ENVIRONMENTAL = "Environmental"
    SOCIAL = "Social"
    GOVERNANCE = "Governance"


class Company(Base):
    """Company information table."""
    
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    country = Column(String(100), nullable=False)
    sector = Column(String(100), nullable=True)
    report_year = Column(Integer, nullable=False)
    report_url = Column(String(500), nullable=True)
    report_filename = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    extracted_data = relationship("ExtractedData", back_populates="company", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Company(id={self.id}, name='{self.name}', country='{self.country}', year={self.report_year})>"


class Indicator(Base):
    """Sustainability indicator definitions."""
    
    __tablename__ = "indicators"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    category = Column(SQLEnum(IndicatorCategory), nullable=False)
    unit = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    esrs_reference = Column(String(50), nullable=True)  # e.g., "ESRS E1", "ESRS S1"
    indicator_number = Column(Integer, nullable=False)  # 1-20
    extraction_priority = Column(Integer, default=1)  # For processing order
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    extracted_data = relationship("ExtractedData", back_populates="indicator", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_indicator_category', 'category'),
        Index('idx_indicator_number', 'indicator_number'),
    )
    
    def __repr__(self) -> str:
        return f"<Indicator(id={self.id}, name='{self.name}', category='{self.category.value}', unit='{self.unit}')>"


class ExtractedData(Base):
    """Extracted sustainability data points."""
    
    __tablename__ = "extracted_data"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    indicator_id = Column(Integer, ForeignKey("indicators.id"), nullable=False)
    
    # Extracted values
    value = Column(String(255), nullable=True)  # String to handle various formats
    numeric_value = Column(Float, nullable=True)  # Parsed numeric value if applicable
    unit = Column(String(50), nullable=True)  # Actual unit found in document
    
    # Metadata
    confidence = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    source_page = Column(Integer, nullable=True)
    source_section = Column(String(255), nullable=True)
    raw_text = Column(Text, nullable=True)  # Original context from document
    notes = Column(Text, nullable=True)  # Additional notes or warnings
    
    # Processing metadata
    extraction_method = Column(String(100), nullable=True)  # e.g., "direct", "table", "calculated"
    model_used = Column(String(100), nullable=True)  # LLM model used
    extraction_timestamp = Column(DateTime, default=datetime.utcnow)
    validated = Column(Integer, default=0)  # 0=not validated, 1=validated, -1=failed validation
    
    # Relationships
    company = relationship("Company", back_populates="extracted_data")
    indicator = relationship("Indicator", back_populates="extracted_data")
    
    # Indexes
    __table_args__ = (
        Index('idx_company_indicator', 'company_id', 'indicator_id'),
        Index('idx_confidence', 'confidence'),
        Index('idx_extraction_timestamp', 'extraction_timestamp'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<ExtractedData(id={self.id}, company_id={self.company_id}, "
            f"indicator_id={self.indicator_id}, value='{self.value}', "
            f"confidence={self.confidence:.2f})>"
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary for CSV export."""
        return {
            "company": self.company.name if self.company else None,
            "report_year": self.company.report_year if self.company else None,
            "indicator_name": self.indicator.name if self.indicator else None,
            "value": self.value,
            "unit": self.unit or (self.indicator.unit if self.indicator else None),
            "confidence": round(self.confidence, 3),
            "source_page": self.source_page,
            "source_section": self.source_section,
            "notes": self.notes,
        }
