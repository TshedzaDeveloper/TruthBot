import json
import websocket
import threading
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import logging
from config import TRADING_PAIRS, MA_CONFIG

class MarketDataHandler:
    def __init__(self):
        self.ws = None
        self.data: Dict[str, pd.DataFrame] = {}
        self.connected = False
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('MarketDataHandler')

    def connect(self):
        """Connect to Binance WebSocket"""
        websocket.enableTrace(True)
        
        # Create WebSocket URL with all symbols
        streams = [f"{symbol.lower()}@kline_1d" for symbol in TRADING_PAIRS]
        ws_url = f"wss://stream.binance.com:9443/stream?streams={'/'.join(streams)}"
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
            on_open=self._on_open
        )
        
        # Start WebSocket connection in a separate thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            if 'data' in data:
                self._process_market_data(data['data'])
        except Exception as e:
            self.logger.error(f"Error processing message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        self.logger.error(f"WebSocket error: {error}")
        self.connected = False

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.logger.info("WebSocket connection closed")
        self.connected = False

    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        self.logger.info("WebSocket connection established")
        self.connected = True

    def _process_market_data(self, data: Dict):
        """Process incoming market data"""
        try:
            symbol = data['s']  # Symbol
            kline = data['k']   # Kline/Candlestick data
            
            if symbol in TRADING_PAIRS:
                # Convert Binance data to our format
                candle_data = {
                    'timestamp': kline['t'],
                    'open': float(kline['o']),
                    'high': float(kline['h']),
                    'low': float(kline['l']),
                    'close': float(kline['c']),
                    'volume': float(kline['v'])
                }
                self._update_symbol_data(symbol, candle_data)
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")

    def _update_symbol_data(self, symbol: str, data: Dict):
        """Update stored data for a symbol"""
        try:
            # Create DataFrame from single candle
            df = pd.DataFrame([data])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate weighted close
            df['hlcc4'] = (df['high'] + df['low'] + df['close'] + df['close']) / 4
            
            # Calculate smoothed moving average
            df['sma'] = self._calculate_sma(df['hlcc4'])
            
            # Update or initialize symbol data
            if symbol in self.data:
                self.data[symbol] = pd.concat([self.data[symbol], df])
                # Keep only last 1000 candles
                self.data[symbol] = self.data[symbol].tail(1000)
            else:
                self.data[symbol] = df
                
        except Exception as e:
            self.logger.error(f"Error updating symbol data for {symbol}: {e}")

    def _calculate_sma(self, series: pd.Series) -> pd.Series:
        """Calculate smoothed moving average"""
        return series.ewm(
            span=MA_CONFIG['period'],
            adjust=False
        ).mean().shift(MA_CONFIG['shift'])

    def get_latest_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get latest market data for a symbol"""
        return self.data.get(symbol)

    def get_all_symbols_data(self) -> Dict[str, pd.DataFrame]:
        """Get latest market data for all symbols"""
        return self.data

    def is_connected(self) -> bool:
        """Check if WebSocket is connected"""
        return self.connected

    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close() 