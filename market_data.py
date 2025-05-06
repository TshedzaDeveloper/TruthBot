import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from config import TRADING_PAIRS, MA_CONFIG
import time
from datetime import datetime, timedelta
import traceback

class MarketDataHandler:
    def __init__(self):
        self.data: Dict[str, pd.DataFrame] = {}
        self.setup_logging()
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.connected = False
        self.symbol_mapping = {
            '^NDX': '^NDX',
            'QQQ': 'QQQ',
            'GC=F': 'GC=F',
            'GBP=X': 'GBP=X'
        }
        
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

    def _update_symbol_data(self, symbol: str) -> None:
        """Update market data for a specific symbol."""
        try:
            # Map symbol to Yahoo Finance format
            yahoo_symbol = self.symbol_mapping.get(symbol, symbol)
            logging.info(f"Fetching data for {symbol} (mapped to {yahoo_symbol})")
            
            # Try different intervals to get the most recent data
            intervals = ['5m', '15m', '1h']  # Removed 1m as it's not reliable for indices
            data = None
            
            for interval in intervals:
                try:
                    # Get data for the last 7 days to ensure we have enough data points
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=7)
                    
                    # Fetch data with the current interval
                    temp_data = yf.download(
                        yahoo_symbol,
                        start=start_date,
                        end=end_date,
                        interval=interval,
                        progress=False
                    )
                    
                    if not temp_data.empty and len(temp_data) >= 50:
                        data = temp_data
                        logging.info(f"Successfully fetched {symbol} data with {interval} interval: {len(data)} candles")
                        break
                    else:
                        logging.warning(f"Insufficient data for {symbol} with {interval} interval: {len(temp_data) if not temp_data.empty else 0} candles")
                except Exception as e:
                    logging.warning(f"Failed to fetch {symbol} data with {interval} interval: {str(e)}")
                    continue
            
            if data is None or data.empty:
                logging.error(f"Failed to fetch data for {symbol} with any interval")
                return
            
            # Calculate weighted close and smoothed moving average
            data['hlcc4'] = (data['High'] + data['Low'] + data['Close'] + data['Close']) / 4
            data['sma'] = data['hlcc4'].ewm(span=MA_CONFIG['period'], adjust=False).mean().shift(MA_CONFIG['shift'])
            
            # Verify data freshness
            latest_time = data.index[-1]
            if latest_time.tzinfo is not None:
                latest_time = latest_time.tz_localize(None)
            time_diff = datetime.now() - latest_time
            if time_diff.total_seconds() > 3600:  # More than 1 hour old
                logging.warning(f"Data for {symbol} is not recent. Latest data is from {latest_time}")
            
            # Store the data
            self.data[symbol] = data
            logging.info(f"Successfully updated data for {symbol} with {len(data)} candles")
            logging.info(f"Latest price for {symbol}: {data['Close'].iloc[-1]}")
            logging.info(f"Data time range: {data.index[0]} to {data.index[-1]}")
            
        except Exception as e:
            logging.error(f"Error updating data for {symbol}: {str(e)}")
            logging.error(traceback.format_exc())

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