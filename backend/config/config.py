from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
import secrets
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        validate_default=True,
    )

    # PostgreSQL 데이터베이스 설정
    DB_HOST: str = Field(description="Database host")
    DB_PORT: int = Field(ge=1, le=65535, description="Database port")
    DB_USER: str = Field(min_length=1, description="Database username")
    DB_PASSWORD: str = Field(min_length=1, description="Database password")
    DB_NAME: str = Field(min_length=1, description="Database name")
    
    # 보안 설정
    SECRET_KEY: str = Field(min_length=32, description="JWT secret key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=360, ge=1, description="Access token expiration in minutes")
    
    # CORS 설정
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000", description="Allowed CORS origins (comma-separated)")
    
    # 로깅 설정
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FILE: str = Field(default="logs/app.log", description="Log file path")
    
    # API 설정
    API_V1_STR: str = Field(default="/api/v1", description="API prefix")
    PROJECT_NAME: str = Field(default="TradingAgents API", description="Project name")
    
    # Rate Limiting 설정
    RATE_LIMIT_REQUESTS: int = Field(default=100, ge=1, description="Rate limit requests per minute")
    RATE_LIMIT_PERIOD: int = Field(default=60, ge=1, description="Rate limit period in seconds")
    
    # 환경 설정
    ENVIRONMENT: str = Field(default="development", description="Environment (development/staging/production)")
    DEBUG: bool = Field(default=True, description="Debug mode")

    # Supabase 설정
    SUPABASE_URL: str = Field(default="", description="Supabase URL")
    SUPABASE_ANON_KEY: str = Field(default="", description="Supabase Anon Key")
    SUPABASE_SERVICE_KEY: str = Field(default="", description="Supabase Service Key")
    
    # 쿠키 보안 설정
    COOKIE_SECURE: bool | None = Field(default=None, description="Use secure cookies (HTTPS only)")
    COOKIE_SAMESITE: str = Field(default="strict", description="SameSite cookie attribute")
    COOKIE_DOMAIN: str | None = Field(default=None, description="Cookie domain")
    
    @field_validator('ENVIRONMENT')
    @classmethod
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of {allowed_envs}')
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v):
        allowed_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in allowed_levels:
            raise ValueError(f'Log level must be one of {allowed_levels}')
        return v.upper()
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError('SECRET_KEY must be at least 32 characters long')
        return v
    
    @property
    def database_url(self) -> str:
        return f"postgresql+psycopg2://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    @property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',')]
    
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def cookie_secure(self) -> bool:
        """환경에 따라 쿠키 secure 설정을 자동으로 결정"""
        if self.COOKIE_SECURE is not None:
            return self.COOKIE_SECURE
        return self.is_production

@lru_cache 
def get_settings():
    return Settings()