"""
Telegram Alerter for Critical Bot Failures
"""
import os
import telegram
import asyncio
import logging
import requests
from typing import Optional
from bot.logger import get_logger

logger = get_logger(__name__)

# --- CONFIGURATION ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Trade alert toggles
_TOGGLE_TRUTHY = {"1", "true", "yes"}
_env_toggle = os.getenv("TELEGRAM_TRADE_ALERTS")
# Auto-enable alerts when credentials are present unless explicitly disabled by env
if _env_toggle is None:
    TELEGRAM_TRADE_ALERTS = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
else:
    TELEGRAM_TRADE_ALERTS = _env_toggle.lower() in _TOGGLE_TRUTHY
TELEGRAM_ALERTS_INCLUDE_HOLD = os.getenv("TELEGRAM_ALERTS_INCLUDE_HOLD", "0").lower() in _TOGGLE_TRUTHY
TELEGRAM_ALERTS_PARSE_MODE = os.getenv("TELEGRAM_ALERTS_PARSE_MODE", "Markdown")
TELEGRAM_ALERTS_SILENT = os.getenv("TELEGRAM_ALERTS_SILENT", "0").lower() in _TOGGLE_TRUTHY
try:
    TELEGRAM_ALERTS_MAXLEN = int(os.getenv("TELEGRAM_ALERTS_MAXLEN", "2000"))
except Exception:
    TELEGRAM_ALERTS_MAXLEN = 2000


def _http_fallback_send(message: str, silent: bool = False, parse_mode: str = "Markdown") -> bool:
    """HTTP fallback using Telegram Bot API directly. Returns True on 200 OK."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram token or chat ID not set. Cannot send alert.")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_notification": bool(silent),
        }
        if parse_mode:
            payload["parse_mode"] = parse_mode
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            logger.info("Telegram alert sent via HTTP fallback (200 OK)")
            return True
        logger.warning(f"HTTP fallback sendMessage failed: {resp.status_code} {resp.text[:200]}")
        return False
    except Exception as e:
        logger.warning(f"HTTP fallback exception: {e}")
        return False


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
        # Last-chance fallback
        _http_fallback_send(message, silent=False, parse_mode='Markdown')


def notify_dev_of_error(error_message: str):
    """
    Synchronous wrapper to run the async send_telegram_alert function.
    """
    try:
        asyncio.run(send_telegram_alert(error_message))
    except Exception as e:
        logger.error(f"Failed to run asyncio for Telegram alert: {e}")


# --- New: Trade update helpers ---
async def send_trade_update(message: str, silent: Optional[bool] = None, parse_mode: Optional[str] = None):
    """Async sender for trade updates with safe fallbacks."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Trade alert skipped: token or chat ID missing")
        return
    if not TELEGRAM_TRADE_ALERTS:
        logger.info("Trade alerts disabled by env (TELEGRAM_TRADE_ALERTS=0)")
        return

    pmode = parse_mode or TELEGRAM_ALERTS_PARSE_MODE or 'Markdown'
    silent_flag = TELEGRAM_ALERTS_SILENT if silent is None else bool(silent)

    try:
        bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode=pmode,
            disable_notification=silent_flag,
        )
        logger.info("Telegram trade alert sent (Bot API)")
    except Exception as e:
        logger.warning(f"Telegram trade alert via Bot API failed: {e}; attempting HTTP fallback")
        _http_fallback_send(message, silent=silent_flag, parse_mode=pmode)


def notify_trade_update(message: str, silent: Optional[bool] = None, parse_mode: Optional[str] = None):
    """
    Sync wrapper for trade updates. Clamps message length and uses async send with HTTP fallback.
    Respects TELEGRAM_TRADE_ALERTS toggle.
    """
    try:
        # Clamp length to avoid Telegram 400 errors on long messages
        clamped = False
        maxlen = max(200, TELEGRAM_ALERTS_MAXLEN)
        if len(message) > maxlen:
            message = message[: maxlen - 3] + "..."
            clamped = True
        logger.info(
            f"Trade alerts: enabled={TELEGRAM_TRADE_ALERTS} include_hold={TELEGRAM_ALERTS_INCLUDE_HOLD} "
            f"parse_mode={parse_mode or TELEGRAM_ALERTS_PARSE_MODE} silent={TELEGRAM_ALERTS_SILENT if silent is None else bool(silent)}"
        )
        logger.info(f"Trade alert composed: len={len(message)} clamped={'YES' if clamped else 'NO'}")
        asyncio.run(send_trade_update(message, silent=silent, parse_mode=parse_mode))
    except RuntimeError as e:
        # In case of existing event loop (rare in this project), fallback to HTTP
        logger.warning(f"Async loop issue for trade alert ({e}); using HTTP fallback")
        _http_fallback_send(message, silent=bool(silent) if silent is not None else TELEGRAM_ALERTS_SILENT, parse_mode=parse_mode or TELEGRAM_ALERTS_PARSE_MODE)
    except Exception as e:
        logger.warning(f"Trade alert send failed: {e}")


if __name__ == '__main__':
    # Example usage for testing
    print("Sending test alert to Telegram...")
    # You must have .env file with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID set
    test_error = "OpenAI API request failed after 2 retries. Error: 500 Internal Server Error."
    notify_dev_of_error(test_error)
    print("Test alert sent.")
