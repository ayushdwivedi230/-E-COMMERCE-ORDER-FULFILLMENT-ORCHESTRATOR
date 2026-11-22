import os
from decimal import Decimal
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "E-Commerce Order Fulfillment Orchestrator"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "sqlite:///./ecommerce.db"
    
    @property
    def effective_database_url(self) -> str:
        # Check specific override first
        url = self.DATABASE_URL
        if "ECOMMERCE_DATABASE_URL" in os.environ:
            url = os.environ["ECOMMERCE_DATABASE_URL"]
        # Discard unrelated ambient system environment variables from other projects
        elif "SmartBookingSalon" in url:
            url = "sqlite:///./ecommerce.db"
        # Standardize PostgreSQL URI scheme for SQLAlchemy compatibility
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            try:
                import psycopg  # noqa: F401
            except ImportError:
                # Fallback to psycopg2 if psycopg v3 is not installed
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    # Fraud Risk Thresholds
    FRAUD_LOW_THRESHOLD: int = 29
    FRAUD_MEDIUM_THRESHOLD: int = 69
    FRAUD_HIGH_THRESHOLD: int = 70

    # Pricing Parameters (Decimal)
    DEFAULT_TAX_RATE: Decimal = Decimal("0.08")
    FREE_SHIPPING_THRESHOLD: Decimal = Decimal("100.00")
    STANDARD_SHIPPING_COST: Decimal = Decimal("5.00")
    EXPRESS_SHIPPING_COST: Decimal = Decimal("15.00")

    # LLM / AI Configuration
    ENABLE_LLM_REASONING: bool = False
    MODEL_NAME: str = "gpt-4o"
    OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_DEPLOYMENT_NAME: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
