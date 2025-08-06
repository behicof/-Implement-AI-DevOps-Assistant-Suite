"""
Binance exchange client implementation
"""

import asyncio
import logging
import hashlib
import hmac
import time
from typing import Dict, Any, Optional, List
from urllib.parse import urlencode

import aiohttp
import json

logger = logging.getLogger(__name__)


class BinanceClient:
    """Binance exchange client with async support"""
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            self.base_url = "https://testnet.binance.vision"
            self.ws_url = "wss://testnet.binance.vision/ws"
        else:
            self.base_url = "https://api.binance.com"
            self.ws_url = "wss://stream.binance.com:9443/ws"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(10)  # Rate limiting
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """Generate HMAC SHA256 signature for Binance API"""
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                      signed: bool = False) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Binance API"""
        async with self._rate_limiter:
            url = f"{self.base_url}{endpoint}"
            headers = {}
            
            if params is None:
                params = {}
            
            if signed:
                # Add timestamp
                params['timestamp'] = int(time.time() * 1000)
                # Generate signature
                params['signature'] = self._generate_signature(params)
                headers['X-MBX-APIKEY'] = self.api_key
            
            session = await self._get_session()
            
            try:
                if method.upper() == 'GET':
                    async with session.get(url, params=params, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.error(f"Binance API error: {response.status} - {await response.text()}")
                            return None
                            
                elif method.upper() == 'POST':
                    async with session.post(url, data=params, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        else:
                            logger.error(f"Binance API error: {response.status} - {await response.text()}")
                            return None
                            
            except asyncio.TimeoutError:
                logger.error(f"Timeout for Binance API request: {endpoint}")
                return None
            except Exception as e:
                logger.error(f"Binance API request failed: {e}")
                return None
    
    async def ping(self) -> Optional[Dict[str, Any]]:
        """Test connectivity to Binance API"""
        return await self._request('GET', '/api/v3/ping')
    
    async def get_server_time(self) -> Optional[Dict[str, Any]]:
        """Get server time from Binance"""
        return await self._request('GET', '/api/v3/time')
    
    async def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Get exchange trading rules and symbol information"""
        return await self._request('GET', '/api/v3/exchangeInfo')
    
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get 24hr ticker price change statistics"""
        params = {'symbol': symbol.upper()}
        return await self._request('GET', '/api/v3/ticker/24hr', params)
    
    async def get_all_tickers(self) -> Optional[List[Dict[str, Any]]]:
        """Get all symbol ticker data"""
        return await self._request('GET', '/api/v3/ticker/24hr')
    
    async def get_orderbook(self, symbol: str, limit: int = 100) -> Optional[Dict[str, Any]]:
        """Get order book for symbol"""
        params = {'symbol': symbol.upper(), 'limit': limit}
        return await self._request('GET', '/api/v3/depth', params)
    
    async def get_recent_trades(self, symbol: str, limit: int = 500) -> Optional[List[Dict[str, Any]]]:
        """Get recent trades for symbol"""
        params = {'symbol': symbol.upper(), 'limit': limit}
        return await self._request('GET', '/api/v3/trades', params)
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance"""
        result = await self._request('GET', '/api/v3/account', signed=True)
        
        if result and 'balances' in result:
            # Convert to simplified format
            balance = {}
            for item in result['balances']:
                asset = item['asset']
                free = float(item['free'])
                locked = float(item['locked'])
                total = free + locked
                
                if total > 0:  # Only include non-zero balances
                    balance[asset] = {
                        'free': free,
                        'locked': locked,
                        'total': total
                    }
            
            return balance
        
        return None
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: Optional[float] = None, 
                         time_in_force: str = 'GTC') -> Optional[Dict[str, Any]]:
        """Place a new order"""
        params = {
            'symbol': symbol.upper(),
            'side': side.upper(),
            'type': order_type.upper(),
            'quantity': str(quantity),
        }
        
        if order_type.upper() == 'LIMIT':
            if price is None:
                raise ValueError("Price is required for LIMIT orders")
            params['price'] = str(price)
            params['timeInForce'] = time_in_force
        
        return await self._request('POST', '/api/v3/order', params, signed=True)
    
    async def get_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order status"""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        return await self._request('GET', '/api/v3/order', params, signed=True)
    
    async def cancel_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Cancel an active order"""
        params = {
            'symbol': symbol.upper(),
            'orderId': order_id
        }
        return await self._request('DELETE', '/api/v3/order', params, signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get all open orders"""
        params = {}
        if symbol:
            params['symbol'] = symbol.upper()
        
        return await self._request('GET', '/api/v3/openOrders', params, signed=True)
    
    async def get_order_history(self, symbol: str, limit: int = 500) -> Optional[List[Dict[str, Any]]]:
        """Get order history for symbol"""
        params = {
            'symbol': symbol.upper(),
            'limit': limit
        }
        return await self._request('GET', '/api/v3/allOrders', params, signed=True)
    
    async def get_trade_history(self, symbol: str, limit: int = 500) -> Optional[List[Dict[str, Any]]]:
        """Get trade history for symbol"""
        params = {
            'symbol': symbol.upper(),
            'limit': limit
        }
        return await self._request('GET', '/api/v3/myTrades', params, signed=True)
    
    async def get_deposit_history(self, coin: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get deposit history"""
        params = {}
        if coin:
            params['coin'] = coin.upper()
        
        return await self._request('GET', '/sapi/v1/capital/deposit/hisrec', params, signed=True)
    
    async def get_withdraw_history(self, coin: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get withdrawal history"""
        params = {}
        if coin:
            params['coin'] = coin.upper()
        
        return await self._request('GET', '/sapi/v1/capital/withdraw/history', params, signed=True)
    
    async def get_klines(self, symbol: str, interval: str, limit: int = 500) -> Optional[List[List]]:
        """Get kline/candlestick data"""
        params = {
            'symbol': symbol.upper(),
            'interval': interval,
            'limit': limit
        }
        return await self._request('GET', '/api/v3/klines', params)
    
    async def get_24hr_stats(self) -> Optional[Dict[str, Any]]:
        """Get 24hr ticker price change statistics for all symbols"""
        tickers = await self.get_all_tickers()
        
        if tickers:
            stats = {
                'total_symbols': len(tickers),
                'gainers': 0,
                'losers': 0,
                'volume_24h': 0.0,
                'top_gainer': None,
                'top_loser': None
            }
            
            max_change = -100.0
            min_change = 100.0
            
            for ticker in tickers:
                change_percent = float(ticker.get('priceChangePercent', 0))
                volume = float(ticker.get('volume', 0))
                
                if change_percent > 0:
                    stats['gainers'] += 1
                elif change_percent < 0:
                    stats['losers'] += 1
                
                stats['volume_24h'] += volume
                
                if change_percent > max_change:
                    max_change = change_percent
                    stats['top_gainer'] = ticker
                
                if change_percent < min_change:
                    min_change = change_percent
                    stats['top_loser'] = ticker
            
            return stats
        
        return None
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            asyncio.create_task(self.session.close())