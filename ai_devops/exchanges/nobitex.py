"""
Nobitex exchange client implementation (Iranian exchange)
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


class NobitexClient:
    """Nobitex exchange client (Iranian exchange) with async support"""
    
    def __init__(self, api_key: str, api_secret: str, username: Optional[str] = None, password: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.username = username
        self.password = password
        self.base_url = "https://api.nobitex.ir"
        
        self.session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = asyncio.Semaphore(8)  # More generous rate limiting
        self._auth_token: Optional[str] = None
    
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
    
    async def _authenticate(self) -> bool:
        """Authenticate with Nobitex API"""
        if self.username and self.password:
            params = {
                'username': self.username,
                'password': self.password
            }
            
            result = await self._request('POST', '/auth/login/', params)
            
            if result and 'token' in result:
                self._auth_token = result['token']
                return True
        
        return False
    
    def _generate_signature(self, params: Dict[str, Any], timestamp: str) -> str:
        """Generate HMAC SHA256 signature for Nobitex API"""
        # Nobitex may use different signature method - adjust based on documentation
        message = f"{timestamp}{json.dumps(params, separators=(',', ':'), sort_keys=True)}"
        return hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    async def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, 
                      signed: bool = False) -> Optional[Dict[str, Any]]:
        """Make HTTP request to Nobitex API"""
        async with self._rate_limiter:
            url = f"{self.base_url}{endpoint}"
            headers = {}
            
            if params is None:
                params = {}
            
            if signed:
                # Try to authenticate if we don't have a token
                if not self._auth_token:
                    await self._authenticate()
                
                if self._auth_token:
                    headers['Authorization'] = f'Token {self._auth_token}'
                else:
                    # Fallback to API key authentication
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
                            logger.error(f"Nobitex API error: {response.status} - {error_text}")
                            return None
                            
                elif method.upper() == 'POST':
                    async with session.post(url, json=params, headers=headers) as response:
                        if response.status in [200, 201]:
                            return await response.json()
                        else:
                            error_text = await response.text()
                            logger.error(f"Nobitex API error: {response.status} - {error_text}")
                            return None
                            
            except asyncio.TimeoutError:
                logger.error(f"Timeout for Nobitex API request: {endpoint}")
                return None
            except Exception as e:
                logger.error(f"Nobitex API request failed: {e}")
                return None
    
    async def get_server_time(self) -> Optional[Dict[str, Any]]:
        """Get server time from Nobitex"""
        # Use market stats as health check
        result = await self._request('GET', '/market/stats')
        return {'server_time': int(time.time() * 1000)} if result else None
    
    async def get_exchange_info(self) -> Optional[Dict[str, Any]]:
        """Get exchange information and trading rules"""
        result = await self._request('GET', '/market/stats')
        
        if result:
            return {
                'name': 'Nobitex',
                'type': 'iranian',
                'base_currency': 'IRT',  # Iranian Rial Toman
                'supported_currencies': list(result.keys()) if isinstance(result, dict) else [],
                'trading_features': ['spot_trading', 'rial_gateway', 'instant_trading']
            }
        
        return None
    
    async def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for symbol"""
        # Nobitex uses different symbol format
        currency = symbol.replace('/IRT', '').replace('/TMN', '').lower()
        
        result = await self._request('GET', '/market/stats', {'srcCurrency': currency, 'dstCurrency': 'rls'})
        
        if result and isinstance(result, dict) and 'stats' in result:
            stats = result['stats'].get(f'{currency}-rls', {})
            
            return {
                'symbol': f"{currency.upper()}/IRT",
                'lastPrice': stats.get('latest'),
                'priceChange': stats.get('dayChange'),
                'volume': stats.get('volumeSrc'),
                'high': stats.get('dayHigh'),
                'low': stats.get('dayLow')
            }
        
        return None
    
    async def get_all_tickers(self) -> Optional[List[Dict[str, Any]]]:
        """Get all ticker data"""
        result = await self._request('GET', '/market/stats')
        
        if result and isinstance(result, dict) and 'stats' in result:
            tickers = []
            
            for pair, stats in result['stats'].items():
                if isinstance(stats, dict):
                    # Parse currency pair (e.g., 'btc-rls' -> 'BTC/IRT')
                    if '-' in pair:
                        base, quote = pair.split('-', 1)
                        symbol = f"{base.upper()}/IRT"
                        
                        ticker = {
                            'symbol': symbol,
                            'lastPrice': stats.get('latest'),
                            'priceChange': stats.get('dayChange'),
                            'volume': stats.get('volumeSrc'),
                            'high': stats.get('dayHigh'),
                            'low': stats.get('dayLow')
                        }
                        tickers.append(ticker)
            
            return tickers
        
        return None
    
    async def get_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance"""
        result = await self._request('GET', '/users/wallets/list', signed=True)
        
        if result and 'wallets' in result:
            balance = {}
            
            for wallet in result['wallets']:
                if isinstance(wallet, dict):
                    currency = wallet.get('currency', '').upper()
                    available = float(wallet.get('balance', 0))
                    blocked = float(wallet.get('blocked', 0))
                    
                    # Convert RLS to IRT (1 IRT = 10 RLS)
                    if currency == 'RLS':
                        currency = 'IRT'
                        available /= 10
                        blocked /= 10
                    
                    if available > 0 or blocked > 0:
                        balance[currency] = {
                            'free': available,
                            'locked': blocked,
                            'total': available + blocked
                        }
            
            return balance
        
        return None
    
    async def get_orderbook(self, symbol: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get order book for symbol"""
        currency = symbol.replace('/IRT', '').replace('/TMN', '').lower()
        
        result = await self._request('GET', '/v2/orderbook', {
            'symbol': f'{currency}rls'
        })
        
        if result:
            return {
                'symbol': symbol,
                'bids': result.get('bids', []),
                'asks': result.get('asks', [])
            }
        
        return None
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         quantity: float, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place a new order"""
        currency = symbol.replace('/IRT', '').replace('/TMN', '').lower()
        
        params = {
            'type': side.lower(),  # 'buy' or 'sell'
            'srcCurrency': currency if side.lower() == 'sell' else 'rls',
            'dstCurrency': 'rls' if side.lower() == 'sell' else currency,
            'amount': str(quantity)
        }
        
        if order_type.upper() == 'LIMIT' and price:
            params['price'] = str(price * 10)  # Convert IRT to RLS
        
        return await self._request('POST', '/market/orders/add', params, signed=True)
    
    async def get_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order status"""
        params = {'id': order_id}
        return await self._request('GET', '/market/orders/status', params, signed=True)
    
    async def cancel_order(self, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Cancel an active order"""
        params = {'order': order_id}
        return await self._request('POST', '/market/orders/cancel-old', params, signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """Get all open orders"""
        params = {}
        if symbol:
            currency = symbol.replace('/IRT', '').replace('/TMN', '').lower()
            params['symbol'] = f'{currency}rls'
        
        return await self._request('GET', '/market/orders/list', params, signed=True)
    
    async def get_order_history(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get order history"""
        currency = symbol.replace('/IRT', '').replace('/TMN', '').lower()
        
        params = {
            'symbol': f'{currency}rls',
            'limit': limit,
            'status': 'done'
        }
        
        return await self._request('GET', '/market/orders/list', params, signed=True)
    
    async def get_trade_history(self, symbol: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """Get trade history"""
        currency = symbol.replace('/IRT', '').replace('/TMN', '').lower()
        
        params = {
            'symbol': f'{currency}rls',
            'limit': limit
        }
        
        return await self._request('GET', '/market/trades/list', params, signed=True)
    
    async def get_global_stats(self) -> Optional[Dict[str, Any]]:
        """Get global market statistics"""
        return await self._request('GET', '/market/global-stats')
    
    async def get_profile(self) -> Optional[Dict[str, Any]]:
        """Get user profile information"""
        return await self._request('GET', '/users/profile', signed=True)
    
    async def get_deposit_addresses(self) -> Optional[Dict[str, Any]]:
        """Get cryptocurrency deposit addresses"""
        return await self._request('GET', '/users/wallets/generate-address', signed=True)
    
    async def get_withdrawals(self) -> Optional[List[Dict[str, Any]]]:
        """Get withdrawal history"""
        return await self._request('GET', '/users/wallets/withdraws/list', signed=True)
    
    async def get_deposits(self) -> Optional[List[Dict[str, Any]]]:
        """Get deposit history"""
        return await self._request('GET', '/users/wallets/deposits/list', signed=True)
    
    async def get_market_summary(self) -> Optional[Dict[str, Any]]:
        """Get market summary with Iranian market focus"""
        stats = await self._request('GET', '/market/stats')
        global_stats = await self.get_global_stats()
        
        if stats and 'stats' in stats:
            summary = {
                'total_pairs': len(stats['stats']),
                'total_volume_rls': 0,
                'gainers': 0,
                'losers': 0,
                'top_gainer': None,
                'top_loser': None
            }
            
            max_change = -100.0
            min_change = 100.0
            
            for pair, data in stats['stats'].items():
                if isinstance(data, dict):
                    change = float(data.get('dayChange', '0').replace('%', ''))
                    volume = float(data.get('volumeDst', 0))
                    
                    summary['total_volume_rls'] += volume
                    
                    if change > 0:
                        summary['gainers'] += 1
                    elif change < 0:
                        summary['losers'] += 1
                    
                    if change > max_change:
                        max_change = change
                        summary['top_gainer'] = {'pair': pair, 'change': change}
                    
                    if change < min_change:
                        min_change = change
                        summary['top_loser'] = {'pair': pair, 'change': change}
            
            # Add global stats if available
            if global_stats:
                summary['global_stats'] = global_stats
            
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