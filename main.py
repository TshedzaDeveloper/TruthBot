import asyncio
import logging
import schedule
import time
from datetime import datetime
from market_data import MarketDataHandler
from strategy import StrategyAnalyzer
from telegram_bot import TelegramBot
from config import TRADING_PAIRS, SCHEDULE_CONFIG

class TruthBot:
    def __init__(self):
        self.setup_logging()
        self.market_data = MarketDataHandler()
        self.strategy = StrategyAnalyzer()
        self.telegram_bot = TelegramBot()
        self.last_analysis_time = {}
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TruthBot')

    async def analyze_markets(self):
        """Analyze all trading pairs and send signals if found"""
        try:
            # Check if it's Sunday
            if datetime.now().strftime('%A') in SCHEDULE_CONFIG['exclude_days']:
                self.logger.info("Skipping analysis on Sunday")
                return

            # Get market data for all symbols
            market_data = self.market_data.get_all_symbols_data()
            
            for symbol in TRADING_PAIRS:
                # Check if enough time has passed since last analysis
                current_time = time.time()
                if symbol in self.last_analysis_time:
                    time_since_last = current_time - self.last_analysis_time[symbol]
                    if time_since_last < SCHEDULE_CONFIG['interval_minutes'] * 60:
                        continue
                
                # Get data for symbol
                data = market_data.get(symbol)
                if data is None:
                    self.logger.warning(f"No data available for {symbol}")
                    continue
                
                # Analyze symbol
                signal = self.strategy.analyze_symbol(symbol, data)
                
                if signal:
                    # Send signal via Telegram
                    await self.telegram_bot.send_signal(signal)
                    self.logger.info(f"Signal sent for {symbol}")
                
                # Update last analysis time
                self.last_analysis_time[symbol] = current_time
                
        except Exception as e:
            self.logger.error(f"Error in market analysis: {e}")

    async def run(self):
        """Run the bot"""
        try:
            # Connect to market data
            self.market_data.connect()
            
            # Wait for market data connection
            while not self.market_data.is_connected():
                self.logger.info("Waiting for market data connection...")
                await asyncio.sleep(1)
            
            self.logger.info("Market data connected successfully")
            
            # Schedule market analysis
            schedule.every(SCHEDULE_CONFIG['interval_minutes']).minutes.do(
                lambda: asyncio.create_task(self.analyze_markets())
            )
            
            # Run initial analysis
            await self.analyze_markets()
            
            # Start Telegram bot
            self.telegram_bot.run()
            
            # Keep the bot running
            while True:
                schedule.run_pending()
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        try:
            self.market_data.close()
            self.telegram_bot.stop()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

if __name__ == "__main__":
    # Create and run the bot
    bot = TruthBot()
    
    try:
        # Run the bot
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
    except Exception as e:
        logging.error(f"Bot stopped due to error: {e}")
    finally:
        bot.cleanup() 