# Truth Bot - Market Analysis Telegram Bot

A Python-based Telegram bot that analyzes real-time market data for NAS100, XAUUSD, and GBPUSD using a sophisticated moving average and support/resistance strategy.

## Features

- Real-time market analysis for NAS100, XAUUSD, and GBPUSD
- Smoothed Moving Average strategy with reversion rules
- Automatic support and resistance detection
- Telegram notifications for trading signals
- Configurable risk management parameters
- Scheduled analysis every 15 minutes (excluding Sundays)

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd TruthBot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create a `.env` file in the root directory with the following variables:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

4. **Run the bot**
   ```bash
   python main.py
   ```

## Configuration

The bot can be configured through the `config.py` file:
- Moving Average parameters
- Risk management settings
- Trading pairs
- Analysis schedule

## Deployment

The bot can be deployed on:
- PythonAnywhere
- Render
- Any VPS with Python 3.8+

## Market Data Integration

The bot currently uses TradingView's WebSocket API for real-time market data. To use a different data provider:
1. Modify the `market_data.py` file
2. Update the data fetching methods
3. Ensure the data format matches the expected structure

## License

MIT License 