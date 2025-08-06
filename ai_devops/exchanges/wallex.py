"""
Wallex exchange client implementation (Iranian exchange)
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


class WallexClient:
    """Wallex exchange client (Iranian exchange) with async support"""
    
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.wallex.ir"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(5)  # Conservative rate limiting
    
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
        """Generate HMAC SHA256 signature for Wallex API"""
        # Wallex signature format may differ - this is a placeholder
        message = f"{timestamp}{json.dumps(params, sort_keys=True)}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                      signed: bool = False) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Wallex API"""
        async with self._rate_limiter:
            url = f"{self.base_url}{endpoint}"
            headers = {}
            
            if params is None:
                params = {}
            
            if signed:
                timestamp = str(int(time.time() * 1000))
                headers.update({
                    'X-API-Key': self.api_key,
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
                            logger.error(f"Wallex API error: {response.status} - {error_text}")
                            return None
                            
                elif method.upper() == 'POST':
                    async with session.post(url, json=params, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Wallex API error: {response.status} - {error_text}")
                            return None
                            
            except asyncio.TimeoutError:
                logger.error(f"Timeout for Wallex API request: {endpoint}")
                return None
            except Exception as e:
                logger.error(f"Wallex API request failed: {e}")
                return None
    
    async def get_server_time(self) -> Optional[Dict[str, Any]]:
        """Get server time from Wallex"""
        # Wallex might not have a dedicated ping endpoint, so we get stats
        return await self._request('GET', '/v1/currencies/stats')
    
    async def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Get exchange information and trading rules"""
        result = await self._request('GET', '/v1/currencies/stats')
        
        if result:
            return {
                'name': 'Wallex',
                'type': 'iranian',
                'base_currency': 'IRT',  # Iranian Rial Toman
                'supported_currencies': list(result.keys()) if isinstance(result, dict) else [],
                'trading_features': ['spot_trading', 'rial_gateway']
            }
        
        return None
    
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for symbol"""
        # Wallex uses different symbol format, typically just the currency
        # e.g., 'BTC' instead of 'BTC/IRT'
        currency = symbol.replace('/IRT', '').replace('/TMN', '').upper()
        
        result = await self._request('GET', f'/v1/currencies/stats')
        
        if result and isinstance(result, dict) and currency in result:
            currency_data = result[currency]
            
            return {
                'symbol': f"{currency}/IRT",
                'lastPrice': currency_data.get('stats', {}).get('lastTradePrice'),
                'priceChange': currency_data.get('stats', {}).get('dayChangeAmount'),
                'priceChangePercent': currency_data.get('stats', {}).get('dayChangePercent'),
                'volume': currency_data.get('stats', {}).get('dayTradedAmount'),
                'high': currency_data.get('stats', {}).get('dayHighPrice'),
                'low': currency_data.get('stats', {}).get('dayLowPrice'),
                'bid': currency_data.get('stats', {}).get('dayOpenPrice'),
                'ask': currency_data.get('stats', {}).get('dayClosePrice'),
            }
        
        return None
    
    async def get_all_tickers(self) -> Optional[List[Dict[str, Any]]]:
        """Get all ticker data"""
        result = await self._request('GET', '/v1/currencies/stats')
        
        if result and isinstance(result, dict):
            tickers = []
            
            for currency, data in result.items():
                if isinstance(data, dict) and 'stats' in data:
                    stats = data['stats']
                    ticker = {
                        'symbol': f"{currency}/IRT",
                        'lastPrice': stats.get('lastTradePrice'),
                        'priceChange': stats.get('dayChangeAmount'),
                        'priceChangePercent': stats.get('dayChangePercent'),
                        'volume': stats.get('dayTradedAmount'),
                        'high': stats.get('dayHighPrice'),
                        'low': stats.get('dayLowPrice'),
                    }
                    tickers.append(ticker)
            
            return tickers
        
        return None
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance"""
        result = await self._request('GET', '/v1/account/balances', signed=True)
        
        if result and isinstance(result, dict):
            balance = {}
            
            # Wallex balance format may vary - adjust based on actual API response
            if 'balances' in result:
                for item in result['balances']:
                    currency = item.get('currency', '').upper()
                    available = float(item.get('value', 0))
                    locked = float(item.get('frozen', 0))
                    
                    if available > 0 or locked > 0:
                        balance[currency] = {
                            'free': available,
                            'locked': locked, 
                            'total': available + locked
                        }
            
            return balance
        
        return None
    
    async def get_orderbook(self, symbol: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get order book for symbol"""
        currency = symbol.replace('/IRT', '').replace('/TMN', '').upper()
        
        result = await self._request('GET', f'/v1/depth', {
            'symbol': currency,
            'type': 'all'
        })
        
        if result:
            return {
                'symbol': symbol,
                'bids': result.get('buy', []),
                'asks': result.get('sell', [])
            }
        
        return None
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a new order"""
        currency = symbol.replace('/IRT', '').replace('/TMN', '').upper()
        
        params = {
            'type': side.lower(),  # 'buy' or 'sell'
            'srcCurrency': 'IRT' if side.lower() == 'buy' else currency,
            'dstCurrency': currency if side.lower() == 'buy' else 'IRT',
            'amount': str(quantity)
        }
        
        if order_type.upper() == 'LIMIT' and price:
            params['price'] = str(price)
        
        return await self._request('POST', '/v1/account/orders', params, signed=True)
    
    async def get_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order status"""
        return await self._request('GET', f'/v1/account/orders/{order_id}', signed=True)
    
    async def cancel_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Cancel an active order"""
        return await self._request('DELETE', f'/v1/account/orders/{order_id}', signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get all open orders"""
        params = {'status': 'active'}
        if symbol:
            params['symbol'] = symbol.replace('/IRT', '').replace('/TMN', '').upper()
        
        return await self._request('GET', '/v1/account/orders', params, signed=True)
    
    async def get_order_history(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get order history"""
        params = {
            'symbol': symbol.replace('/IRT', '').replace('/TMN', '').upper(),
            'status': 'done',
            'limit': limit
        }
        
        return await self._request('GET', '/v1/account/orders', params, signed=True)
    
    async def get_trade_history(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get trade history"""
        params = {
            'symbol': symbol.replace('/IRT', '').replace('/TMN', '').upper(),
            'limit': limit
        }
        
        return await self._request('GET', '/v1/account/trades', params, signed=True)
    
    async def get_currencies(self) -> Optional[Dict[str, Any]]:
        """Get supported currencies information"""
        return await self._request('GET', '/v1/currencies/stats')
    
    async def get_market_summary(self) -> Optional[Dict[str, Any]]:
        """Get market summary for all currencies"""
        currencies = await self.get_currencies()
        
        if currencies:
            summary = {
                'total_currencies': len(currencies),
                'total_volume_irt': 0,
                'top_volume': None,
                'top_gainer': None,
                'top_loser': None
            }
            
            max_change = -100.0
            min_change = 100.0
            max_volume = 0
            
            for currency, data in currencies.items():
                if isinstance(data, dict) and 'stats' in data:
                    stats = data['stats']
                    
                    volume = float(stats.get('dayTradedAmount', 0))
                    change_percent = float(stats.get('dayChangePercent', 0))
                    
                    summary['total_volume_irt'] += volume
                    
                    if volume > max_volume:
                        max_volume = volume
                        summary['top_volume'] = {'currency': currency, 'volume': volume}
                    
                    if change_percent > max_change:
                        max_change = change_percent
                        summary['top_gainer'] = {'currency': currency, 'change': change_percent}
                    
                    if change_percent < min_change:
                        min_change = change_percent
                        summary['top_loser'] = {'currency': currency, 'change': change_percent}
            
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