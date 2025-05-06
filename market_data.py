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
        self.connected = False
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MarketDataHandler')

    def connect(self) -> bool:
        """Initialize market data connection"""
        self.logger.info("Initializing market data connection")
        try:
            # Test connection with a simple data fetch
            test_symbol = TRADING_PAIRS[0]
            ticker = yf.Ticker(test_symbol)
            test_data = ticker.history(period='1d')
            
            if not test_data.empty:
                self.logger.info("Successfully connected to market data")
                self.connected = True
                # Now fetch initial data for all symbols
                self._fetch_initial_data()
                return True
            else:
                self.logger.error("Failed to establish market data connection")
                self.connected = False
                return False
        except Exception as e:
            self.logger.error(f"Error connecting to market data: {str(e)}")
            self.connected = False
            return False

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
            
            # Get historical data - fetch 7 days of data for better analysis
            end_time = datetime.now()
            start_time = end_time - timedelta(days=7)
            
            # Try different intervals in order of preference
            intervals = ['5m', '15m', '1h']
            data = None
            
            for interval in intervals:
                self.logger.info(f"Attempting to fetch {symbol} data with {interval} interval")
                temp_data = ticker.history(
                    start=start_time,
                    end=end_time,
                    interval=interval,
                    prepost=True  # Include pre/post market data
                )
                
                if not temp_data.empty and len(temp_data) > 50:  # Ensure we have enough data points
                    data = temp_data
                    self.logger.info(f"Successfully fetched {symbol} data with {interval} interval: {len(data)} candles")
                    break
                else:
                    self.logger.warning(f"No data received for {symbol} with {interval} interval")
            
            if data is None or data.empty:
                self.logger.error(f"Failed to get data for {symbol} with any interval")
                return
            
            # Verify data quality
            if len(data) < 50:
                self.logger.error(f"Insufficient data points for {symbol}: {len(data)} candles")
                return
                
            # Calculate weighted close
            data['hlcc4'] = (data['High'] + data['Low'] + data['Close'] + data['Close']) / 4
            
            # Calculate smoothed moving average
            data['sma'] = self._calculate_sma(data['hlcc4'])
            
            # Store the data
            self.data[symbol] = data
            self.logger.info(f"Successfully updated data for {symbol} with {len(data)} candles")
            
            # Log the latest price for verification
            latest_price = data['Close'].iloc[-1]
            self.logger.info(f"Latest price for {symbol}: {latest_price}")
            
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
            # Always try to reconnect if not connected
            if not self.connected:
                self.logger.warning("Not connected to market data, attempting to reconnect...")
                if not self.connect():
                    return None
            
            # Update data before returning
            self._update_symbol_data(symbol)
            
            # Verify we have data
            if symbol not in self.data or self.data[symbol] is None or len(self.data[symbol]) == 0:
                self.logger.error(f"No data available for {symbol}")
                return None
                
            return self.data.get(symbol)
            
        except Exception as e:
            self.logger.error(f"Error getting latest data for {symbol}: {str(e)}")
            # Try to reconnect on error
            self.connected = False
            if self.connect():
                return self.get_latest_data(symbol)
            return None

    def get_all_symbols_data(self) -> Dict[str, pd.DataFrame]:
        """Get latest market data for all symbols"""
        if not self.connected:
            self.logger.warning("Not connected to market data")
            return {}
            
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
        return self.connected and len(self.data) > 0

    def close(self):
        """Clean up resources"""
        self.data.clear()
        self.connected = False
        self.logger.info("Market data connection closed") 