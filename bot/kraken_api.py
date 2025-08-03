import os
import time
import base64
import hashlib
import hmac
import requests
import urllib.parse

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
