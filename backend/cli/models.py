from enum import Enum
from typing import List, Optional, Dict
from pydantic import BaseModel


class AnalystType(str, Enum):
    # MARKET = "market"  # Disabled
    # SOCIAL = "social"  # Disabled
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
