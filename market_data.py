import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from config import TRADING_PAIRS, MA_CONFIG
import time

class MarketDataHandler:
    def __init__(self):
        self.data: Dict[str, pd.DataFrame] = {}
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MarketDataHandler')

    def connect(self):
        """Initialize market data connection"""
        self.logger.info("Initializing market data connection")
        self._fetch_initial_data()
        return True

    def _fetch_initial_data(self):
        """Fetch initial data for all symbols"""
        for symbol in TRADING_PAIRS:
            try:
                self._update_symbol_data(symbol)
                self.logger.info(f"Successfully fetched initial data for {symbol}")
            except Exception as e:
                self.logger.error(f"Error fetching initial data for {symbol}: {e}")

    def _update_symbol_data(self, symbol: str):
        """Update market data for a symbol"""
        try:
            # Download data with 5-minute intervals for the last 2 days
            # This ensures we have enough data for calculations
            data = yf.download(
                symbol,
                interval='5m',
                period='2d',
                progress=False
            )
            
            if data.empty:
                self.logger.warning(f"No data received for {symbol}")
                return
            
            # Calculate weighted close
            data['hlcc4'] = (data['High'] + data['Low'] + data['Close'] + data['Close']) / 4
            
            # Calculate smoothed moving average
            data['sma'] = self._calculate_sma(data['hlcc4'])
            
            # Store the data
            self.data[symbol] = data
            
        except Exception as e:
            self.logger.error(f"Error updating data for {symbol}: {e}")

    def _calculate_sma(self, series: pd.Series) -> pd.Series:
        """Calculate smoothed moving average"""
        return series.ewm(
            span=MA_CONFIG['period'],
            adjust=False
        ).mean().shift(MA_CONFIG['shift'])

    def get_latest_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get latest market data for a symbol"""
        try:
            # Update data before returning
            self._update_symbol_data(symbol)
            return self.data.get(symbol)
        except Exception as e:
            self.logger.error(f"Error getting latest data for {symbol}: {e}")
            return None

    def get_all_symbols_data(self) -> Dict[str, pd.DataFrame]:
        """Get latest market data for all symbols"""
        try:
            # Update all symbols
            for symbol in TRADING_PAIRS:
                self._update_symbol_data(symbol)
            return self.data
        except Exception as e:
            self.logger.error(f"Error getting all symbols data: {e}")
            return {}

    def is_connected(self) -> bool:
        """Check if market data is available"""
        return len(self.data) > 0

    def close(self):
        """Clean up resources"""
        self.data.clear()
        self.logger.info("Market data connection closed") 