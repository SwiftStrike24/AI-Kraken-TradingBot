import os
import pandas as pd
from datetime import datetime
import logging

from bot.kraken_api import KrakenAPI
from bot.logger import get_logger

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)

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
                'timestamp': datetime.now().replace(tzinfo=None).isoformat() + 'Z',
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

            # Start with cash balance (treat USD-denominated assets as $1.00 per unit)
            cash_assets = {'USDC', 'USD', 'USDT'}
            for cash_asset in cash_assets:
                if cash_asset in balance:
                    cash_amount = balance.pop(cash_asset, 0.0)
                    total_equity += cash_amount
                    logger.info(f"Cash {cash_asset}: ${cash_amount:.2f}")

            if balance: # If there are other assets
                # Filter out forex assets that we don't want to include in equity calculation
                forex_assets = {'CAD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'SEK', 'NOK', 'DKK'}
                crypto_assets = [asset for asset in balance.keys() if asset not in forex_assets]
                
                if crypto_assets:
                    valid_pairs = self.kraken_api.get_valid_usd_pairs_for_assets(crypto_assets)
                    
                    if valid_pairs:
                        prices = self.kraken_api.get_ticker_prices(valid_pairs)
                        
                        for asset, amount in balance.items():
                            if asset in crypto_assets:
                                # Find the corresponding USD pair for this crypto asset
                                asset_pair = self.kraken_api.asset_to_usd_pair_map.get(asset)
                                if asset_pair and asset_pair in prices:
                                    price = prices[asset_pair]['price']
                                    value = amount * price
                                    total_equity += value
                                    logger.info(f"Crypto {asset}: {amount} * ${price:,.2f} = ${value:,.2f}")
                                else:
                                    logger.warning(f"Could not find USD price for crypto asset {asset}. It will not be included in equity calculation.")
                            else:
                                # For forex assets, log but don't include in equity
                                logger.info(f"Forex {asset}: {amount} (excluded from equity calculation)")
                    else:
                        logger.warning("No valid USD pairs found for any crypto assets in balance")
                        
                # Log any remaining forex assets
                forex_in_balance = forex_assets.intersection(balance.keys())
                if forex_in_balance:
                    for forex_asset in forex_in_balance:
                        amount = balance[forex_asset]
                        logger.info(f"Forex {forex_asset}: {amount} (excluded from equity calculation)")
            
            log_entry = {
                'timestamp': datetime.now().replace(tzinfo=None).isoformat() + 'Z',
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
            with open(self.thesis_log_path, 'a', encoding='utf-8') as f:
                timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                f.write(f"## Thesis for {timestamp}\n\n")
                f.write(f"{new_thesis}\n\n")
                f.write("---\n\n")
            logger.info(f"Successfully logged new thesis to {self.thesis_log_path}")
        except IOError as e:
            logger.error(f"Failed to write to thesis log file: {e}")

    def log_rejected_trade(self, trade: dict, reason: str):
        """
        Logs a rejected trade to rejected_trades.csv for auditing purposes.

        Args:
            trade: The trade dictionary that was rejected
            reason: The reason why the trade was rejected
        """
        try:
            rejected_log_path = os.path.join(os.path.dirname(self.trades_log_path), "rejected_trades.csv")
            
            log_entry = {
                'timestamp': datetime.now().replace(tzinfo=None).isoformat() + 'Z',
                'requested_pair': trade.get('pair', 'N/A'),
                'action': trade.get('action', 'N/A'),
                'allocation_percentage': trade.get('allocation_percentage', trade.get('volume', 'N/A')),
                'confidence_score': trade.get('confidence_score', 'N/A'),
                'reasoning': trade.get('reasoning', 'N/A'),
                'rejection_reason': reason
            }
            
            df = pd.DataFrame([log_entry])
            
            # Append to CSV, creating the file with a header if it doesn't exist
            df.to_csv(
                rejected_log_path, 
                mode='a', 
                header=not os.path.exists(rejected_log_path), 
                index=False
            )
            logger.info(f"Successfully logged rejected trade: {log_entry['requested_pair']} - {reason}")

        except Exception as e:
            logger.error(f"Could not log rejected trade: {e}")
