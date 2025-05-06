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
        """Connect to TradingView WebSocket"""
        websocket.enableTrace(True)
        self.ws = websocket.WebSocketApp(
            "wss://data.tradingview.com/socket.io/websocket",
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
            self._process_market_data(data)
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
        self._subscribe_to_symbols()

    def _subscribe_to_symbols(self):
        """Subscribe to market data for configured symbols"""
        for symbol in TRADING_PAIRS:
            subscribe_msg = {
                "m": "chart_add_symbol",
                "p": [f"BINANCE:{symbol}", "1D"]
            }
            self.ws.send(json.dumps(subscribe_msg))

    def _process_market_data(self, data: Dict):
        """Process incoming market data"""
        try:
            if "p" in data and len(data["p"]) > 1:
                symbol = data["p"][0]
                if symbol in TRADING_PAIRS:
                    self._update_symbol_data(symbol, data["p"][1])
        except Exception as e:
            self.logger.error(f"Error processing market data: {e}")

    def _update_symbol_data(self, symbol: str, data: Dict):
        """Update stored data for a symbol"""
        try:
            df = pd.DataFrame(data)
            df.columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            df.set_index('timestamp', inplace=True)
            
            # Calculate weighted close
            df['hlcc4'] = (df['high'] + df['low'] + df['close'] + df['close']) / 4
            
            # Calculate smoothed moving average
            df['sma'] = self._calculate_sma(df['hlcc4'])
            
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