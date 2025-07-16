"""
FinnHub utility functions for backward compatibility

Maintains the same interface as the original finnhub_utils.py
"""

import json
import os
from typing import Dict, Any, Optional


def get_data_in_range(
    ticker: str,
    start_date: str,
    end_date: str,
    data_type: str,
    data_dir: str,
    period: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gets finnhub data saved and processed on disk.
    
    This function maintains backward compatibility with the original finnhub_utils.py
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        data_type: Type of data from finnhub to fetch. Can be:
                  - insider_trans
                  - SEC_filings
                  - news_data
                  - insider_senti
                  - fin_as_reported
        data_dir: Directory where the data is saved
        period: Default to None, if specified should be 'annual' or 'quarterly'
        
    Returns:
        Dictionary with date as key and data as value
    """
    # Construct file path
    if period:
        data_path = os.path.join(
            data_dir,
            "finnhub_data",
            data_type,
            f"{ticker}_{period}_data_formatted.json"
        )
    else:
        data_path = os.path.join(
            data_dir,
            "finnhub_data",
            data_type,
            f"{ticker}_data_formatted.json"
        )
    
    # Check if file exists
    if not os.path.exists(data_path):
        # Return empty dict if file doesn't exist
        return {}
    
    try:
        # Read and parse JSON data
        with open(data_path, "r") as f:
            data = json.load(f)
        
        # Filter by date range
        filtered_data = {}
        for key, value in data.items():
            # key is date string in YYYY-MM-DD format
            if start_date <= key <= end_date and len(value) > 0:
                filtered_data[key] = value
        
        return filtered_data
        
    except (json.JSONDecodeError, IOError) as e:
        # Log error and return empty dict
        print(f"Error reading finnhub data from {data_path}: {e}")
        return {}