import logging
from bot.kraken_api import KrakenAPI, KrakenAPIError
from bot.logger import get_logger

# Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)

class TradeExecutor:
    """
    Handles the execution of trades based on a plan from the DecisionEngine.
    It uses a safer two-phase (validate, then execute) approach.
    Now supports percentage-based allocation for dynamic portfolio management.
    """
    def __init__(self, kraken_api: KrakenAPI):
        """
        Initializes the TradeExecutor.

        Args:
            kraken_api: An instance of the KrakenAPI client.
        """
        self.kraken_api = kraken_api

    def _consolidate_trades(self, trades: list, portfolio_value: float) -> tuple[list, list]:
        """
        Consolidate multiple BUY/SELL actions on the same pair into a single net action to avoid
        redundant sell-then-buy of the same asset (minimizes fees).

        Returns:
            (consolidated_sell_trades, consolidated_buy_trades)
        """
        net_by_pair: dict[str, dict] = {}
        price_by_pair: dict[str, float] = {}

        for trade in trades:
            try:
                # Determine normalized pair and volume
                if 'allocation_percentage' in trade:
                    converted = self._convert_percentage_to_volume(trade, portfolio_value)
                    pair = self._normalize_pair(converted['pair'])
                    volume = float(converted['volume'])
                    est_price = float(converted.get('estimated_price') or 0.0)
                else:
                    pair = self._normalize_pair(trade['pair'])
                    volume = float(trade['volume'])
                    volume = self._round_volume_for_pair(pair, volume)
                    # Try to fetch a price for approximate USD computations later
                    try:
                        px = self.kraken_api.get_ticker_prices([pair]).get(pair, {}).get('price', 0.0)
                        est_price = float(px or 0.0)
                    except Exception:
                        est_price = 0.0

                action = str(trade.get('action', '')).lower()
                signed = volume if action == 'buy' else (-volume if action == 'sell' else 0.0)
                if pair not in net_by_pair:
                    net_by_pair[pair] = {'net_volume': 0.0}
                net_by_pair[pair]['net_volume'] += signed
                if est_price and est_price > 0:
                    price_by_pair[pair] = est_price
            except Exception:
                # Skip malformed trade entries; downstream validation will handle plan integrity
                continue

        # Build consolidated lists
        sells: list = []
        buys: list = []
        for pair, data in net_by_pair.items():
            net_vol = float(data.get('net_volume') or 0.0)
            if abs(net_vol) <= 0.0:
                continue
            if net_vol < 0:
                sells.append({'pair': pair, 'action': 'sell', 'volume': abs(self._round_volume_for_pair(pair, -net_vol)), 'estimated_price': price_by_pair.get(pair, 0.0)})
            else:
                buys.append({'pair': pair, 'action': 'buy', 'volume': self._round_volume_for_pair(pair, net_vol), 'estimated_price': price_by_pair.get(pair, 0.0)})

        return sells, buys

    def _round_volume_for_pair(self, pair: str, volume: float) -> float:
        """
        Round the volume to meet Kraken's precision rules for the given pair.
        Uses lot_decimals when available and rounds down to avoid exceeding limits.
        """
        try:
            details = self.kraken_api.get_pair_details(pair) or {}
            # Kraken typically provides 'lot_decimals' for volume precision
            lot_decimals = int(details.get('lot_decimals', 8))
            if lot_decimals < 0 or lot_decimals > 10:
                lot_decimals = 8
            # Round down by formatting, avoiding floating issues
            fmt = f"{{:.{lot_decimals}f}}"
            rounded = float(fmt.format(volume))
            # Ensure non-negative
            return max(0.0, rounded)
        except Exception:
            return float(f"{volume:.8f}")

    def _normalize_pair(self, pair: str) -> str:
        """
        Cleans and standardizes a trading pair string.
        Example: "BTC/USD" -> "XBTUSD", "ETHUSD" -> "XETHZUSD"

        Args:
            pair: The trading pair string from the AI's plan.

        Returns:
            A standardized pair string compatible with the Kraken API.
        """
        # Clean the input
        clean_pair = pair.upper().replace('/', '').replace('-', '')
        
        # Handle specific asset mappings
        clean_pair = clean_pair.replace('BTC', 'XBT')
        
        # For pairs ending in USD, try to find the exact Kraken pair name
        if clean_pair.endswith('USD'):
            base_asset = clean_pair[:-3]  # Remove 'USD'
            
            # Check if we have a direct mapping in our asset_to_usd_pair_map
            if hasattr(self.kraken_api, 'asset_to_usd_pair_map'):
                if base_asset in self.kraken_api.asset_to_usd_pair_map:
                    return self.kraken_api.asset_to_usd_pair_map[base_asset]
                
                # Also try with common Kraken prefixes
                for prefix in ['X', 'Z', '']:
                    prefixed_asset = prefix + base_asset if prefix else base_asset
                    if prefixed_asset in self.kraken_api.asset_to_usd_pair_map:
                        return self.kraken_api.asset_to_usd_pair_map[prefixed_asset]
        
        # Fallback to the original logic if no mapping found
        return clean_pair
    
    def _calculate_portfolio_value(self) -> float:
        """
        Calculate total portfolio value using comprehensive Kraken API data.
        
        Returns:
            Total portfolio value in USD
        """
        try:
            # Use comprehensive portfolio context for accurate valuation
            portfolio_data = self.kraken_api.get_comprehensive_portfolio_context()
            
            logger.info(f"Current portfolio value: ${portfolio_data['total_equity']:,.2f}")
            logger.info(f"Cash: ${portfolio_data['cash_balance']:,.2f}, Crypto: ${portfolio_data['crypto_value']:,.2f}")
            
            return portfolio_data['total_equity']
            
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}")
            return 0.0
    
    def _validate_trade_against_holdings(self, trade: dict) -> tuple[bool, str, dict]:
        """
        Validate a trade against current holdings and adjust for precision.
        
        Args:
            trade: Trade dictionary with pair, action, volume
            
        Returns:
            Tuple of (is_valid, message, adjusted_trade)
        """
        try:
            pair = trade.get('pair', '')
            action = trade.get('action', '').lower()
            volume = float(trade.get('volume', 0))
            
            if action != 'sell':
                return True, "Buy orders don't require balance validation", trade
            
            # Extract base asset from pair using official pair details
            pair_details = self.kraken_api.get_pair_details(pair)
            if not pair_details:
                return False, f"Could not get pair details for {pair} to validate holdings", trade
            
            base_asset = pair_details.get('base')
            if not base_asset:
                return False, f"Could not determine base asset for {pair}", trade

            # Clean asset name (remove Kraken's X/Z prefixes)
            clean_base_asset = base_asset[1:] if base_asset.startswith(('X', 'Z')) and len(base_asset) > 1 else base_asset
            
            # Get current portfolio
            portfolio_data = self.kraken_api.get_comprehensive_portfolio_context()
            current_balance = portfolio_data['raw_balances'].get(clean_base_asset, 0.0)
            
            # Check for precision mismatch and adjust if necessary
            if current_balance < volume:
                # Cap to available balance (sell-all semantics if AI overspecifies)
                adjusted_volume = max(0.0, current_balance)
                adjusted_volume = self._round_volume_for_pair(pair, adjusted_volume)
                if adjusted_volume <= 0.0:
                    return False, f"Insufficient {clean_base_asset} balance. Have: {current_balance:.6f}, Need: {volume:.6f}", trade
                logger.warning(f"Capping sell order for {clean_base_asset} from {volume:.8f} to {adjusted_volume:.8f} (available balance).")
                adjusted_trade = trade.copy()
                adjusted_trade['volume'] = adjusted_volume
                return True, f"Capped sell order for {clean_base_asset} to available balance", adjusted_trade
            
            return True, f"Sufficient {clean_base_asset} balance: {current_balance:.6f} >= {volume:.6f}", trade
            
        except Exception as e:
            logger.error(f"Error validating trade against holdings: {e}", exc_info=True)
            return False, f"Validation error: {e}", trade
    
    def _log_portfolio_impact(self, trade: dict, portfolio_data: dict):
        """
        Log the expected impact of a trade on the portfolio.
        
        Args:
            trade: Trade dictionary
            portfolio_data: Current portfolio data
        """
        try:
            pair = trade.get('pair', '')
            action = trade.get('action', '').lower()
            volume = float(trade.get('volume', 0))
            
            # Extract assets
            if '/' in pair:
                base_asset, quote_asset = pair.split('/')
            else:
                base_asset = pair.replace('USD', '')
                quote_asset = 'USD'
            
            # Clean asset names
            for prefix in ['X', 'Z']:
                if base_asset.startswith(prefix) and len(base_asset) > len(prefix):
                    base_asset = base_asset[len(prefix):]
                if quote_asset.startswith(prefix) and len(quote_asset) > len(prefix):
                    quote_asset = quote_asset[len(prefix):]
            
            # Get current allocations
            current_allocations = portfolio_data.get('allocation_percentages', {})
            total_equity = portfolio_data.get('total_equity', 0)
            
            if action == 'buy':
                logger.info(f"📈 BUY Impact: Adding ~${volume * trade.get('estimated_price', 0):,.2f} to {base_asset}")
                logger.info(f"   Current {base_asset} allocation: {current_allocations.get(base_asset, 0):.1f}%")
            elif action == 'sell':
                current_value = portfolio_data['usd_values'].get(base_asset, {}).get('value', 0)
                sell_value = volume * trade.get('estimated_price', 0)
                logger.info(f"📉 SELL Impact: Reducing {base_asset} by ${sell_value:,.2f}")
                logger.info(f"   Current {base_asset} value: ${current_value:,.2f} ({current_allocations.get(base_asset, 0):.1f}%)")
                
        except Exception as e:
            logger.warning(f"Could not log portfolio impact: {e}")
    
    def _convert_percentage_to_volume(self, trade: dict, portfolio_value: float) -> dict:
        """
        Convert percentage allocation to actual volume for trading.
        
        Args:
            trade: Trade dict with allocation_percentage
            portfolio_value: Total portfolio value in USD
            
        Returns:
            Trade dict with volume field added
        """
        try:
            allocation_percentage = trade.get('allocation_percentage', 0.0)
            if allocation_percentage <= 0:
                raise ValueError(f"Invalid allocation percentage: {allocation_percentage}")
            
            # Calculate USD amount to allocate
            usd_amount = portfolio_value * allocation_percentage
            
            # Get current price for the pair
            normalized_pair = self._normalize_pair(trade['pair'])
            logger.info(f"Converting pair '{trade['pair']}' -> '{normalized_pair}'")
            
            prices = self.kraken_api.get_ticker_prices([normalized_pair])
            
            if normalized_pair not in prices:
                # Try to find alternative pair names
                available_pairs = list(self.kraken_api.asset_pairs.keys())
                similar_pairs = [p for p in available_pairs if trade['pair'].replace('/', '').upper() in p]
                logger.error(f"Cannot get price for pair: {normalized_pair}")
                logger.error(f"Original pair: {trade['pair']}")
                logger.error(f"Similar available pairs: {similar_pairs[:5]}")
                raise ValueError(f"Cannot get price for pair: {normalized_pair}")
            
            current_price = prices[normalized_pair]['price']
            
            # Calculate volume (asset amount to buy/sell)
            volume = usd_amount / current_price if current_price > 0 else 0.0
            
            # Round volume to meet Kraken precision constraints
            volume = self._round_volume_for_pair(normalized_pair, volume)

            # Create new trade dict with volume
            new_trade = trade.copy()
            new_trade['volume'] = volume
            new_trade['calculated_usd_amount'] = usd_amount
            
            logger.info(f"Converted {allocation_percentage*100:.1f}% allocation to {volume:.8f} {normalized_pair.replace('USD', '').replace('ZUSD', '')} (${usd_amount:.2f})")
            
            return new_trade
            
        except Exception as e:
            logger.error(f"Error converting percentage to volume for trade {trade}: {e}", exc_info=True)
            raise

    def execute_trades(self, trade_plan: dict) -> list:
        """
        Executes a list of trades using a two-phase (validate, execute) process.
        It now intelligently handles sales first to free up capital before buys.

        Args:
            trade_plan: A dictionary from the DecisionEngine, containing a list of trades.
                        New format: {'trades': [{'pair': 'ETHUSD', 'action': 'buy', 'allocation_percentage': 0.25, 'confidence_score': 0.8}, ...]}
                        Legacy format: {'trades': [{'pair': 'XBT/USD', 'action': 'buy', 'volume': 0.01}, ...]}

        Returns:
            A list of dictionaries, each detailing the outcome of a trade.
        """
        results = []
        all_trades = trade_plan.get('trades', [])

        if not all_trades:
            logger.info("Trade plan is empty. No trades to execute.")
            return results
        # Consolidate opposing actions for the same pair to minimize fee churn
        portfolio_value = self._calculate_portfolio_value()
        sell_trades, buy_trades = self._consolidate_trades(all_trades, portfolio_value)

        # --- Phase 1: Execute Sell Orders First ---
        sell_txids: list[str] = []
        if sell_trades:
            logger.info(f"🔥 Phase 1: Executing {len(sell_trades)} SELL order(s) to free up capital...")
            sell_results = self._process_trades(sell_trades, 'sell')
            results.extend(sell_results)
            # Collect txids for successful sells
            for r in sell_results:
                if r.get('status') == 'success' and r.get('txid'):
                    sell_txids.append(r['txid'])
            if sell_txids:
                logger.info(f"Waiting for {len(sell_txids)} sell order(s) to close before buying...")
                final_status = self.kraken_api.wait_for_orders_closed(sell_txids, timeout_seconds=60, poll_interval=2.0)
                logger.info(f"Sell order final statuses: {final_status}")
            else:
                logger.info("No successful sell txids to wait on.")
        else:
            logger.info("Phase 1: No SELL orders to execute.")

        # Refresh balances after sells regardless of status to reflect any partial/closed orders
        try:
            portfolio_after_sells = self.kraken_api.get_comprehensive_portfolio_context()
            logger.info(f"Post-sell balances: Cash ${portfolio_after_sells.get('cash_balance', 0):,.2f}")
        except Exception:
            logger.warning("Failed to refresh portfolio after sells; proceeding with buy validation using live queries")
        
        # --- Phase 2: Execute Buy Orders ---
        if buy_trades:
            logger.info(f"💰 Phase 2: Executing {len(buy_trades)} BUY order(s) with available capital...")
            buy_results = self._process_trades(buy_trades, 'buy')
            results.extend(buy_results)
        else:
            logger.info("Phase 2: No BUY orders to execute.")
            
        logger.info("✅ Trade execution cycle complete.")
        return results

    def _process_trades(self, trades_to_process: list, trade_type: str) -> list:
        """
        Helper function to process a list of either buy or sell trades.
        
        Args:
            trades_to_process: A list of trades of the same type (buy or sell).
            trade_type: A string, either 'buy' or 'sell'.
            
        Returns:
            A list of dictionaries with the results of the processed trades.
        """
        results = []
        # --- Validation Loop ---
        logger.info(f"Validating {len(trades_to_process)} {trade_type.upper()} trades...")
        validated_trades = []
        
        # Always get the latest portfolio value for this batch
        portfolio_value = self._calculate_portfolio_value()
        portfolio_data = self.kraken_api.get_comprehensive_portfolio_context()
        logger.info(f"🏦 Portfolio Status for {trade_type.upper()}s: Total Value ${portfolio_value:,.2f}, Cash ${portfolio_data['cash_balance']:,.2f}")

        # For BUY validation, reserve cash progressively to avoid oversubscription within the same batch
        reserved_cash = 0.0
        available_cash_live = 0.0
        if trade_type == 'buy':
            try:
                available_cash_live = float(self.kraken_api.get_comprehensive_portfolio_context().get('cash_balance', 0.0))
            except Exception:
                available_cash_live = float(portfolio_data.get('cash_balance', 0.0))
            logger.info(f"Available cash for BUY reservations: ${available_cash_live:,.2f}")

        for trade in trades_to_process:
            try:
                # Check if this is a percentage-based trade or legacy volume-based trade
                if 'allocation_percentage' in trade:
                    converted_trade = self._convert_percentage_to_volume(trade, portfolio_value)
                    pair = self._normalize_pair(converted_trade['pair'])
                    action = converted_trade['action'].lower()
                    volume = float(converted_trade['volume'])
                    # Ensure volume respects pair precision
                    volume = self._round_volume_for_pair(pair, volume)
                    converted_trade['volume'] = volume
                    
                    allocation_pct = trade['allocation_percentage'] * 100
                    confidence = trade.get('confidence_score', 'N/A')
                    reasoning = trade.get('reasoning', 'No reasoning provided')
                    logger.info(f"Validating: {action.capitalize()} {allocation_pct:.1f}% ({volume:.8f}) of {pair} (Confidence: {confidence}) - {reasoning}")
                    
                    # Add estimated price for impact logging
                    try:
                        prices = self.kraken_api.get_ticker_prices([pair])
                        if pair in prices:
                            converted_trade['estimated_price'] = prices[pair]['price']
                    except:
                        converted_trade['estimated_price'] = 0
                    
                    trade_to_validate = converted_trade
                else:
                    # Legacy volume-based trade
                    pair = self._normalize_pair(trade['pair'])
                    action = trade['action'].lower()
                    volume = float(trade['volume'])
                    volume = self._round_volume_for_pair(pair, volume)
                    logger.info(f"Validating: {action.capitalize()} {volume:.8f} of {pair} (Legacy)")
                    trade_to_validate = trade.copy()
                    trade_to_validate['pair'] = pair
                    trade_to_validate['volume'] = volume
                
                # PORTFOLIO VALIDATION: Check holdings for sell orders
                is_valid, validation_msg, adjusted_trade = self._validate_trade_against_holdings(trade_to_validate)
                if not is_valid:
                    logger.warning(f"❌ Portfolio validation failed: {validation_msg}")
                    results.append({'status': 'insufficient_balance', 'trade': trade, 'error': validation_msg})
                    continue
                logger.info(f"✅ Portfolio validation passed: {validation_msg}")
                
                # Use the adjusted trade volume for further validation and execution
                trade_to_validate = adjusted_trade
                volume = float(trade_to_validate['volume'])

                # LOG PORTFOLIO IMPACT
                self._log_portfolio_impact(trade_to_validate, portfolio_data)
                
                # Dynamic preflight against Kraken (validate=true) to catch unsupported/restricted pairs
                is_ok, not_reason = self.kraken_api.is_pair_tradeable(pair, action, volume)
                if not is_ok:
                    logger.warning(f"Skipping {action.upper()} {pair}: not tradeable for this account/region. Reason: {not_reason}")
                    results.append({
                        'pair': pair,
                        'action': action,
                        'volume': float(volume) if volume is not None else None,
                        'status': 'skipped_not_tradeable',
                        'reason': not_reason,
                    })
                    continue

                # PRE-VALIDATION: Check minimum order size and effective cost minimum
                pair_details = self.kraken_api.get_pair_details(pair)
                if pair_details:
                    ordermin = float(pair_details.get('ordermin', 0))
                    costmin = float(pair_details.get('costmin', 0) or 0.0)
                    # Fetch a price once for both impact & effective USD minimum
                    try:
                        prices = self.kraken_api.get_ticker_prices([pair])
                        price = prices.get(pair, {}).get('price', trade_to_validate.get('estimated_price', 0) or 0)
                    except Exception:
                        price = trade_to_validate.get('estimated_price', 0) or 0
                    
                    # Units minimum check (ordermin) with optional uplift for BUY
                    if volume < ordermin:
                        original_pair = trade.get('pair', pair)
                        if trade_type == 'buy':
                            # attempt uplift to meet minimums if within caps and cash
                            required_usd = max(costmin, ordermin * price if price else 0.0)
                            try:
                                live_ctx = self.kraken_api.get_comprehensive_portfolio_context()
                                available_cash = float(live_ctx.get('cash_balance', 0.0))
                            except Exception:
                                available_cash = float(portfolio_data.get('cash_balance', 0.0))
                            effective_available = max(0.0, available_cash - reserved_cash)
                            # Cap reflects cash buffer policy (small portfolios < $50: 95%; otherwise allow up to 99%)
                            cap_pct = 0.95 if portfolio_value < 50 else 0.99
                            cap_usd = cap_pct * portfolio_value
                            if required_usd > 0 and required_usd <= effective_available * 1.001 and required_usd <= cap_usd * 1.001:
                                uplifted_volume = ordermin
                                trade_to_validate['volume'] = uplifted_volume
                                volume = uplifted_volume
                                # reserve delta cash
                                # trade_usd may not be computed yet; compute from uplift
                                trade_usd_uplift = uplifted_volume * price if price else required_usd
                                delta_usd = max(0.0, trade_usd_uplift - reserved_cash)
                                reserved_cash += delta_usd
                                logger.info(f"⬆️ Uplifted BUY for {pair}: set volume to {uplifted_volume:.8f} to satisfy minimum; reserved +${delta_usd:.2f} (total reserved ${reserved_cash:.2f})")
                            else:
                                error_msg = f"Volume {volume:.8f} below minimum order size {ordermin:.8f} for {pair}"
                                user_friendly_msg = f"Volume {volume:.8f} below minimum order size {ordermin:.8f} for {original_pair}"
                                logger.warning(f"⚠️ Skipping trade: {error_msg}")
                                results.append({'status': 'volume_too_small', 'trade': trade, 'error': user_friendly_msg})
                                continue
                        else:
                            error_msg = f"Volume {volume:.8f} below minimum order size {ordermin:.8f} for {pair}"
                            user_friendly_msg = f"Volume {volume:.8f} below minimum order size {ordermin:.8f} for {original_pair}"
                            logger.warning(f"⚠️ Skipping trade: {error_msg}")
                            results.append({'status': 'volume_too_small', 'trade': trade, 'error': user_friendly_msg})
                            continue
                    
                    # MICRO-TRADE GUARD: Block trades smaller than max($25, 5% of equity)
                    trade_usd = volume * price if price else 0.0
                    micro_abs = 25.0
                    micro_pct = 0.05 * portfolio_value
                    micro_threshold = max(micro_abs, micro_pct)
                    if trade_usd < micro_threshold:
                        original_pair = trade.get('pair', pair)
                        logger.warning(
                            f"⚠️ Skipping trade: USD value ${trade_usd:.2f} below micro-trade threshold ${micro_threshold:.2f} for {pair}"
                        )
                        results.append({
                            'status': 'micro_trade_blocked',
                            'trade': trade,
                            'error': f"USD value ${trade_usd:.2f} below micro-trade threshold ${micro_threshold:.2f} for {original_pair}"
                        })
                        continue

                    # Effective USD minimum check (costmin or ordermin * price)
                    effective_min_usd = max(costmin, ordermin * price if price else 0.0)
                    if effective_min_usd > 0 and trade_usd < effective_min_usd:
                        original_pair = trade.get('pair', pair)
                        logger.warning(
                            f"⚠️ Skipping trade: USD value ${trade_usd:.2f} below effective minimum ${effective_min_usd:.2f} (costmin/ordermin*price) for {pair}"
                        )
                        results.append({
                            'status': 'usd_value_too_small',
                            'trade': trade,
                            'error': f"USD value ${trade_usd:.2f} below effective minimum ${effective_min_usd:.2f} for {original_pair}"
                        })
                        continue

                    # CASH AVAILABILITY CHECK for BUY orders (guard against buy-before-sell & oversubscription)
                    if trade_type == 'buy':
                        try:
                            live_ctx = self.kraken_api.get_comprehensive_portfolio_context()
                            available_cash = float(live_ctx.get('cash_balance', 0.0))
                        except Exception:
                            available_cash = float(portfolio_data.get('cash_balance', 0.0))
                        effective_available = max(0.0, available_cash - reserved_cash)
                        if trade_usd > effective_available * 1.001:  # small tolerance
                            original_pair = trade.get('pair', pair)
                            logger.warning(
                                f"⚠️ Skipping trade: insufficient cash. Needed ${trade_usd:.2f}, available ${effective_available:.2f} (after reservations) for {pair}"
                            )
                            results.append({
                                'status': 'insufficient_cash',
                                'trade': trade,
                                'error': f"Insufficient cash. Needed ${trade_usd:.2f}, available ${effective_available:.2f} for {original_pair}"
                            })
                            continue
                        # Reserve cash for this validated BUY
                        reserved_cash += trade_usd
                        logger.info(f"Reserved ${trade_usd:.2f} for {pair}. Reserved total=${reserved_cash:.2f}; Live cash=${available_cash:.2f}")
                    
                    logger.info(f"✅ Volume check passed: {volume:.8f} >= {ordermin:.8f} minimum for {pair}")
                else:
                    logger.warning(f"⚠️ Could not verify minimum order size for {pair} - proceeding")
                
                self.kraken_api.place_order(
                    pair=pair,
                    order_type=action,
                    volume=volume,
                    validate=True
                )
                
                validated_trades.append({'pair': pair, 'action': action, 'volume': volume, 'original_trade': trade})
                logger.info(f"Validation successful for {pair}.")

            except KrakenAPIError as e:
                error_message = f"Validation failed for trade {trade}: {e}"
                logger.error(error_message)
                results.append({'status': 'validation_failed', 'trade': trade, 'error': str(e)})
                continue
            except (KeyError, ValueError) as e:
                error_message = f"Invalid trade format in plan {trade}: {e}"
                logger.error(error_message, exc_info=True)
                results.append({'status': 'invalid_format', 'trade': trade, 'error': str(e)})
                continue

        logger.info(f"Validation Complete: {len(validated_trades)} {trade_type.upper()} trade(s) ready for execution.")

        # --- Execution Loop ---
        if not validated_trades:
            return results
            
        logger.info(f"Executing {len(validated_trades)} {trade_type.upper()} trade(s)...")
        txids: list[str] = []
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
                txids.append(txid)

            except KrakenAPIError as e:
                error_message = f"Live execution failed for trade {trade}: {e}"
                logger.error(error_message)
                results.append({'status': 'execution_failed', 'trade': trade, 'error': str(e)})
                continue
            except Exception as e:
                error_message = f"An unexpected error occurred during execution of {trade}: {e}"
                logger.error(error_message, exc_info=True)
                results.append({'status': 'unexpected_error', 'trade': trade, 'error': str(e)})

        logger.info(f"Execution of {trade_type.upper()} trades complete.")
        return results
