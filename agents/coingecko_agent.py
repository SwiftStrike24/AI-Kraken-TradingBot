"""
CoinGecko Agent (Market Data Specialist)

This agent specializes in gathering comprehensive cryptocurrency market data
from the CoinGecko API, including real-time prices, market caps, volumes,
trending tokens, and market performance metrics.

It provides structured market intelligence to complement the news-based
research from the Analyst Agent with quantitative market data.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta

from .base_agent import BaseAgent

# logger = logging.getLogger(__name__)

class CoinGeckoAPIError(Exception):
    """Custom exception for CoinGecko API errors."""
    pass

class CoinGeckoAgent(BaseAgent):
    """
    The CoinGecko-AI specializes in cryptocurrency market data gathering.
    
    This agent:
    1. Fetches real-time token price data and market metrics
    2. Retrieves trending tokens from CoinGecko
    3. Provides structured market data for trading decisions
    4. Implements intelligent caching and rate limiting
    """
    
    def __init__(self, logs_dir: str = "logs", session_dir: str = None, api_key: Optional[str] = None):
        """
        Initialize the CoinGecko Agent.
        
        Args:
            logs_dir: Directory for saving agent transcripts
            session_dir: Optional session directory for unified transcript storage
            api_key: Optional CoinGecko API key for higher rate limits
        """
        super().__init__("CoinGecko-AI", logs_dir, session_dir)
        
        # API configuration
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = api_key or os.getenv('COINGECKO_API_KEY')
        
        # Session for persistent connections
        self.session = requests.Session()
        
        # Headers for API requests
        headers = {
            'User-Agent': 'ChatGPT-Kraken-Bot/1.0',
            'Accept': 'application/json'
        }
        
        if self.api_key:
            headers['x-cg-demo-api-key'] = self.api_key
            
        self.session.headers.update(headers)
        
        # Cache configuration
        self.cache_file = os.path.join(logs_dir, "coingecko_cache.json")
        self.cache_duration = 300  # 5 minutes
        self.cache = self._load_cache()
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 2.0  # 2 seconds between requests for free tier
        
        # Validation controls (env toggles)
        self.validate_changes = os.getenv("COINGECKO_VALIDATE", "0").lower() in {"1", "true", "yes"}
        try:
            self.validation_tolerance_pp = float(os.getenv("COINGECKO_TOLERANCE_PCTPOINTS", "0.2"))
        except ValueError:
            self.validation_tolerance_pp = 0.2
        self.validation_log_path = os.path.join(logs_dir, "coingecko_validation.jsonl")
        
        self.logger.info("CoinGecko agent initialized successfully")
    
    def execute(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute market data gathering from CoinGecko.
        
        Args:
            inputs: Control inputs from Supervisor with optional configurations
            
        Returns:
            Structured market data report
        """
        self.logger.info("Beginning CoinGecko market data gathering...")
        
        # Extract configuration from inputs
        token_ids = inputs.get('token_ids', ['bitcoin', 'ethereum', 'solana', 'cardano', 'ripple', 'sui', 'ethena', 'dogecoin', 'fartcoin', 'bonk'])
        include_trending = inputs.get('include_trending', True)
        vs_currency = inputs.get('vs_currency', 'usd')
        
        try:
            market_data = {}
            trending_data = {}
            
            # Fetch market data for specified tokens
            if token_ids:
                self.logger.info(f"Fetching market data for {len(token_ids)} tokens")
                market_data = self.get_token_market_data(token_ids, vs_currency)
            
            # Fetch trending tokens if requested
            if include_trending:
                self.logger.info("Fetching trending tokens data")
                trending_data = self.get_trending_tokens(vs_currency)
            
            # Assess data quality
            data_quality = self._assess_data_quality(market_data, trending_data)
            
            self.logger.info("CoinGecko market data gathering completed successfully")
            
            return {
                "status": "success",
                "agent": "CoinGecko-AI",
                "timestamp": datetime.now().isoformat(),
                "market_data": market_data,
                "trending_data": trending_data,
                "configuration": {
                    "token_ids": token_ids,
                    "vs_currency": vs_currency,
                    "include_trending": include_trending
                },
                "data_quality": data_quality,
                "cache_stats": self._get_cache_stats()
            }
            
        except CoinGeckoAPIError as e:
            self.logger.error(f"CoinGecko API error: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during market data gathering: {e}")
            raise
    
    def get_token_market_data(self, token_ids: List[str], vs_currency: str = 'usd') -> Dict[str, Any]:
        """
        Fetch detailed market data for specified tokens.
        
        Args:
            token_ids: List of CoinGecko token IDs (e.g., ['bitcoin', 'ethereum'])
            vs_currency: Currency to price against (default: 'usd')
            
        Returns:
            Dictionary with market data for each token
        """
        cache_key = f"market_data_{','.join(sorted(token_ids))}_{vs_currency}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            self.logger.info(f"Using cached market data for {len(token_ids)} tokens")
            return cached_data
        
        # Prepare API request
        endpoint = "/coins/markets"
        params = {
            'ids': ','.join(token_ids),
            'vs_currency': vs_currency,
            'order': 'market_cap_desc',
            'per_page': len(token_ids),
            'page': 1,
            'sparkline': False,
            'price_change_percentage': '1h,24h,7d,30d'
        }
        
        try:
            response_data = self._query_api(endpoint, params)
            
            # Structure the response
            market_data: Dict[str, Any] = {}
            for coin in response_data:
                token_id = coin['id']
                market_data[token_id] = {
                    'name': coin['name'],
                    'symbol': coin['symbol'],
                    'current_price': coin['current_price'],
                    'market_cap': coin['market_cap'],
                    'market_cap_rank': coin['market_cap_rank'],
                    'fully_diluted_valuation': coin['fully_diluted_valuation'],
                    'total_volume': coin['total_volume'],
                    'circulating_supply': coin['circulating_supply'],
                    'total_supply': coin['total_supply'],
                    'max_supply': coin['max_supply'],
                    'price_change_percentage_1h': coin.get('price_change_percentage_1h_in_currency'),
                    'price_change_percentage_24h': coin.get('price_change_percentage_24h_in_currency'),
                    'price_change_percentage_7d': coin.get('price_change_percentage_7d_in_currency'),
                    'price_change_percentage_30d': coin.get('price_change_percentage_30d_in_currency'),
                    'last_updated': coin['last_updated']
                }
            
            # Validation and fallback: fill missing or inconsistent values
            for token_id in list(market_data.keys()):
                token_entry = market_data[token_id]
                # Determine which fields are missing
                pct_fields = [
                    ('1h', 'price_change_percentage_1h'),
                    ('24h', 'price_change_percentage_24h'),
                    ('7d', 'price_change_percentage_7d'),
                    ('30d', 'price_change_percentage_30d'),
                ]
                need_overview = any(token_entry.get(field_name) is None for _, field_name in pct_fields)
                overview = None
                recomputed = None

                # Fetch coin overview if needed or if validation is on
                if need_overview or self.validate_changes:
                    try:
                        overview = self._fetch_coin_overview(token_id)
                    except Exception as _:
                        overview = None
                
                # Fetch market chart and recompute if still missing or validation is on
                if need_overview or self.validate_changes:
                    try:
                        chart = self._fetch_market_chart(token_id, vs_currency=vs_currency, days=30, interval='hourly')
                        recomputed = self._recompute_changes_from_chart(chart.get('prices', []))
                    except Exception as _:
                        recomputed = None
                
                sources_used: Dict[str, str] = {}
                discrepancies: Dict[str, Dict[str, float]] = {}

                for horizon, field_name in pct_fields:
                    mkts_val = token_entry.get(field_name)

                    ov_val = None
                    if overview:
                        ov_map = {
                            '1h': 'price_change_percentage_1h_in_currency',
                            '24h': 'price_change_percentage_24h_in_currency',
                            '7d': 'price_change_percentage_7d_in_currency',
                            '30d': 'price_change_percentage_30d_in_currency'
                        }
                        # Coin overview uses nested fields under market_data; in_currency may be a dict per fiat
                        md = overview.get('market_data') if isinstance(overview, dict) else None
                        if md:
                            # CoinGecko often provides fiat-agnostic percentage fields (not per currency) on overview
                            if horizon == '1h':
                                ov_val = md.get('price_change_percentage_1h_in_currency', {}).get(vs_currency)
                            elif horizon == '24h':
                                ov_val = md.get('price_change_percentage_24h_in_currency', {}).get(vs_currency)
                            elif horizon == '7d':
                                ov_val = md.get('price_change_percentage_7d_in_currency', {}).get(vs_currency)
                            elif horizon == '30d':
                                ov_val = md.get('price_change_percentage_30d_in_currency', {}).get(vs_currency)
                    rc_val = None
                    if recomputed:
                        rc_val = recomputed.get(horizon)

                    selected_val = mkts_val
                    source = 'markets'

                    # Fallback when mkts missing
                    if selected_val is None:
                        if ov_val is not None:
                            selected_val = ov_val
                            source = 'coin_overview'
                        elif rc_val is not None:
                            selected_val = rc_val
                            source = 'recomputed'

                    # If validation mode, consider swapping when mkts deviates strongly and others agree
                    if self.validate_changes and mkts_val is not None:
                        diffs = {}
                        if ov_val is not None:
                            diffs['markets_vs_overview'] = abs(mkts_val - ov_val)
                        if rc_val is not None:
                            diffs['markets_vs_recomputed'] = abs(mkts_val - rc_val)
                        # If both alt sources exist and agree, and mkts far, switch to overview
                        if ov_val is not None and rc_val is not None:
                            if abs(ov_val - rc_val) <= self.validation_tolerance_pp and max(diffs.values() or [0]) > self.validation_tolerance_pp:
                                selected_val = ov_val
                                source = 'coin_overview'
                                discrepancies[field_name] = {
                                    'markets': mkts_val,
                                    'overview': ov_val,
                                    'recomputed': rc_val
                                }
                        elif ov_val is not None and 'markets_vs_overview' in diffs and diffs['markets_vs_overview'] > self.validation_tolerance_pp:
                            selected_val = ov_val
                            source = 'coin_overview'
                            discrepancies[field_name] = {
                                'markets': mkts_val,
                                'overview': ov_val,
                                'recomputed': rc_val if rc_val is not None else float('nan')
                            }
                        elif rc_val is not None and 'markets_vs_recomputed' in diffs and diffs['markets_vs_recomputed'] > self.validation_tolerance_pp:
                            # Prefer recomputed only if overview missing
                            if ov_val is None:
                                selected_val = rc_val
                                source = 'recomputed'
                                discrepancies[field_name] = {
                                    'markets': mkts_val,
                                    'overview': float('nan'),
                                    'recomputed': rc_val
                                }

                    token_entry[field_name] = selected_val
                    sources_used[field_name] = source
                
                if self.validate_changes:
                    try:
                        self._log_validation(token_id, market_data[token_id], overview, recomputed, sources_used, discrepancies)
                    except Exception as _:
                        pass
                # Attach sources so downstream can optionally show provenance
                token_entry['price_change_pct_sources'] = sources_used
            
            # Cache the structured data
            self._cache_data(cache_key, market_data)
            
            self.logger.info(f"Successfully fetched market data for {len(market_data)} tokens")
            return market_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch market data: {e}")
            raise CoinGeckoAPIError(f"Market data fetch failed: {e}")
    
    def get_trending_tokens(self, vs_currency: str = 'usd') -> Dict[str, Any]:
        """
        Fetch currently trending tokens from CoinGecko.
        
        Returns:
            Dictionary with trending tokens data
        """
        cache_key = f"trending_tokens_{vs_currency}"
        
        # Check cache first
        cached_data = self._get_cached_data(cache_key)
        if cached_data:
            self.logger.info("Using cached trending tokens data")
            return cached_data
        
        endpoint = "/search/trending"
        
        try:
            response_data = self._query_api(endpoint, {})
            
            # Structure trending data
            trending_data = {
                'coins': [],
                'nfts': [],
                'categories': []
            }
            
            # Process trending coins
            trending_ids: List[str] = []
            for coin_data in response_data.get('coins', []):
                coin = coin_data.get('item', {})
                trending_data['coins'].append({
                    'id': coin.get('id'),
                    'name': coin.get('name'),
                    'symbol': coin.get('symbol'),
                    'market_cap_rank': coin.get('market_cap_rank'),
                    'thumb': coin.get('thumb'),
                    'price_btc': coin.get('price_btc'),  # kept for reference; not displayed
                    'score': coin.get('score')
                })
                if coin.get('id'):
                    trending_ids.append(coin.get('id'))
            
            # Enrich trending coins with USD metrics using /coins/markets
            if trending_ids:
                try:
                    markets = self._query_api(
                        "/coins/markets",
                        {
                            'ids': ','.join(trending_ids),
                            'vs_currency': vs_currency,
                            'order': 'market_cap_desc',
                            'per_page': len(trending_ids),
                            'page': 1,
                            'sparkline': False,
                            'price_change_percentage': '1h,24h,7d,30d'
                        }
                    )
                    mk_map = {m['id']: m for m in markets if isinstance(m, dict) and 'id' in m}
                    for coin in trending_data['coins']:
                        m = mk_map.get(coin.get('id'))
                        if not m:
                            continue
                        coin['price_usd'] = m.get('current_price')
                        coin['price_change_percentage_1h'] = m.get('price_change_percentage_1h_in_currency')
                        coin['price_change_percentage_24h'] = m.get('price_change_percentage_24h_in_currency')
                        coin['price_change_percentage_7d'] = m.get('price_change_percentage_7d_in_currency')
                        coin['price_change_percentage_30d'] = m.get('price_change_percentage_30d_in_currency')
                        coin['market_cap'] = m.get('market_cap')
                        coin['total_volume'] = m.get('total_volume')
                except Exception as enrich_err:
                    self.logger.warning(f"Could not enrich trending coins with USD metrics: {enrich_err}")
            
            # Process trending NFTs
            for nft_data in response_data.get('nfts', []):
                nft = nft_data.get('item', {})
                trending_data['nfts'].append({
                    'id': nft.get('id'),
                    'name': nft.get('name'),
                    'symbol': nft.get('symbol'),
                    'thumb': nft.get('thumb'),
                    'floor_price_in_native_currency': nft.get('floor_price_in_native_currency'),
                    'floor_price_24h_percentage_change': nft.get('floor_price_24h_percentage_change')
                })
            
            # Process trending categories
            for cat_data in response_data.get('categories', []):
                category = cat_data.get('item', {})
                trending_data['categories'].append({
                    'id': category.get('id'),
                    'name': category.get('name'),
                    'market_cap_1h_change': category.get('market_cap_1h_change'),
                    'slug': category.get('slug')
                })
            
            # Cache the data
            self._cache_data(cache_key, trending_data)
            
            self.logger.info(f"Successfully fetched {len(trending_data['coins'])} trending coins")
            return trending_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch trending data: {e}")
            raise CoinGeckoAPIError(f"Trending data fetch failed: {e}")
    
    def _query_api(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make a request to the CoinGecko API with proper rate limiting and error handling.
        
        Args:
            endpoint: API endpoint (e.g., '/coins/markets')
            params: Query parameters
            
        Returns:
            Parsed JSON response
        """
        # Rate limiting
        time_since_last = time.time() - self.last_request_time
        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.debug(f"Making request to: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            self.last_request_time = time.time()
            
            # Handle rate limiting
            if response.status_code == 429:
                retry_after = int(response.headers.get('Retry-After', 60))
                self.logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                time.sleep(retry_after)
                response = self.session.get(url, params=params, timeout=30)
                self.last_request_time = time.time()
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            raise CoinGeckoAPIError("API request timed out")
        except requests.exceptions.ConnectionError:
            raise CoinGeckoAPIError("Failed to connect to CoinGecko API")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 404:
                raise CoinGeckoAPIError(f"Endpoint not found: {endpoint}")
            elif response.status_code == 429:
                raise CoinGeckoAPIError("Rate limit exceeded")
            else:
                raise CoinGeckoAPIError(f"HTTP {response.status_code}: {e}")
        except json.JSONDecodeError:
            raise CoinGeckoAPIError("Invalid JSON response from API")
        except Exception as e:
            raise CoinGeckoAPIError(f"Unexpected API error: {e}")
    
    def _load_cache(self) -> Dict[str, Any]:
        """Load cache from file if it exists."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                # Clean expired entries
                self._clean_expired_cache(cache)
                return cache
        except Exception as e:
            self.logger.warning(f"Failed to load cache: {e}")
        
        return {}
    
    def _save_cache(self):
        """Save cache to file."""
        try:
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cache, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save cache: {e}")
    
    def _clean_expired_cache(self, cache: Dict[str, Any]):
        """Remove expired entries from cache."""
        current_time = datetime.now()
        expired_keys = []
        
        for key, entry in cache.items():
            if isinstance(entry, dict) and 'timestamp' in entry:
                cached_time = datetime.fromisoformat(entry['timestamp'])
                if (current_time - cached_time).total_seconds() > self.cache_duration:
                    expired_keys.append(key)
        
        for key in expired_keys:
            del cache[key]
    
    def _get_cached_data(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get data from cache if not expired."""
        entry = self.cache.get(cache_key)
        if not entry or 'timestamp' not in entry:
            return None
        
        cached_time = datetime.fromisoformat(entry['timestamp'])
        if (datetime.now() - cached_time).total_seconds() > self.cache_duration:
            # Expired
            del self.cache[cache_key]
            return None
        
        return entry.get('data')
    
    def _cache_data(self, cache_key: str, data: Dict[str, Any]):
        """Cache data with timestamp."""
        self.cache[cache_key] = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self._save_cache()
    
    def _assess_data_quality(self, market_data: Dict[str, Any], trending_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality and completeness of gathered market data.
        
        Args:
            market_data: Token market data
            trending_data: Trending tokens data
            
        Returns:
            Quality assessment metrics
        """
        market_tokens = len(market_data)
        trending_coins = len(trending_data.get('coins', []))
        
        # Quality scoring based on data completeness
        if market_tokens >= 8 and trending_coins >= 7:
            quality_score = "excellent"
        elif market_tokens >= 5 and trending_coins >= 5:
            quality_score = "good"
        elif market_tokens >= 3 and trending_coins >= 1:
            quality_score = "fair"
        else:
            quality_score = "poor"
        
        return {
            "quality_score": quality_score,
            "market_tokens_count": market_tokens,
            "trending_coins_count": trending_coins,
            "trending_nfts_count": len(trending_data.get('nfts', [])),
            "data_freshness": "real-time",
            "api_status": "operational"
        }
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_entries = len(self.cache)
        valid_entries = 0
        
        current_time = datetime.now()
        for entry in self.cache.values():
            if isinstance(entry, dict) and 'timestamp' in entry:
                cached_time = datetime.fromisoformat(entry['timestamp'])
                if (current_time - cached_time).total_seconds() <= self.cache_duration:
                    valid_entries += 1
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "cache_hit_ratio": valid_entries / max(total_entries, 1),
            "cache_duration_minutes": self.cache_duration / 60
        }
    
    def generate_reasoning(self, inputs: Dict[str, Any], outputs: Dict[str, Any]) -> str:
        """
        Generate detailed reasoning about the market data gathering process.
        
        Args:
            inputs: Input directives from supervisor
            outputs: Generated market data report
            
        Returns:
            Natural language explanation of the data gathering process
        """
        if outputs.get("status") == "error":
            return f"Market data gathering failed due to: {outputs.get('error_message', 'unknown error')}. This will impact trading decision quality significantly."
        
        market_data = outputs.get("market_data", {})
        trending_data = outputs.get("trending_data", {})
        data_quality = outputs.get("data_quality", {})
        cache_stats = outputs.get("cache_stats", {})
        
        reasoning = f"""
        CoinGecko Market Data Analysis Completed:
        
        1. Market Data Collection: Successfully gathered data for {data_quality.get('market_tokens_count', 0)} cryptocurrencies
        2. Trending Analysis: Identified {data_quality.get('trending_coins_count', 0)} trending coins and {data_quality.get('trending_nfts_count', 0)} trending NFTs
        3. Data Quality: {data_quality.get('quality_score', 'unknown')} - providing {data_quality.get('data_freshness', 'unknown')} market intelligence
        4. Performance: Cache hit ratio of {cache_stats.get('cache_hit_ratio', 0)*100:.0f}% with {cache_stats.get('valid_entries', 0)} valid cached entries
        5. Strategic Impact: This quantitative market data complements news-based intelligence for comprehensive market analysis
        
        Key market insights extracted from CoinGecko include real-time pricing, market cap rankings, volume trends, and trending token momentum indicators.
        """
        
        return reasoning.strip() 

    def _fetch_coin_overview(self, token_id: str) -> Optional[Dict[str, Any]]:
        """Fetch coin overview with market_data for a single token."""
        endpoint = f"/coins/{token_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'market_data': 'true',
            'community_data': 'false',
            'developer_data': 'false',
            'sparkline': 'false',
        }
        return self._query_api(endpoint, params)

    def _fetch_market_chart(self, token_id: str, vs_currency: str = 'usd', days: int = 30, interval: str = 'hourly') -> Optional[Dict[str, Any]]:
        """Fetch market chart data for a token to recompute change percentages."""
        endpoint = f"/coins/{token_id}/market_chart"
        params = {
            'vs_currency': vs_currency,
            'days': days,
            'interval': interval,
        }
        return self._query_api(endpoint, params)

    def _recompute_changes_from_chart(self, prices: List[List[float]]) -> Optional[Dict[str, float]]:
        """
        Recompute 1h/24h/7d/30d change percentages from time-series prices.
        prices: list of [timestamp_ms, price]
        """
        try:
            if not prices or len(prices) < 2:
                return None
            # Ensure sorted by timestamp
            prices_sorted = sorted(prices, key=lambda x: x[0])
            last_ts_ms, last_px = prices_sorted[-1]
            if not last_px or last_px <= 0:
                return None
            targets_sec = {
                '1h': 3600,
                '24h': 24*3600,
                '7d': 7*24*3600,
                '30d': 30*24*3600,
            }
            results: Dict[str, float] = {}
            for key, secs in targets_sec.items():
                target_ms = last_ts_ms - (secs * 1000)
                base_px = self._find_price_at_or_before(prices_sorted, target_ms)
                if base_px and base_px > 0:
                    pct = (last_px - base_px) / base_px * 100.0
                    results[key] = pct
                else:
                    results[key] = None
            return results
        except Exception:
            return None

    def _find_price_at_or_before(self, series: List[List[float]], ts_ms: int) -> Optional[float]:
        """Binary search nearest price at or before ts_ms."""
        lo, hi = 0, len(series) - 1
        candidate = None
        while lo <= hi:
            mid = (lo + hi) // 2
            mid_ts = series[mid][0]
            if mid_ts == ts_ms:
                return float(series[mid][1])
            if mid_ts < ts_ms:
                candidate = float(series[mid][1])
                lo = mid + 1
            else:
                hi = mid - 1
        return candidate

    def _log_validation(self, token_id: str, markets_entry: Dict[str, Any], overview: Optional[Dict[str, Any]], recomputed: Optional[Dict[str, float]], sources_used: Dict[str, str], discrepancies: Dict[str, Dict[str, float]]):
        """Append a validation record to JSONL file for offline inspection."""
        record: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'token_id': token_id,
            'markets': {
                'price_change_percentage_1h': markets_entry.get('price_change_percentage_1h'),
                'price_change_percentage_24h': markets_entry.get('price_change_percentage_24h'),
                'price_change_percentage_7d': markets_entry.get('price_change_percentage_7d'),
                'price_change_percentage_30d': markets_entry.get('price_change_percentage_30d'),
                'current_price': markets_entry.get('current_price'),
            },
            'sources_used': sources_used,
            'discrepancies': discrepancies,
            'tolerance_pp': self.validation_tolerance_pp,
        }
        if overview and isinstance(overview, dict):
            md = overview.get('market_data', {})
            record['coin_overview'] = {
                'price_change_percentage_1h': (md.get('price_change_percentage_1h_in_currency') or {}).get('usd'),
                'price_change_percentage_24h': (md.get('price_change_percentage_24h_in_currency') or {}).get('usd'),
                'price_change_percentage_7d': (md.get('price_change_percentage_7d_in_currency') or {}).get('usd'),
                'price_change_percentage_30d': (md.get('price_change_percentage_30d_in_currency') or {}).get('usd'),
            }
        else:
            record['coin_overview'] = None
        record['recomputed'] = recomputed
        os.makedirs(os.path.dirname(self.validation_log_path), exist_ok=True)
        with open(self.validation_log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + "\n") 