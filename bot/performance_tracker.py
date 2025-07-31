import os
import pandas as pd
from datetime import datetime
import logging

from bot.kraken_api import KrakenAPI

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PerformanceTracker:
    """
    Logs all critical data for performance analysis and debugging,
    including trades, daily equity, and the AI's strategic thesis.
    """
    def __init__(self, kraken_api: KrakenAPI, logs_dir: str = "logs"):
        """
        Initializes the PerformanceTracker.

        Args:
            kraken_api: An instance of the KrakenAPI client.
            logs_dir: The directory where log files will be stored.
        """
        self.kraken_api = kraken_api
        
        self.equity_log_path = os.path.join(logs_dir, "equity.csv")
        self.trades_log_path = os.path.join(logs_dir, "trades.csv")
        self.thesis_log_path = os.path.join(logs_dir, "thesis_log.md")
        
        # Ensure the logs directory exists
        os.makedirs(logs_dir, exist_ok=True)

    def log_trade(self, trade_result: dict):
        """
        Logs a single successful trade to trades.csv.

        Args:
            trade_result: A dictionary representing a successful trade from the TradeExecutor.
                          Example: {'status': 'success', 'trade': {'pair': 'XBTUSD', ...}, 'txid': '...'}
        """
        if trade_result.get('status') != 'success':
            return # Only log successful trades

        try:
            trade_data = trade_result['trade']
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'pair': trade_data['pair'],
                'action': trade_data['action'],
                'volume': trade_data['volume'],
                'txid': trade_result.get('txid', 'N/A')
            }
            
            df = pd.DataFrame([log_entry])
            
            # Append to CSV, creating the file with a header if it doesn't exist
            df.to_csv(
                self.trades_log_path, 
                mode='a', 
                header=not os.path.exists(self.trades_log_path), 
                index=False
            )
            logger.info(f"Successfully logged trade: {log_entry}")

        except (KeyError, TypeError) as e:
            logger.error(f"Could not log trade due to invalid format: {trade_result}. Error: {e}")

    def log_equity(self):
        """
        Calculates the total portfolio value in USD and logs it to equity.csv.
        """
        logger.info("Calculating and logging total portfolio equity...")
        try:
            balance = self.kraken_api.get_account_balance()
            total_equity = 0.0

            # Start with cash balance
            total_equity += balance.pop('USDC', 0.0)

            if balance: # If there are crypto assets
                # Prepare pairs for price fetching
                pairs_to_fetch = [f"{asset}USD" for asset in balance.keys()]
                pairs_to_fetch = [p.replace("BTCUSD", "XBTUSD") for p in pairs_to_fetch]
                
                prices = self.kraken_api.get_ticker_prices(pairs_to_fetch)
                
                for asset, amount in balance.items():
                    # Find the corresponding Kraken pair name (e.g., 'XBT' -> 'XXBTZUSD')
                    kraken_pair = next((p for p in prices if asset in p and 'USD' in p), None)
                    if kraken_pair and kraken_pair in prices:
                        price = prices[kraken_pair]['price']
                        value = amount * price
                        total_equity += value
                        logger.info(f"Asset {asset}: {amount} * ${price:,.2f} = ${value:,.2f}")
                    else:
                        logger.warning(f"Could not find price for {asset}. It will not be included in equity calculation.")
            
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_equity_usd': round(total_equity, 2)
            }
            
            df = pd.DataFrame([log_entry])
            df.to_csv(
                self.equity_log_path, 
                mode='a', 
                header=not os.path.exists(self.equity_log_path), 
                index=False
            )
            logger.info(f"Successfully logged equity: ${total_equity:,.2f}")

        except Exception as e:
            logger.error(f"Failed to log equity: {e}")

    def log_thesis(self, new_thesis: str):
        """
        Appends the AI's new strategic thesis to thesis_log.md.

        Args:
            new_thesis: The thesis string from the AI's response.
        """
        try:
            with open(self.thesis_log_path, 'a') as f:
                timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                f.write(f"## Thesis for {timestamp}\n\n")
                f.write(f"{new_thesis}\n\n")
                f.write("---\n\n")
            logger.info(f"Successfully logged new thesis to {self.thesis_log_path}")
        except IOError as e:
            logger.error(f"Failed to write to thesis log file: {e}")
