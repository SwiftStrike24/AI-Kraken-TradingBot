import os
import pandas as pd
from datetime import datetime, timezone
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
        self.pnl_log_path = os.path.join(logs_dir, "pnl.csv")
        
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
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
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
            # Use the comprehensive portfolio context as the single source of truth
            portfolio_ctx = self.kraken_api.get_comprehensive_portfolio_context()

            total_equity = float(round(portfolio_ctx.get('total_equity', 0.0), 2))
            cash_balance = float(round(portfolio_ctx.get('cash_balance', 0.0), 2))
            crypto_value = float(round(portfolio_ctx.get('crypto_value', 0.0), 2))

            # Diagnostics to validate correctness against previous implementation issues
            logger.info(f"Cash (USD/USDC/USDT): ${cash_balance:,.2f}")
            logger.info(f"Crypto assets total value: ${crypto_value:,.2f}")

            usd_values = portfolio_ctx.get('usd_values', {}) or {}
            if usd_values:
                # Show top 3 holdings by USD value for quick verification
                try:
                    top_holdings = sorted(
                        [(a, d) for a, d in usd_values.items() if a != 'USD'],
                        key=lambda x: x[1].get('value', 0.0),
                        reverse=True
                    )[:3]
                    for asset, data in top_holdings:
                        amount = data.get('amount', 0.0)
                        price = data.get('price', 0.0)
                        value = data.get('value', 0.0)
                        logger.info(f"Holding {asset}: {amount:.6f} @ ${price:,.2f} = ${value:,.2f}")
                except Exception:
                    # Best-effort diagnostics
                    pass

            # Final log entry uses the unified total
            log_entry = {
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
                'total_equity_usd': total_equity
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
                timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
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
                'timestamp': datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
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

    # New: daily P&L metrics based on equity curve
    def log_daily_pnl(self):
        try:
            if not os.path.exists(self.equity_log_path):
                logger.warning("P&L: equity.csv missing; skipping daily pnl logging")
                return
            eq = pd.read_csv(self.equity_log_path, names=['timestamp', 'total_equity_usd']) if not self._has_header(self.equity_log_path) else pd.read_csv(self.equity_log_path)
            eq['timestamp'] = pd.to_datetime(eq['timestamp'], errors='coerce', utc=True)
            eq['total_equity_usd'] = pd.to_numeric(eq['total_equity_usd'], errors='coerce')
            eq = eq.dropna(subset=['timestamp', 'total_equity_usd'])
            if eq.empty:
                logger.warning("P&L: equity.csv has no valid rows")
                return
            eq['date'] = eq['timestamp'].dt.date
            # Take last value per day
            daily = eq.sort_values('timestamp').groupby('date').tail(1).copy()
            daily['daily_return_pct'] = daily['total_equity_usd'].pct_change().fillna(0.0) * 100.0
            # Rolling vol (percentage points) and simple Sharpe (assuming 0 RF), annualization ignored for simplicity in micro accounts
            daily['rolling_vol_7d'] = daily['daily_return_pct'].rolling(window=7, min_periods=2).std().fillna(0.0)
            daily['rolling_sharpe_30d'] = (
                daily['daily_return_pct'].rolling(window=30, min_periods=2).mean().fillna(0.0) /
                daily['daily_return_pct'].rolling(window=30, min_periods=2).std().replace(0, pd.NA)
            ).fillna(0.0)
            # Drawdown
            daily['peak'] = daily['total_equity_usd'].cummax()
            daily['drawdown_pct'] = (daily['total_equity_usd'] / daily['peak'] - 1.0) * 100.0
            daily['max_drawdown_pct'] = daily['drawdown_pct'].cummin()
            # Append/overwrite pnl.csv with latest full daily set
            daily[['date','timestamp','total_equity_usd','daily_return_pct','rolling_vol_7d','rolling_sharpe_30d','drawdown_pct','max_drawdown_pct']].to_csv(
                self.pnl_log_path,
                index=False
            )
            logger.info(f"P&L: wrote {len(daily)} daily rows to {self.pnl_log_path}")
        except Exception as e:
            logger.error(f"P&L: failed to compute/write daily pnl: {e}")

    def get_pnl_summary(self, days: int = 3) -> str:
        try:
            if not os.path.exists(self.pnl_log_path):
                return "P&L summary unavailable (pnl.csv missing)."
            df = pd.read_csv(self.pnl_log_path)
            if df.empty:
                return "P&L summary unavailable (no daily rows)."
            df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
            df = df.dropna(subset=['timestamp'])
            recent = df.sort_values('timestamp').tail(days)
            if recent.empty:
                return "P&L summary unavailable (insufficient recent rows)."
            ret = recent['daily_return_pct'].sum()
            dd = float(recent['drawdown_pct'].min()) if 'drawdown_pct' in recent.columns else 0.0
            sharpe = float(recent['rolling_sharpe_30d'].iloc[-1]) if 'rolling_sharpe_30d' in recent.columns else 0.0
            return f"Last {len(recent)} days total return {ret:+.2f}pp, min drawdown {dd:.2f}pp, 30d Sharpe {sharpe:.2f}."
        except Exception as e:
            logger.warning(f"P&L summary failed: {e}")
            return "P&L summary unavailable (error)."

    def _has_header(self, path: str) -> bool:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                first = f.readline().lower()
                return ("timestamp" in first and "," in first)
        except Exception:
            return False
