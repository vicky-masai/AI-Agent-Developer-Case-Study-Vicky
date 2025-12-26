"""
Configuration management for CSRD extraction system.
Handles environment variables, API keys, and application settings.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Project paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    # OpenAI Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model_primary: str = Field(default="gpt-4-turbo-preview")
    openai_model_fallback: str = Field(default="gpt-3.5-turbo")
    openai_max_tokens: int = Field(default=4096)
    openai_temperature: float = Field(default=0.1)
    
    # Database Configuration
    database_url: str = Field(default="sqlite:///database/csrd_extraction.db")
    database_echo: bool = Field(default=False)
    
    # Vector Store Configuration
    vector_store_path: str = Field(default="database/chromadb")
    embedding_model: str = Field(default="text-embedding-3-small")
    
    # Application Settings
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/csrd_extraction.log")
    cache_enabled: bool = Field(default=True)
    cache_dir: str = Field(default="data/cache")
    
    # Processing Configuration
    max_workers: int = Field(default=4)
    batch_size: int = Field(default=5)
    retry_attempts: int = Field(default=3)
    retry_delay: int = Field(default=2)
    
    # Extraction Settings
    confidence_threshold: float = Field(default=0.6)
    min_context_length: int = Field(default=100)
    max_context_length: int = Field(default=4000)
    
    # Cost Optimization
    enable_caching: bool = Field(default=True)
    use_fallback_model: bool = Field(default=True)
    max_api_cost_usd: float = Field(default=100.0)
    
    @field_validator("openai_api_key")
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        """Validate that API key is provided."""
        if not v or v == "your_openai_api_key_here":
            raise ValueError(
                "OpenAI API key not configured. "
                "Please set OPENAI_API_KEY in .env file"
            )
        return v
    
    @field_validator("confidence_threshold")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        """Validate confidence threshold is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Confidence threshold must be between 0 and 1")
        return v
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """Convert relative path to absolute path from project root."""
        return self.project_root / relative_path
    
    def ensure_directories(self) -> None:
        """Create necessary directories if they don't exist."""
        directories = [
            self.get_absolute_path("data/reports"),
            self.get_absolute_path("data/processed"),
            self.get_absolute_path("data/output"),
            self.get_absolute_path("data/cache"),
            self.get_absolute_path("database"),
            self.get_absolute_path("logs"),
            self.get_absolute_path(self.vector_store_path),
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    @property
    def reports_dir(self) -> Path:
        """Get reports directory path."""
        return self.get_absolute_path("data/reports")
    
    @property
    def output_dir(self) -> Path:
        """Get output directory path."""
        return self.get_absolute_path("data/output")
    
    @property
    def database_path(self) -> Path:
        """Get database file path."""
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            return self.get_absolute_path(db_path)
        return Path(self.database_url)


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    settings = Settings()
    settings.ensure_directories()
    return settings


# Convenience function to get settings
def load_settings() -> Settings:
    """Load and return settings."""
    return get_settings()
