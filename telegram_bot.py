import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
import json
from datetime import datetime
from typing import Dict, List, Optional
from market_data import MarketDataHandler
from strategy import StrategyAnalyzer
from chart_generator import ChartGenerator
import asyncio

class TelegramBot:
    def __init__(self):
        self.setup_logging()
        self.application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
        self.stored_signals: List[Dict] = []
        self.market_data = MarketDataHandler()
        self.strategy = StrategyAnalyzer()
        self.chart_generator = ChartGenerator()
        self.is_running = False
        
        # Connect to market data
        if not self.market_data.connect():
            self.logger.error("Failed to connect to market data")
            raise Exception("Failed to connect to market data")

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('TelegramBot')

    def setup_handlers(self):
        """Setup command handlers"""
        self.logger.info("Setting up command handlers")
        try:
            # Add command handlers
            self.application.add_handler(CommandHandler("start", self.start_command))
            self.application.add_handler(CommandHandler("help", self.help_command))
            self.application.add_handler(CommandHandler("status", self.status_command))
            self.application.add_handler(CommandHandler("signal", self.signal_command))
            
            # Log successful handler setup
            self.logger.info("Command handlers setup completed")
            
        except Exception as e:
            self.logger.error(f"Error setting up command handlers: {e}")
            raise

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        await update.message.reply_text(
            "Welcome to Truth Bot! 🤖\n"
            "I analyze market data and send trading signals.\n"
            "Use /help to see available commands."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "Available commands:\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/status - Check bot status\n"
            "/signal - Generate trading signal\n\n"
            "The bot automatically sends trading signals when valid setups are found."
        )
        await update.message.reply_text(help_text)

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        status_text = (
            "🤖 Truth Bot Status\n\n"
            "✅ Bot is running\n"
            "📊 Monitoring:\n"
            "   • NAS100 (^NDX)\n"
            "   • Gold (GC=F)\n"
            "   • GBP/USD (GBP=X)\n"
            "⏰ Analysis interval: Every 15 minutes\n"
            f"📝 Last signal: {self._get_last_signal_time()}"
        )
        await update.message.reply_text(status_text)

    async def signal_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /signal command"""
        try:
            self.logger.info("=== Signal Command Debug ===")
            self.logger.info(f"Update: {update}")
            self.logger.info(f"Context args: {context.args}")
            
            # Get the symbol from command arguments or use default
            symbol = context.args[0] if context.args else "GC=F"
            self.logger.info(f"Received signal request for symbol: {symbol}")
            
            # Map common symbol aliases to their yfinance equivalents
            symbol_map = {
                # Gold symbols
                "XAUUSD": "GC=F",
                "XAUUSD=X": "GC=F",
                "GOLD": "GC=F",
                # NASDAQ-100 symbols
                "NAS100": "^NDX",
                "NDX": "^NDX",
                "QQQ": "QQQ",
                "NASDAQ100": "^NDX",
                "NASDAQ-100": "^NDX",
                # GBP/USD symbols
                "GBPUSD": "GBP=X",
                "GBPUSD=X": "GBP=X"
            }
            
            # Convert to yfinance symbol if needed
            original_symbol = symbol
            symbol = symbol_map.get(symbol.upper(), symbol)
            self.logger.info(f"Mapped {original_symbol} to {symbol}")
            
            # Get market data
            self.logger.info(f"Fetching market data for {symbol}")
            self.logger.info(f"Market data handler connected: {self.market_data.is_connected()}")
            data = self.market_data.get_latest_data(symbol)
            
            if data is None:
                self.logger.error(f"No data available for {symbol}")
                await update.message.reply_text(
                    f"❌ No data available for {symbol}\n"
                    "Available symbols:\n"
                    "• GC=F (Gold)\n"
                    "• ^NDX (NASDAQ-100 Index)\n"
                    "• QQQ (NASDAQ-100 ETF)\n"
                    "• GBP=X (GBP/USD)"
                )
                return
            
            self.logger.info(f"Successfully retrieved data for {symbol} with {len(data)} candles")
            self.logger.info(f"Data columns: {data.columns.tolist()}")
            self.logger.info(f"Latest price: {data['Close'].iloc[-1]}")
            
            # Generate signal
            self.logger.info(f"Generating signal for {symbol}")
            signal = self.strategy.analyze_symbol(symbol, data)
            
            if signal:
                # Generate chart
                chart_path = self.chart_generator.generate_chart(symbol, data, signal)
                
                # Format and send signal
                self.logger.info(f"Signal generated for {symbol}: {signal}")
                message = self._format_signal_message(signal)
                
                # Send chart first if available
                if chart_path:
                    await update.message.reply_photo(
                        photo=open(chart_path, 'rb'),
                        caption=message,
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(message, parse_mode='HTML')
                
                # Store the signal
                await self.send_signal(signal)
            else:
                self.logger.info(f"No valid setup found for {symbol}")
                # Generate chart without signal
                chart_path = self.chart_generator.generate_chart(symbol, data)
                if chart_path:
                    await update.message.reply_photo(
                        photo=open(chart_path, 'rb'),
                        caption=f"❌ No valid setup found for {symbol}"
                    )
                else:
                    await update.message.reply_text(f"❌ No valid setup found for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error generating signal: {str(e)}", exc_info=True)
            await update.message.reply_text("❌ Error generating signal. Please try again.")

    def _get_last_signal_time(self) -> str:
        """Get the time of the last signal"""
        if not self.stored_signals:
            return "No signals yet"
        last_signal = self.stored_signals[-1]
        return last_signal.get('timestamp', 'Unknown')

    async def send_signal(self, signal: Dict):
        """Send a trading signal to the configured chat"""
        try:
            # Format the signal message
            message = self._format_signal_message(signal)
            
            # Send the message
            await self.application.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='HTML'
            )
            
            # Store the signal
            signal['timestamp'] = datetime.now().isoformat()
            self.stored_signals.append(signal)
            
            # Keep only the last 100 signals
            if len(self.stored_signals) > 100:
                self.stored_signals = self.stored_signals[-100:]
                
            self.logger.info(f"Signal sent for {signal['symbol']}")
            
        except Exception as e:
            self.logger.error(f"Error sending signal: {e}")

    def _format_signal_message(self, signal: Dict) -> str:
        """Format the signal message with HTML"""
        emoji = "🟢" if signal['direction'] == "BUY" else "🔴"
        confidence_emoji = "🔥" * (3 if signal['confidence'] == 'High' else 2)
        
        return (
            f"{emoji} <b>TRUTH BOT SIGNAL</b> {emoji}\n\n"
            f"<b>Symbol:</b> {signal['symbol']}\n"
            f"<b>Direction:</b> {signal['direction']}\n"
            f"<b>Entry Price:</b> {signal['entry_price']}\n"
            f"<b>Stop Loss:</b> {signal['stop_loss']}\n"
            f"<b>Take Profit:</b> {signal['take_profit']}\n"
            f"<b>Confidence:</b> {confidence_emoji}\n"
            f"<b>Reason:</b> {signal['reason']}\n\n"
            f"⚠️ <i>Trade at your own risk</i>"
        )

    async def start(self):
        """Start the bot"""
        if self.is_running:
            self.logger.warning("Bot is already running")
            return
            
        try:
            # Initialize market data connection
            if not self.market_data.connect():
                self.logger.error("Failed to connect to market data")
                return
                
            # Initialize application
            await self.application.initialize()
            await self.application.start()
            
            # Start polling with clean start and specific updates
            await self.application.updater.start_polling(
                drop_pending_updates=True,
                allowed_updates=["message"]
            )
            
            self.is_running = True
            self.logger.info("Telegram bot started successfully")
            
        except Exception as e:
            self.logger.error(f"Error starting Telegram bot: {e}")
            self.is_running = False
            raise

    async def stop(self):
        """Stop the bot"""
        if not self.is_running:
            return
            
        try:
            # Stop polling
            if self.application.updater.running:
                await self.application.updater.stop()
            
            # Stop application
            if self.application.running:
                await self.application.stop()
                await self.application.shutdown()
            
            self.is_running = False
            self.logger.info("Telegram bot stopped successfully")
            
        except Exception as e:
            self.logger.error(f"Error stopping Telegram bot: {e}")
            raise 