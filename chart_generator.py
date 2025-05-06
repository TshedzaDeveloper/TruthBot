import mplfinance as mpf
import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging
from datetime import datetime
import os

class ChartGenerator:
    def __init__(self):
        self.setup_logging()
        self.chart_dir = "charts"
        os.makedirs(self.chart_dir, exist_ok=True)
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('ChartGenerator')

    def generate_chart(self, symbol: str, data: pd.DataFrame, signal: Optional[Dict] = None) -> str:
        """Generate a chart with analysis and save it"""
        try:
            # Prepare the data
            df = data.copy()
            df.index = pd.to_datetime(df.index)
            
            # Calculate additional indicators
            df['SMA'] = df['Close'].rolling(window=50).mean()
            
            # Create the chart
            fig, axes = mpf.plot(
                df,
                type='candle',
                style='charles',
                title=f'\n{symbol} Analysis',
                volume=True,
                figsize=(12, 8),
                returnfig=True,
                panel_ratios=(3, 1),
                addplot=[
                    mpf.make_addplot(df['SMA'], color='blue', width=0.7, panel=0),
                ],
                savefig=dict(
                    fname=os.path.join(self.chart_dir, f"{symbol.replace('=', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"),
                    dpi=300,
                    bbox_inches='tight'
                )
            )
            
            # Add signal information if available
            if signal:
                ax = axes[0]
                if signal['direction'] == 'BUY':
                    ax.axhline(y=signal['entry_price'], color='g', linestyle='--', alpha=0.5)
                    ax.axhline(y=signal['stop_loss'], color='r', linestyle='--', alpha=0.5)
                    ax.axhline(y=signal['take_profit'], color='g', linestyle='--', alpha=0.5)
                else:
                    ax.axhline(y=signal['entry_price'], color='r', linestyle='--', alpha=0.5)
                    ax.axhline(y=signal['stop_loss'], color='g', linestyle='--', alpha=0.5)
                    ax.axhline(y=signal['take_profit'], color='r', linestyle='--', alpha=0.5)
                
                # Add annotations
                ax.annotate(
                    f"Entry: {signal['entry_price']}",
                    xy=(df.index[-1], signal['entry_price']),
                    xytext=(10, 10),
                    textcoords='offset points',
                    color='blue'
                )
                ax.annotate(
                    f"SL: {signal['stop_loss']}",
                    xy=(df.index[-1], signal['stop_loss']),
                    xytext=(10, -10),
                    textcoords='offset points',
                    color='red'
                )
                ax.annotate(
                    f"TP: {signal['take_profit']}",
                    xy=(df.index[-1], signal['take_profit']),
                    xytext=(10, 10),
                    textcoords='offset points',
                    color='green'
                )
            
            # Save the chart
            fig.savefig(
                os.path.join(self.chart_dir, f"{symbol.replace('=', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"),
                dpi=300,
                bbox_inches='tight'
            )
            
            # Return the path to the saved chart
            return os.path.join(self.chart_dir, f"{symbol.replace('=', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
        except Exception as e:
            self.logger.error(f"Error generating chart for {symbol}: {e}")
            return None 