"""
Bitpin exchange client implementation (Iranian exchange)
"""

import asyncio
import logging
import hashlib
import hmac
import time
import json
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

import aiohttp

logger = logging.getLogger(__name__)


class BitpinClient:
    """Bitpin exchange client (Iranian exchange) with async support"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.bitpin.org"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(3)  # Conservative rate limiting
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            headers = {
                'User-Agent': 'AI-DevOps-Assistant/1.0',
                'Content-Type': 'application/json'
            }
            self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        return self.session
    
    def _generate_signature(self, params: Dict[str, Any], timestamp: str) -> str:
        """Generate HMAC SHA256 signature for Bitpin API"""
        # Bitpin signature format - adjust based on actual API documentation
        message = f"{timestamp}{json.dumps(params, separators=(',', ':'), sort_keys=True)}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                      signed: bool = False) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Bitpin API"""
        async with self._rate_limiter:
            url = f"{self.base_url}{endpoint}"
            headers = {}
            
            if params is None:
                params = {}
            
            if signed:
                timestamp = str(int(time.time() * 1000))
                headers.update({
                    'Authorization': f'Token {self.api_key}',
                    'X-Timestamp': timestamp,
                    'X-Signature': self._generate_signature(params, timestamp)
                })
            
            session = await self._get_session()
            
            try:
                if method.upper() == 'GET':
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Bitpin API error: {response.status} - {error_text}")
                            return None
                            
                elif method.upper() == 'POST':
                    async with session.post(url, json=params, headers=headers) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Bitpin API error: {response.status} - {error_text}")
                            return None
                            
            except asyncio.TimeoutError:
                logger.error(f"Timeout for Bitpin API request: {endpoint}")
                return None
            except Exception as e:
                logger.error(f"Bitpin API request failed: {e}")
                return None
    
    async def get_server_time(self) -> Optional[Dict[str, Any]]:
        """Get server time from Bitpin"""
        # Use currencies endpoint as health check
        result = await self._request('GET', '/v1/currencies/')
        return {'server_time': int(time.time() * 1000)} if result else None
    
    async def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Get exchange information and trading rules"""
        currencies = await self._request('GET', '/v1/currencies/')
        
        if currencies:
            return {
                'name': 'Bitpin',
                'type': 'iranian',
                'base_currency': 'IRT',  # Iranian Rial Toman
                'supported_currencies': [curr.get('code') for curr in currencies if isinstance(curr, dict)],
                'trading_features': ['spot_trading', 'rial_gateway', 'p2p_trading']
            }
        
        return None
    
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for symbol"""
        # Bitpin uses market ID instead of symbol pairs
        # This is a simplified approach - in practice, you'd need to map symbols to market IDs
        
        markets = await self._request('GET', '/v1/mkt/markets/')
        
        if markets:
            # Find market by symbol
            for market in markets:
                if isinstance(market, dict):
                    market_symbol = f"{market.get('currency1', {}).get('code', '')}/{market.get('currency2', {}).get('code', '')}"
                    if market_symbol.upper() == symbol.upper():
                        market_id = market.get('id')
                        
                        # Get ticker data for this market
                        ticker = await self._request('GET', f'/v1/mkt/markets/{market_id}/')
                        
                        if ticker:
                            return {
                                'symbol': symbol,
                                'lastPrice': ticker.get('price'),
                                'priceChange': ticker.get('change'),
                                'priceChangePercent': ticker.get('change_percent'),
                                'volume': ticker.get('volume_24h'),
                                'high': ticker.get('high_24h'),
                                'low': ticker.get('low_24h')
                            }
        
        return None
    
    async def get_all_tickers(self) -> Optional[List[Dict[str, Any]]]:
        """Get all ticker data"""
        markets = await self._request('GET', '/v1/mkt/markets/')
        
        if markets:
            tickers = []
            
            for market in markets:
                if isinstance(market, dict):
                    currency1 = market.get('currency1', {}).get('code', '')
                    currency2 = market.get('currency2', {}).get('code', '')
                    symbol = f"{currency1}/{currency2}"
                    
                    ticker = {
                        'symbol': symbol,
                        'lastPrice': market.get('price'),
                        'priceChange': market.get('change'),
                        'priceChangePercent': market.get('change_percent'),
                        'volume': market.get('volume_24h'),
                        'high': market.get('high_24h'),
                        'low': market.get('low_24h')
                    }
                    tickers.append(ticker)
            
            return tickers
        
        return None
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance"""
        result = await self._request('GET', '/v1/usr/wallets/', signed=True)
        
        if result:
            balance = {}
            
            for wallet in result:
                if isinstance(wallet, dict):
                    currency = wallet.get('currency', {}).get('code', '').upper()
                    available = float(wallet.get('balance', 0))
                    frozen = float(wallet.get('frozen', 0))
                    
                    if available > 0 or frozen > 0:
                        balance[currency] = {
                            'free': available,
                            'locked': frozen,
                            'total': available + frozen
                        }
            
            return balance
        
        return None
    
    async def get_orderbook(self, symbol: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get order book for symbol"""
        # First find the market ID for this symbol
        markets = await self._request('GET', '/v1/mkt/markets/')
        
        if markets:
            for market in markets:
                if isinstance(market, dict):
                    currency1 = market.get('currency1', {}).get('code', '')
                    currency2 = market.get('currency2', {}).get('code', '')
                    market_symbol = f"{currency1}/{currency2}"
                    
                    if market_symbol.upper() == symbol.upper():
                        market_id = market.get('id')
                        
                        # Get orderbook for this market
                        orderbook = await self._request('GET', f'/v1/mkt/orderbook/{market_id}/')
                        
                        if orderbook:
                            return {
                                'symbol': symbol,
                                'bids': orderbook.get('bids', []),
                                'asks': orderbook.get('asks', [])
                            }
        
        return None
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a new order"""
        # First find the market ID
        markets = await self._request('GET', '/v1/mkt/markets/')
        
        if markets:
            for market in markets:
                if isinstance(market, dict):
                    currency1 = market.get('currency1', {}).get('code', '')
                    currency2 = market.get('currency2', {}).get('code', '')
                    market_symbol = f"{currency1}/{currency2}"
                    
                    if market_symbol.upper() == symbol.upper():
                        market_id = market.get('id')
                        
                        params = {
                            'market': market_id,
                            'type': side.lower(),  # 'buy' or 'sell'
                            'amount': str(quantity)
                        }
                        
                        if order_type.upper() == 'LIMIT' and price:
                            params['price'] = str(price)
                            params['mode'] = 'limit'
                        else:
                            params['mode'] = 'market'
                        
                        return await self._request('POST', '/v1/usr/orders/', params, signed=True)
        
        return None
    
    async def get_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order status"""
        return await self._request('GET', f'/v1/usr/orders/{order_id}/', signed=True)
    
    async def cancel_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Cancel an active order"""
        return await self._request('DELETE', f'/v1/usr/orders/{order_id}/', signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get all open orders"""
        params = {'status': 'active'}
        
        # If symbol is specified, find market ID
        if symbol:
            markets = await self._request('GET', '/v1/mkt/markets/')
            if markets:
                for market in markets:
                    if isinstance(market, dict):
                        currency1 = market.get('currency1', {}).get('code', '')
                        currency2 = market.get('currency2', {}).get('code', '')
                        market_symbol = f"{currency1}/{currency2}"
                        
                        if market_symbol.upper() == symbol.upper():
                            params['market'] = market.get('id')
                            break
        
        return await self._request('GET', '/v1/usr/orders/', params, signed=True)
    
    async def get_order_history(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get order history"""
        params = {'status': 'done', 'limit': limit}
        
        # Find market ID for symbol
        markets = await self._request('GET', '/v1/mkt/markets/')
        if markets:
            for market in markets:
                if isinstance(market, dict):
                    currency1 = market.get('currency1', {}).get('code', '')
                    currency2 = market.get('currency2', {}).get('code', '')
                    market_symbol = f"{currency1}/{currency2}"
                    
                    if market_symbol.upper() == symbol.upper():
                        params['market'] = market.get('id')
                        break
        
        return await self._request('GET', '/v1/usr/orders/', params, signed=True)
    
    async def get_trade_history(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get trade history"""
        params = {'limit': limit}
        
        # Find market ID for symbol
        markets = await self._request('GET', '/v1/mkt/markets/')
        if markets:
            for market in markets:
                if isinstance(market, dict):
                    currency1 = market.get('currency1', {}).get('code', '')
                    currency2 = market.get('currency2', {}).get('code', '')
                    market_symbol = f"{currency1}/{currency2}"
                    
                    if market_symbol.upper() == symbol.upper():
                        params['market'] = market.get('id')
                        break
        
        return await self._request('GET', '/v1/usr/trades/', params, signed=True)
    
    async def get_currencies(self) -> Optional[List[Dict[str, Any]]]:
        """Get supported currencies"""
        return await self._request('GET', '/v1/currencies/')
    
    async def get_markets(self) -> Optional[List[Dict[str, Any]]]:
        """Get all available markets"""
        return await self._request('GET', '/v1/mkt/markets/')
    
    async def get_market_summary(self) -> Optional[Dict[str, Any]]:
        """Get market summary"""
        markets = await self.get_markets()
        
        if markets:
            summary = {
                'total_markets': len(markets),
                'total_volume_irt': 0,
                'gainers': 0,
                'losers': 0,
                'top_gainer': None,
                'top_loser': None
            }
            
            max_change = -100.0
            min_change = 100.0
            
            for market in markets:
                if isinstance(market, dict):
                    change_percent = float(market.get('change_percent', 0))
                    volume = float(market.get('volume_24h', 0))
                    
                    summary['total_volume_irt'] += volume
                    
                    if change_percent > 0:
                        summary['gainers'] += 1
                    elif change_percent < 0:
                        summary['losers'] += 1
                    
                    if change_percent > max_change:
                        max_change = change_percent
                        summary['top_gainer'] = market
                    
                    if change_percent < min_change:
                        min_change = change_percent
                        summary['top_loser'] = market
            
            return summary
        
        return None
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            asyncio.create_task(self.session.close())