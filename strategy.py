import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import logging
from config import MA_CONFIG, SR_CONFIG, RISK_CONFIG

class StrategyAnalyzer:
    def __init__(self):
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('StrategyAnalyzer')

    def analyze_symbol(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        Analyze a symbol for potential trading signals
        Returns a signal dictionary if a valid setup is found
        """
        try:
            if data is None or len(data) < MA_CONFIG['period'] + MA_CONFIG['shift']:
                return None

            # Get latest price and MA
            latest_price = data['hlcc4'].iloc[-1]
            latest_ma = data['sma'].iloc[-1]
            
            # Check if price is above or below MA
            is_above_ma = latest_price > latest_ma
            
            # Find support and resistance levels
            sr_levels = self._find_support_resistance(data)
            
            # Check for reversion setup
            signal = self._check_reversion_setup(
                data, 
                latest_price, 
                latest_ma, 
                is_above_ma, 
                sr_levels
            )
            
            if signal:
                signal['symbol'] = symbol
                return signal
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error analyzing symbol {symbol}: {e}")
            return None

    def _find_support_resistance(self, data: pd.DataFrame) -> Dict[str, List[float]]:
        """Find support and resistance levels"""
        try:
            prices = data['hlcc4'].values
            levels = {
                'support': [],
                'resistance': []
            }
            
            # Look for local minima and maxima
            for i in range(2, len(prices) - 2):
                # Support level
                if prices[i] < prices[i-1] and prices[i] < prices[i-2] and \
                   prices[i] < prices[i+1] and prices[i] < prices[i+2]:
                    levels['support'].append(prices[i])
                
                # Resistance level
                if prices[i] > prices[i-1] and prices[i] > prices[i-2] and \
                   prices[i] > prices[i+1] and prices[i] > prices[i+2]:
                    levels['resistance'].append(prices[i])
            
            # Filter levels based on touch points
            filtered_levels = {
                'support': self._filter_levels(levels['support'], prices),
                'resistance': self._filter_levels(levels['resistance'], prices)
            }
            
            return filtered_levels
            
        except Exception as e:
            self.logger.error(f"Error finding support/resistance levels: {e}")
            return {'support': [], 'resistance': []}

    def _filter_levels(self, levels: List[float], prices: np.ndarray) -> List[float]:
        """Filter support/resistance levels based on touch points"""
        filtered = []
        for level in levels:
            touches = 0
            for price in prices:
                if abs(price - level) / level <= SR_CONFIG['zone_size_pct']:
                    touches += 1
            if touches >= SR_CONFIG['min_touch_points']:
                filtered.append(level)
        return filtered

    def _check_reversion_setup(
        self, 
        data: pd.DataFrame, 
        latest_price: float, 
        latest_ma: float, 
        is_above_ma: bool,
        sr_levels: Dict[str, List[float]]
    ) -> Optional[Dict]:
        """Check for valid reversion setup"""
        try:
            # Calculate price distance from MA
            ma_distance = abs(latest_price - latest_ma) / latest_ma
            
            # Check if price is near MA
            if ma_distance > 0.002:  # 0.2% threshold
                return None
            
            # Determine direction and check S/R levels
            if is_above_ma:
                # Looking for SELL signals
                for resistance in sr_levels['resistance']:
                    if abs(latest_price - resistance) / latest_price <= SR_CONFIG['zone_size_pct']:
                        return self._create_signal(
                            direction="SELL",
                            entry=latest_price,
                            stop_loss=latest_price * 1.01,  # 1% above entry
                            take_profit=latest_price * 0.985  # 1.5% below entry
                        )
            else:
                # Looking for BUY signals
                for support in sr_levels['support']:
                    if abs(latest_price - support) / latest_price <= SR_CONFIG['zone_size_pct']:
                        return self._create_signal(
                            direction="BUY",
                            entry=latest_price,
                            stop_loss=latest_price * 0.99,  # 1% below entry
                            take_profit=latest_price * 1.015  # 1.5% above entry
                        )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking reversion setup: {e}")
            return None

    def _create_signal(
        self, 
        direction: str, 
        entry: float, 
        stop_loss: float, 
        take_profit: float
    ) -> Dict:
        """Create a trading signal dictionary"""
        return {
            'direction': direction,
            'entry_price': round(entry, 5),
            'stop_loss': round(stop_loss, 5),
            'take_profit': round(take_profit, 5),
            'confidence': 'High' if direction == "BUY" else 'Medium',
            'reason': f"Price reversion at {'support' if direction == 'BUY' else 'resistance'} zone + MA"
        } 