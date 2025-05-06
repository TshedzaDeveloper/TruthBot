import asyncio
import logging
import time
from datetime import datetime
from market_data import MarketDataHandler
from strategy import StrategyAnalyzer
from telegram_bot import TelegramBot
from config import TRADING_PAIRS, SCHEDULE_CONFIG
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import signal
import sys

class TruthBot:
    def __init__(self):
        self.setup_logging()
        self.market_data = MarketDataHandler()
        self.strategy = StrategyAnalyzer()
        self.telegram_bot = TelegramBot()
        self.running = False
        self.scheduler = AsyncIOScheduler()
        
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
                
        except Exception as e:
            self.logger.error(f"Error in market analysis: {e}")

    def signal_handler(self, signum, frame):
        """Handle system signals"""
        self.logger.info(f"Received signal {signum}")
        self.running = False

    async def run(self):
        """Run the bot"""
        try:
            self.running = True
            
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            # Connect to market data
            if not self.market_data.connect():
                self.logger.error("Failed to connect to market data")
                return
            
            self.logger.info("Market data connected successfully")
            
            # Start Telegram bot
            try:
                await self.telegram_bot.start()
                self.logger.info("Telegram bot started successfully")
            except Exception as e:
                self.logger.error(f"Failed to start Telegram bot: {e}")
                return
            
            # Configure scheduler
            self.scheduler.add_job(
                self.analyze_markets,
                CronTrigger(
                    minute='*/15',  # Every 15 minutes
                    day_of_week='mon-sat'  # Monday to Saturday
                ),
                id='market_analysis',
                replace_existing=True
            )
            
            # Start scheduler
            self.scheduler.start()
            self.logger.info("Scheduler started successfully")
            
            # Run initial analysis
            await self.analyze_markets()
            
            # Keep the bot running
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"Error running bot: {e}")
        finally:
            await self.cleanup()

    async def cleanup(self):
        """Cleanup resources"""
        try:
            self.running = False
            
            # Stop scheduler
            if self.scheduler.running:
                self.scheduler.shutdown()
                self.logger.info("Scheduler stopped")
            
            # Close market data connection
            self.market_data.close()
            self.logger.info("Market data connection closed")
            
            # Stop Telegram bot
            try:
                await self.telegram_bot.stop()
                self.logger.info("Telegram bot stopped")
            except Exception as e:
                self.logger.error(f"Error stopping Telegram bot: {e}")
            
            self.logger.info("Bot cleanup completed")
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
    sys.exit(0) 