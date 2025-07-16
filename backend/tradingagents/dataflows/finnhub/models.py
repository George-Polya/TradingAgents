"""
FinnHub data models using Pydantic for validation
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator


class Quote(BaseModel):
    """Real-time quote data"""
    current_price: float = Field(alias='c')
    change: float = Field(alias='d')
    percent_change: float = Field(alias='dp')
    high: float = Field(alias='h')
    low: float = Field(alias='l')
    open: float = Field(alias='o')
    previous_close: float = Field(alias='pc')
    timestamp: int = Field(alias='t')
    
    class Config:
        allow_population_by_field_name = True
    
    @validator('timestamp')
    def validate_timestamp(cls, v):
        """Convert timestamp to datetime if needed"""
        return v


class CompanyProfile(BaseModel):
    """Company profile information"""
    symbol: str = Field(default='')
    name: str
    country: str
    currency: str
    exchange: str
    ipo_date: str = Field(alias='ipo')
    market_capitalization: float = Field(alias='marketCapitalization')
    phone: str
    outstanding_shares: float = Field(alias='shareOutstanding')
    website: str = Field(alias='weburl')
    logo: str
    industry: str = Field(alias='finnhubIndustry')
    
    class Config:
        allow_population_by_field_name = True


class CompanyNews(BaseModel):
    """Company news article"""
    category: str
    datetime: int
    headline: str
    id: int
    image: str
    related: str
    source: str
    summary: str
    url: str
    
    @validator('datetime')
    def convert_timestamp(cls, v):
        """Keep as timestamp for now, convert when needed"""
        return v
    
    def get_datetime(self) -> datetime:
        """Convert timestamp to datetime object"""
        return datetime.fromtimestamp(self.datetime)


class MarketNews(BaseModel):
    """Market news article"""
    category: str
    datetime: int
    headline: str
    id: int
    image: str
    related: str
    source: str
    summary: str
    url: str
    
    def get_datetime(self) -> datetime:
        """Convert timestamp to datetime object"""
        return datetime.fromtimestamp(self.datetime)


class InsiderSentiment(BaseModel):
    """Insider sentiment data"""
    symbol: str
    year: int
    month: int
    change: float
    mspr: float  # Monthly Share Purchase Ratio
    
    class Config:
        allow_population_by_field_name = True


class InsiderTransaction(BaseModel):
    """Insider transaction data"""
    symbol: str
    name: str
    share: float
    change: float
    filing_date: str = Field(alias='filingDate')
    transaction_date: str = Field(alias='transactionDate')
    transaction_price: float = Field(alias='transactionPrice')
    transaction_code: str = Field(alias='transactionCode')
    
    class Config:
        allow_population_by_field_name = True