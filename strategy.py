import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from config import MA_CONFIG, SR_CONFIG, RISK_CONFIG
import traceback

class StrategyAnalyzer:
    def __init__(self):
        self.setup_logging()
        self.trend_ma_period = 200  # For trend identification
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('StrategyAnalyzer')

    def analyze_symbol(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """Analyze a symbol and generate trading signals."""
        try:
            if data is None or len(data) < max(MA_CONFIG['period'], self.trend_ma_period) + MA_CONFIG['shift']:
                logging.error(f"Insufficient data for {symbol}: {len(data) if data is not None else 0} candles")
                return None
            
            # Calculate trend MA
            data['trend_ma'] = data['Close'].ewm(span=self.trend_ma_period, adjust=False).mean()
            
            # Get the latest prices and moving averages
            latest_price = data['Close'].iloc[-1]
            latest_ma = data['sma'].iloc[-1]
            latest_trend_ma = data['trend_ma'].iloc[-1]
            
            # Determine overall trend
            is_uptrend = latest_price > latest_trend_ma
            is_downtrend = latest_price < latest_trend_ma
            
            logging.info(f"Analyzing {symbol} - Latest price: {latest_price}, MA: {latest_ma}, Trend MA: {latest_trend_ma}")
            logging.info(f"Market is in {'uptrend' if is_uptrend else 'downtrend' if is_downtrend else 'sideways'}")
            
            # Calculate price volatility for dynamic levels
            volatility = data['Close'].pct_change().std() * 100
            logging.info(f"Price volatility: {volatility:.2f}%")
            
            # Adjust support/resistance levels based on volatility
            if symbol in ['GBP=X', 'EUR=X', 'USD=X']:  # Forex pairs
                level_multiplier = max(0.1, min(0.5, volatility / 2))
            else:
                level_multiplier = 0.2
            
            # Find support and resistance levels
            levels = self._find_support_resistance(data, level_multiplier)
            logging.info(f"Found {len(levels)} support/resistance levels")
            
            # Determine if price is near a level
            near_level = False
            level_type = None
            level_price = None
            
            # Increase the zone size to catch more retracements
            zone_size = 0.002  # 0.2% zone for retracements
            
            for level in levels:
                if abs(latest_price - level['price']) / latest_price < zone_size:
                    near_level = True
                    level_type = level['type']
                    level_price = level['price']
                    logging.info(f"Price is near {level_type} level at {level_price}")
                    break
            
            # Generate signal based on trend and retracements
            signal = None
            
            if near_level:
                # Check for bullish retracement in uptrend
                if is_uptrend and level_type == 'support' and latest_price >= latest_ma:
                    signal = {
                        'direction': 'BUY',
                        'entry': latest_price,
                        'stop_loss': min(level_price * (1 - level_multiplier), latest_ma * 0.995),  # Use MA as reference
                        'take_profit': latest_price * (1 + level_multiplier * 2),
                        'confidence': '🔥🔥🔥',
                        'reason': f"Bullish retracement at support in uptrend"
                    }
                    logging.info(f"Generated BUY signal for {symbol} - Retracement in uptrend")
                
                # Check for bearish retracement in downtrend
                elif is_downtrend and level_type == 'resistance' and latest_price <= latest_ma:
                    signal = {
                        'direction': 'SELL',
                        'entry': latest_price,
                        'stop_loss': max(level_price * (1 + level_multiplier), latest_ma * 1.005),  # Use MA as reference
                        'take_profit': latest_price * (1 - level_multiplier * 2),
                        'confidence': '🔥🔥🔥',
                        'reason': f"Bearish retracement at resistance in downtrend"
                    }
                    logging.info(f"Generated SELL signal for {symbol} - Retracement in downtrend")
                
                # Check for trend continuation after retracement
                elif is_uptrend and latest_price > latest_ma and latest_ma > latest_trend_ma:
                    # Price pulled back to MA and bouncing in uptrend
                    signal = {
                        'direction': 'BUY',
                        'entry': latest_price,
                        'stop_loss': latest_ma * 0.995,  # Just below MA
                        'take_profit': latest_price * (1 + level_multiplier * 2),
                        'confidence': '🔥🔥',
                        'reason': f"Trend continuation after pullback to MA"
                    }
                    logging.info(f"Generated BUY signal for {symbol} - Trend continuation")
            
            if signal:
                logging.info(f"Signal details for {symbol}: {signal}")
            else:
                logging.info(f"No valid setup found for {symbol}")
            
            return signal
            
        except Exception as e:
            logging.error(f"Error analyzing {symbol}: {str(e)}")
            logging.error(traceback.format_exc())
            return None

    def _find_support_resistance(self, data: pd.DataFrame, level_multiplier: float) -> List[Dict]:
        """Find support and resistance levels"""
        try:
            prices = data['hlcc4'].values
            levels = []
            
            # Look for local minima and maxima
            for i in range(2, len(prices) - 2):
                # Support level
                if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
                   prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                    levels.append({
                        'type': 'support',
                        'price': prices[i],
                        'multiplier': level_multiplier
                    })
                
                # Resistance level
                if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
                   prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                    levels.append({
                        'type': 'resistance',
                        'price': prices[i],
                        'multiplier': level_multiplier
                    })
            
            # Filter levels based on touch points
            filtered_levels = self._filter_levels(levels, prices)
            
            return filtered_levels
            
        except Exception as e:
            self.logger.error(f"Error finding support/resistance levels: {e}")
            return []

    def _filter_levels(self, levels: List[Dict], prices: np.ndarray) -> List[Dict]:
        """Filter support/resistance levels based on touch points"""
        filtered = []
        for level in levels:
            touches = 0
            for price in prices:
                if abs(price - level['price']) / level['price'] <= SR_CONFIG['zone_size_pct']:
                    touches += 1
            if touches >= SR_CONFIG['min_touch_points']:
                filtered.append(level)
        return filtered 