import logging
from bot.kraken_api import KrakenAPI, KrakenAPIError

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TradeExecutor:
    """
    Handles the execution of trades based on a plan from the DecisionEngine.
    It uses a safer two-phase (validate, then execute) approach.
    """
    def __init__(self, kraken_api: KrakenAPI):
        """
        Initializes the TradeExecutor.

        Args:
            kraken_api: An instance of the KrakenAPI client.
        """
        self.kraken_api = kraken_api

    def _normalize_pair(self, pair: str) -> str:
        """
        Cleans and standardizes a trading pair string.
        Example: "BTC/USD" -> "XBTUSD"

        Args:
            pair: The trading pair string from the AI's plan.

        Returns:
            A standardized pair string compatible with the Kraken API.
        """
        return pair.upper().replace('/', '').replace('-', '').replace('BTC', 'XBT')

    def execute_trades(self, trade_plan: dict) -> list:
        """
        Executes a list of trades using a two-phase (validate, execute) process.

        Args:
            trade_plan: A dictionary from the DecisionEngine, containing a list of trades.
                        Example: {'trades': [{'pair': 'XBT/USD', 'action': 'buy', 'volume': 0.01}, ...]}

        Returns:
            A list of dictionaries, each detailing the outcome of a trade.
        """
        results = []
        trades_to_execute = trade_plan.get('trades', [])

        if not trades_to_execute:
            logger.info("Trade plan is empty. No trades to execute.")
            return results

        # --- Phase 1: Validation ---
        logger.info("Starting Phase 1: Validating all trades...")
        validated_trades = []
        for trade in trades_to_execute:
            try:
                pair = self._normalize_pair(trade['pair'])
                action = trade['action'].lower()
                volume = float(trade['volume'])

                logger.info(f"Validating: {action.capitalize()} {volume:.8f} of {pair}")
                
                self.kraken_api.place_order(
                    pair=pair,
                    order_type=action,
                    volume=volume,
                    validate=True
                )
                
                # If validation succeeds, add the cleaned trade to our list
                validated_trades.append({'pair': pair, 'action': action, 'volume': volume})
                logger.info(f"Validation successful for {pair}.")

            except KrakenAPIError as e:
                error_message = f"Validation failed for trade {trade}: {e}"
                logger.error(error_message)
                results.append({'status': 'validation_failed', 'trade': trade, 'error': str(e)})
                # Abort the entire process if any trade fails validation
                logger.error("Aborting execution due to validation failure.")
                return results
            except (KeyError, ValueError) as e:
                error_message = f"Invalid trade format in plan {trade}: {e}"
                logger.error(error_message)
                results.append({'status': 'invalid_format', 'trade': trade, 'error': str(e)})
                logger.error("Aborting execution due to invalid trade format.")
                return results

        logger.info("Phase 1 Complete: All trades validated successfully.")

        # --- Phase 2: Execution ---
        logger.info("Starting Phase 2: Executing all trades...")
        for trade in validated_trades:
            try:
                pair = trade['pair']
                action = trade['action']
                volume = trade['volume']

                logger.info(f"Executing: {action.capitalize()} {volume:.8f} of {pair}")

                response = self.kraken_api.place_order(
                    pair=pair,
                    order_type=action,
                    volume=volume,
                    validate=False # This is a live order
                )
                
                txid = response.get('txid', ['N/A'])[0]
                success_message = f"Successfully executed {action} of {pair}. TxID: {txid}"
                logger.info(success_message)
                results.append({'status': 'success', 'trade': trade, 'txid': txid})

            except KrakenAPIError as e:
                error_message = f"Live execution failed for trade {trade}: {e}"
                logger.error(error_message)
                results.append({'status': 'execution_failed', 'trade': trade, 'error': str(e)})
                # Continue to the next trade even if one fails
            except Exception as e:
                error_message = f"An unexpected error occurred during execution of {trade}: {e}"
                logger.error(error_message)
                results.append({'status': 'unexpected_error', 'trade': trade, 'error': str(e)})

        logger.info("Phase 2 Complete: All trades have been processed.")
        return results
