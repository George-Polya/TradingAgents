"""
FinnHub specific exceptions
"""


class FinnHubError(Exception):
    """Base exception for FinnHub provider"""
    pass


class APIKeyError(FinnHubError):
    """Raised when API key is missing or invalid"""
    pass


class RateLimitError(FinnHubError):
    """Raised when API rate limit is exceeded"""
    pass


class DataFetchError(FinnHubError):
    """Raised when data fetch fails"""
    pass


class InvalidSymbolError(FinnHubError):
    """Raised when invalid stock symbol is provided"""
    pass