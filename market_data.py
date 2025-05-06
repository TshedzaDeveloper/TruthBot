import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from config import TRADING_PAIRS, MA_CONFIG
import time
from datetime import datetime, timedelta

class MarketDataHandler:
    def __init__(self):
        self.data: Dict[str, pd.DataFrame] = {}
        self.setup_logging()
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
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
            success = False
            retries = 0
            
            while not success and retries < self.max_retries:
                try:
                    self._update_symbol_data(symbol)
                    self.logger.info(f"Successfully fetched initial data for {symbol}")
                    success = True
                except Exception as e:
                    retries += 1
                    if retries < self.max_retries:
                        self.logger.warning(f"Retry {retries}/{self.max_retries} for {symbol}: {str(e)}")
                        time.sleep(self.retry_delay)
                    else:
                        self.logger.error(f"Failed to fetch data for {symbol} after {self.max_retries} attempts: {str(e)}")

    def _update_symbol_data(self, symbol: str):
        """Update market data for a symbol"""
        try:
            # Create ticker object
            ticker = yf.Ticker(symbol)
            
            # Get historical data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=2)
            
            data = ticker.history(
                start=start_time,
                end=end_time,
                interval='5m'
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
            self.logger.error(f"Error updating data for {symbol}: {str(e)}")
            raise

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
            self.logger.error(f"Error getting latest data for {symbol}: {str(e)}")
            return None

    def get_all_symbols_data(self) -> Dict[str, pd.DataFrame]:
        """Get latest market data for all symbols"""
        try:
            # Update all symbols
            for symbol in TRADING_PAIRS:
                try:
                    self._update_symbol_data(symbol)
                except Exception as e:
                    self.logger.error(f"Error updating {symbol}: {str(e)}")
            return self.data
        except Exception as e:
            self.logger.error(f"Error getting all symbols data: {str(e)}")
            return {}

    def is_connected(self) -> bool:
        """Check if market data is available"""
        return len(self.data) > 0

    def close(self):
        """Clean up resources"""
        self.data.clear()
        self.logger.info("Market data connection closed") 