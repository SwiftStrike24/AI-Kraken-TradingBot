"""
Telegram Alerter for Critical Bot Failures
"""
import os
import telegram
import asyncio
import logging
from bot.logger import get_logger

logger = get_logger(__name__)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram_alert(message: str):
    """
    Sends a formatted message to a specified Telegram chat.

    This function is designed to be called when a critical, unrecoverable
    error occurs in the trading bot, providing instant notification.

    Args:
        message: The error message to send.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram token or chat ID not set. Cannot send alert.")
        return

    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        
        # Format the message for better readability in Telegram
        formatted_message = f"🚨 **Crypto Trading Bot Alert** 🚨\n\n"
        formatted_message += "The bot has encountered a critical error and has been shut down to prevent issues.\n\n"
        formatted_message += "**Error Details:**\n"
        formatted_message += f"```\n{message}\n```"
        
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=formatted_message,
            parse_mode='Markdown'
        )
        logger.info(f"Successfully sent alert to Telegram chat ID {TELEGRAM_CHAT_ID}")

    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")

def notify_dev_of_error(error_message: str):
    """
    Synchronous wrapper to run the async send_telegram_alert function.
    """
    try:
        asyncio.run(send_telegram_alert(error_message))
    except Exception as e:
        logger.error(f"Failed to run asyncio for Telegram alert: {e}")

if __name__ == '__main__':
    # Example usage for testing
    print("Sending test alert to Telegram...")
    # You must have .env file with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID set
    test_error = "OpenAI API request failed after 2 retries. Error: 500 Internal Server Error."
    notify_dev_of_error(test_error)
    print("Test alert sent.")
