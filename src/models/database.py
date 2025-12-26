"""
Database management for CSRD extraction system.
Handles database initialization, connections, and CRUD operations.
"""

from contextlib import contextmanager
from typing import List, Optional, Generator
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.config import get_settings
from src.utils import get_logger
from .models import Base, Company, Indicator, ExtractedData, IndicatorCategory

logger = get_logger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL (uses settings if not provided)
        """
        settings = get_settings()
        self.database_url = database_url or settings.database_url
        
        # Create engine with appropriate settings
        if self.database_url.startswith("sqlite"):
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.database_echo,
            )
        else:
            self.engine = create_engine(
                self.database_url,
                echo=settings.database_echo,
            )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info(f"Database manager initialized with URL: {self.database_url}")
    
    def create_tables(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Get a database session with automatic cleanup.
        
        Yields:
            Database session
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # Company operations
    def create_company(
        self,
        name: str,
        country: str,
        report_year: int,
        sector: Optional[str] = None,
        report_url: Optional[str] = None,
        report_filename: Optional[str] = None,
    ) -> Company:
        """Create a new company record."""
        with self.get_session() as session:
            company = Company(
                name=name,
                country=country,
                sector=sector,
                report_year=report_year,
                report_url=report_url,
                report_filename=report_filename,
            )
            session.add(company)
            session.flush()
            session.refresh(company)
            logger.info(f"Created company: {company}")
            return company
    
    def get_company_by_name(self, name: str) -> Optional[Company]:
        """Get company by name."""
        with self.get_session() as session:
            stmt = select(Company).where(Company.name == name)
            return session.execute(stmt).scalar_one_or_none()
    
    def get_or_create_company(
        self,
        name: str,
        country: str,
        report_year: int,
        **kwargs
    ) -> Company:
        """Get existing company or create new one."""
        company = self.get_company_by_name(name)
        if company:
            logger.info(f"Found existing company: {name}")
            return company
        return self.create_company(name, country, report_year, **kwargs)
    
    # Indicator operations
    def create_indicator(
        self,
        name: str,
        category: IndicatorCategory,
        unit: str,
        indicator_number: int,
        description: Optional[str] = None,
        esrs_reference: Optional[str] = None,
    ) -> Indicator:
        """Create a new indicator."""
        with self.get_session() as session:
            indicator = Indicator(
                name=name,
                category=category,
                unit=unit,
                indicator_number=indicator_number,
                description=description,
                esrs_reference=esrs_reference,
            )
            session.add(indicator)
            session.flush()
            session.refresh(indicator)
            logger.info(f"Created indicator: {indicator}")
            return indicator
    
    def get_indicator_by_name(self, name: str) -> Optional[Indicator]:
        """Get indicator by name."""
        with self.get_session() as session:
            stmt = select(Indicator).where(Indicator.name == name)
            return session.execute(stmt).scalar_one_or_none()
    
    def get_all_indicators(self) -> List[Indicator]:
        """Get all indicators ordered by number."""
        with self.get_session() as session:
            stmt = select(Indicator).order_by(Indicator.indicator_number)
            return list(session.execute(stmt).scalars().all())
    
    # Extracted data operations
    def create_extracted_data(
        self,
        company_id: int,
        indicator_id: int,
        value: Optional[str] = None,
        numeric_value: Optional[float] = None,
        unit: Optional[str] = None,
        confidence: float = 0.0,
        source_page: Optional[int] = None,
        source_section: Optional[str] = None,
        raw_text: Optional[str] = None,
        notes: Optional[str] = None,
        extraction_method: Optional[str] = None,
        model_used: Optional[str] = None,
    ) -> ExtractedData:
        """Create a new extracted data record."""
        with self.get_session() as session:
            data = ExtractedData(
                company_id=company_id,
                indicator_id=indicator_id,
                value=value,
                numeric_value=numeric_value,
                unit=unit,
                confidence=confidence,
                source_page=source_page,
                source_section=source_section,
                raw_text=raw_text,
                notes=notes,
                extraction_method=extraction_method,
                model_used=model_used,
            )
            session.add(data)
            session.flush()
            session.refresh(data)
            logger.info(f"Created extracted data: company_id={company_id}, indicator_id={indicator_id}")
            return data
    
    def get_extracted_data(
        self,
        company_id: Optional[int] = None,
        indicator_id: Optional[int] = None,
    ) -> List[ExtractedData]:
        """Get extracted data with optional filters."""
        with self.get_session() as session:
            stmt = select(ExtractedData)
            
            if company_id:
                stmt = stmt.where(ExtractedData.company_id == company_id)
            if indicator_id:
                stmt = stmt.where(ExtractedData.indicator_id == indicator_id)
            
            return list(session.execute(stmt).scalars().all())
    
    def get_all_extracted_data(self) -> List[ExtractedData]:
        """Get all extracted data."""
        with self.get_session() as session:
            stmt = select(ExtractedData).order_by(
                ExtractedData.company_id,
                ExtractedData.indicator_id
            )
            return list(session.execute(stmt).scalars().all())


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get global database manager instance."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.create_tables()
    return _db_manager


def initialize_database() -> DatabaseManager:
    """Initialize database and create tables."""
    db = get_db()
    logger.info("Database initialized successfully")
    return db
