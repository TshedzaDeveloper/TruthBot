from typing import Dict, List
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Trading Pairs
TRADING_PAIRS = [
    "NDX",  # NAS100 (Nasdaq-100)
    "GC=F",  # Gold
    "GBPUSD=X"  # GBP/USD
]

# Moving Average Configuration
MA_CONFIG = {
    "period": 50,
    "shift": 115,
    "method": "smoothed",
    "apply_to": "hlcc4"  # (High + Low + Close + Close) / 4
}

# Risk Management
RISK_CONFIG = {
    "default_sl_tp_ratio": 1.5,  # 1:1.5 ratio
    "min_confidence_level": 0.7,  # Minimum confidence level to send signals
    "max_daily_signals": 5,  # Maximum signals per pair per day
    "min_time_between_signals": 3600  # Minimum time between signals in seconds
}

# Support & Resistance Configuration
SR_CONFIG = {
    "lookback_periods": 100,  # Number of periods to look back for S/R levels
    "min_touch_points": 3,  # Minimum number of touches to consider a level valid
    "zone_size_pct": 0.002  # Size of the zone as percentage of price
}

# Analysis Schedule
SCHEDULE_CONFIG = {
    "interval_minutes": 15,
    "exclude_days": ["Sunday"]
}

# Signal Storage
SIGNAL_STORAGE = {
    "max_stored_signals": 100,  # Maximum number of signals to store
    "storage_file": "signals.json"
}

# Logging Configuration
LOGGING_CONFIG = {
    "log_file": "truth_bot.log",
    "log_level": "INFO",
    "max_log_size": 10485760,  # 10MB
    "backup_count": 5
} 