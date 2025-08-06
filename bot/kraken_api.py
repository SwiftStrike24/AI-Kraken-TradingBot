import os
import time
import base64
import hashlib
import hmac
import requests
import urllib.parse
import logging

logger = logging.getLogger(__name__)

class KrakenAPIError(Exception):
    """Custom exception for Kraken API errors."""
    pass

class KrakenAPI:
    """
    A wrapper for the Kraken REST API.
    """
    def __init__(self):
        """Initializes the API client."""
        self.api_key = os.getenv("KRAKEN_API_KEY")
        self.api_secret = os.getenv("KRAKEN_API_SECRET")
        self.base_url = "https://api.kraken.com"

        if not self.api_key or not self.api_secret:
            raise ValueError("KRAKEN_API_KEY and KRAKEN_API_SECRET must be set in the .env file.")
        
        # Fetch and cache all available asset pairs
        self.asset_pairs = self._fetch_asset_pairs()
        self.asset_to_usd_pair_map = self._build_asset_to_usd_map()

    def _get_kraken_signature(self, url_path, data):
        """
        Generates the API-Sign header for private endpoints.
        """
        postdata = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + postdata).encode()
        message = url_path.encode() + hashlib.sha256(encoded).digest()

        mac = hmac.new(base64.b64decode(self.api_secret), message, hashlib.sha512)
        sigdigest = base64.b64encode(mac.digest())
        return sigdigest.decode()

    def _query_api(self, method_type, url_path, data=None, max_retries=3):
        """
        Centralized method to handle all API requests.
        """
        if data is None:
            data = {}

        full_url = self.base_url + url_path
        headers = {}
        
        session = requests.Session()

        if method_type == 'private':
            data['nonce'] = str(int(time.time() * 1000))
            headers['API-Key'] = self.api_key
            headers['API-Sign'] = self._get_kraken_signature(url_path, data)

        for attempt in range(max_retries):
            try:
                if method_type == 'private':
                    response = session.post(full_url, headers=headers, data=data, timeout=20)
                else: # public
                    response = session.get(full_url, params=data, timeout=20)

                response.raise_for_status()
                payload = response.json()

                if payload.get('error'):
                    raise KrakenAPIError(f"API Error: {payload['error']}")

                return payload.get('result', {})

            except requests.exceptions.RequestException as e:
                # Need to check response text for rate limit error string from Kraken
                response_text = response.text if 'response' in locals() else ''
                if "EGeneral:Too many requests" in response_text and attempt < max_retries - 1:
                    time.sleep(2 ** attempt) # Exponential backoff
                    continue
                raise KrakenAPIError(f"Request failed: {e}. Response: {response_text}")
        raise KrakenAPIError(f"Failed to query API after {max_retries} retries.")

    def _fetch_asset_pairs(self):
        """
        Fetches all available asset pairs from Kraken's API.
        Returns a dictionary of pair data.
        """
        try:
            return self._query_api('public', '/0/public/AssetPairs')
        except Exception as e:
            # Fallback to empty dict if we can't fetch pairs
            return {}

    def _build_asset_to_usd_map(self):
        """
        Creates a mapping from cleaned asset names to their USD trading pairs.
        Only includes crypto assets, excludes forex pairs.
        Example: {'XBT': 'XXBTZUSD', 'ETH': 'XETHZUSD'}
        """
        asset_map = {}
        
        # Forex currencies to exclude
        forex_assets = {'USD', 'EUR', 'GBP', 'CAD', 'JPY', 'CHF', 'AUD', 'SEK', 'NOK', 'DKK'}
        
        for pair_name, pair_info in self.asset_pairs.items():
            # Look for pairs that trade against USD/ZUSD
            if ('USD' in pair_name or 'ZUSD' in pair_name):
                # Extract the base asset from the pair info
                base_asset = pair_info.get('base', '')
                quote_asset = pair_info.get('quote', '')
                
                # Clean the asset names (remove X/Z prefixes)
                if base_asset.startswith(('X', 'Z')) and len(base_asset) > 1:
                    clean_base = base_asset[1:]
                else:
                    clean_base = base_asset
                
                if quote_asset.startswith(('X', 'Z')) and len(quote_asset) > 1:
                    clean_quote = quote_asset[1:]
                else:
                    clean_quote = quote_asset
                
                # Only include if base is not forex and quote is USD
                if (clean_base not in forex_assets and 
                    clean_quote == 'USD' and 
                    clean_base and 
                    clean_base not in asset_map):
                    asset_map[clean_base] = pair_name
        
        return asset_map

    def get_valid_usd_pairs_for_assets(self, assets):
        """
        Given a list of asset names, returns only the valid USD trading pairs.
        Input: ['XBT', 'ETH', 'INVALID_ASSET']
        Output: ['XXBTZUSD', 'XETHZUSD']
        """
        valid_pairs = []
        for asset in assets:
            if asset in self.asset_to_usd_pair_map:
                valid_pairs.append(self.asset_to_usd_pair_map[asset])
        return valid_pairs

    def get_account_balance(self):
        """
        Fetches all asset balances from the spot wallet.
        Returns a dictionary of {'ASSET': balance}.
        """
        balance = self._query_api('private', '/0/private/Balance')
        clean_balance = {}
        if not balance:
            return {}
            
        for key, value in balance.items():
            # Kraken uses prefixes like X for crypto (XXBT) and Z for fiat (ZUSD)
            if len(key) > 3 and key.startswith(('X', 'Z')):
                clean_key = key[1:]
            else:
                clean_key = key
            
            amount = float(value)
            if amount > 1e-8: # Filter out dust balances
                clean_balance[clean_key] = amount
        return clean_balance

    def get_ticker_prices(self, pairs):
        """
        Gets the last traded price for one or more trading pairs.
        Input: ['XBTUSD', 'ETHUSD']
        Output: {'XXBTZUSD': {'price': 60000.0}, 'XETHZUSD': {'price': 4000.0}}
        """
        if not isinstance(pairs, list) or not pairs:
            raise ValueError("Input must be a non-empty list of pairs.")

        # Kraken's API expects comma-separated string for multiple pairs
        pair_string = ",".join(pairs)
        tickers = self._query_api('public', '/0/public/Ticker', {'pair': pair_string})

        prices = {}
        for pair, info in tickers.items():
            prices[pair] = {
                'price': float(info['c'][0]) # 'c' field is [last_trade_price, last_trade_volume]
            }
        return prices

    def get_pair_details(self, pair: str) -> dict:
        """
        Get detailed information for a specific trading pair, including ordermin.
        
        Args:
            pair: Trading pair name (e.g., 'XETHZUSD', 'XXBTZUSD')
            
        Returns:
            Dictionary with pair details including ordermin, or empty dict if not found
        """
        return self.asset_pairs.get(pair, {})
    
    def get_all_usd_trading_rules(self) -> dict:
        """
        Get trading rules for all USD pairs including minimum order sizes.
        
        Returns:
            Dictionary with pair info including minimum order sizes
        """
        trading_rules = {}
        
        for pair_name, pair_info in self.asset_pairs.items():
            # Look for pairs that trade against USD/ZUSD
            if 'USD' in pair_name or 'ZUSD' in pair_name:
                base_asset = pair_info.get('base', '')
                quote_asset = pair_info.get('quote', '')
                
                # Check if this is a USD pair
                if quote_asset in ['USD', 'ZUSD']:
                    trading_rules[pair_name] = {
                        'base': base_asset,
                        'quote': quote_asset,
                        'ordermin': pair_info.get('ordermin', '0.0001'),
                        'costmin': pair_info.get('costmin', '0.5'),
                        'tick_size': pair_info.get('tick_size', '0.01')
                    }
        
        return trading_rules

    def get_comprehensive_portfolio_context(self) -> dict:
        """
        Get comprehensive portfolio information including USD values, allocation percentages,
        and trading context for AI decision making.
        
        Returns:
            Dictionary containing:
            - portfolio_summary: Formatted string for prompt
            - raw_balances: Dict of asset balances
            - usd_values: Dict of USD values per asset
            - total_equity: Total portfolio value in USD
            - allocation_percentages: Asset allocation as percentages
            - tradeable_assets: List of assets that can be traded to USD
        """
        try:
            # Get raw balances from Kraken
            balance = self.get_account_balance()
            
            if not balance:
                return {
                    'portfolio_summary': "Portfolio is currently empty. No assets held.",
                    'raw_balances': {},
                    'usd_values': {},
                    'total_equity': 0.0,
                    'allocation_percentages': {},
                    'tradeable_assets': []
                }
            
            # Separate cash and crypto assets
            cash_assets = {'USDC', 'USD', 'USDT'}
            forex_assets = {'CAD', 'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'SEK', 'NOK', 'DKK'}
            
            # Calculate total cash value
            total_cash = 0.0
            for cash_asset in cash_assets:
                if cash_asset in balance:
                    total_cash += balance[cash_asset]
            
            # Identify crypto assets (excluding forex)
            crypto_assets = [asset for asset in balance.keys() 
                           if asset not in cash_assets and asset not in forex_assets]
            
            # Get USD prices for crypto assets
            usd_values = {}
            total_crypto_value = 0.0
            tradeable_assets = []
            
            if crypto_assets:
                valid_pairs = self.get_valid_usd_pairs_for_assets(crypto_assets)
                if valid_pairs:
                    prices = self.get_ticker_prices(valid_pairs)
                    
                    for asset in crypto_assets:
                        if asset in balance:
                            amount = balance[asset]
                            asset_pair = self.asset_to_usd_pair_map.get(asset)
                            
                            if asset_pair and asset_pair in prices:
                                price = prices[asset_pair]['price']
                                value = amount * price
                                usd_values[asset] = {
                                    'amount': amount,
                                    'price': price,
                                    'value': value
                                }
                                total_crypto_value += value
                                tradeable_assets.append(asset)
                            else:
                                usd_values[asset] = {
                                    'amount': amount,
                                    'price': 0.0,
                                    'value': 0.0
                                }
            
            # Add cash to USD values
            if total_cash > 0:
                usd_values['USD'] = {
                    'amount': total_cash,
                    'price': 1.0,
                    'value': total_cash
                }
                tradeable_assets.append('USD')
            
            # Calculate total equity
            total_equity = total_cash + total_crypto_value
            
            # Calculate allocation percentages
            allocation_percentages = {}
            if total_equity > 0:
                for asset, data in usd_values.items():
                    allocation_percentages[asset] = (data['value'] / total_equity) * 100
            
            # Build formatted portfolio summary for AI prompt
            portfolio_summary = f"Current cash balance: ${total_cash:,.2f} USD.\n"
            
            if crypto_assets:
                portfolio_summary += "Current Holdings:\n"
                for asset in sorted(crypto_assets, key=lambda x: usd_values.get(x, {}).get('value', 0), reverse=True):
                    if asset in usd_values:
                        data = usd_values[asset]
                        allocation = allocation_percentages.get(asset, 0)
                        # Only include positions worth at least $0.01 and > 0.05% allocation
                        if data['value'] >= 0.01 and allocation >= 0.05:
                            portfolio_summary += f"- {asset}: {data['amount']:.6f} (Value: ${data['value']:,.2f} @ ${data['price']:,.2f}) [{allocation:.1f}%]\n"
                        # For debugging: log dust positions but don't include in AI context
                        elif data['value'] > 0:
                            logger.debug(f"Filtering out dust position: {asset} ${data['value']:,.3f} ({allocation:.2f}%)")
            
            portfolio_summary += f"\nTotal Portfolio Value: ${total_equity:,.2f} USD"
            
            if total_equity > 0:
                cash_percentage = (total_cash / total_equity) * 100
                crypto_percentage = (total_crypto_value / total_equity) * 100
                portfolio_summary += f"\nAllocation: {cash_percentage:.1f}% Cash, {crypto_percentage:.1f}% Crypto"
            
            return {
                'portfolio_summary': portfolio_summary,
                'raw_balances': balance,
                'usd_values': usd_values,
                'total_equity': total_equity,
                'allocation_percentages': allocation_percentages,
                'tradeable_assets': tradeable_assets,
                'cash_balance': total_cash,
                'crypto_value': total_crypto_value
            }
            
        except Exception as e:
            logger.error(f"Error getting comprehensive portfolio context: {e}")
            return {
                'portfolio_summary': f"Error retrieving portfolio data: {e}",
                'raw_balances': {},
                'usd_values': {},
                'total_equity': 0.0,
                'allocation_percentages': {},
                'tradeable_assets': [],
                'cash_balance': 0.0,
                'crypto_value': 0.0
            }

    def place_order(self, pair, order_type, volume, ordertype='market', validate=False):
        """
        Submits a market buy or sell order.
        - pair: The trading pair, e.g., 'XBTUSD'
        - order_type: 'buy' or 'sell'
        - volume: The amount of asset to trade
        - validate: If True, test order without executing.
        """
        data = {
            'pair': pair,
            'type': order_type,
            'ordertype': ordertype,
            'volume': f"{volume:.8f}", # Format volume to 8 decimal places
        }
        if validate:
            data['validate'] = 'true'
        
        result = self._query_api('private', '/0/private/AddOrder', data)
        return result
