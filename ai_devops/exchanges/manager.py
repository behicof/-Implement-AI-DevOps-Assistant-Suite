"""
Exchange manager for handling multiple cryptocurrency exchanges
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime

from .binance import BinanceClient
from .wallex import WallexClient  
from .bitpin import BitpinClient
from .nobitex import NobitexClient

logger = logging.getLogger(__name__)


class ExchangeManager:
    """Manages multiple cryptocurrency exchange connections and operations"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.exchanges: Dict[str, Any] = {}
        self.exchange_configs = self._load_exchange_configs()
        self._initialize_exchanges()
    
    def _load_exchange_configs(self) -> Dict[str, Any]:
        """Load exchange configurations from JSON file"""
        config_file = Path(__file__).parent.parent / "config" / "exchanges.json"
        
        with open(config_file, "r") as f:
            return json.load(f)
    
    def _initialize_exchanges(self):
        """Initialize configured exchanges"""
        credentials = self.config.get("credentials", {})
        
        # International exchanges
        if "binance" in credentials:
            try:
                self.exchanges["binance"] = BinanceClient(
                    api_key=credentials["binance"]["api_key"],
                    api_secret=credentials["binance"]["api_secret"],
                    testnet=credentials["binance"].get("sandbox", False)
                )
                logger.info("Binance client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Binance: {e}")
        
        # Iranian exchanges
        iranian_exchanges = {
            "wallex": WallexClient,
            "bitpin": BitpinClient,
            "nobitex": NobitexClient
        }
        
        for exchange_name, client_class in iranian_exchanges.items():
            if exchange_name in credentials:
                try:
                    self.exchanges[exchange_name] = client_class(
                        api_key=credentials[exchange_name]["api_key"],
                        api_secret=credentials[exchange_name]["api_secret"]
                    )
                    logger.info(f"{exchange_name.title()} client initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize {exchange_name}: {e}")
    
    async def list_exchanges(self) -> List[Dict[str, Any]]:
        """List all configured exchanges with their status"""
        exchange_list = []
        
        for exchange_name, client in self.exchanges.items():
            try:
                # Test connection
                connected = await self._test_exchange_connection(exchange_name)
                
                exchange_info = {
                    "name": exchange_name,
                    "display_name": self.exchange_configs["exchanges"][exchange_name]["name"],
                    "type": self.exchange_configs["exchanges"][exchange_name]["type"],
                    "connected": connected,
                    "status": "Connected" if connected else "Disconnected",
                    "features": self.exchange_configs["exchanges"][exchange_name]["supported_features"]
                }
                
                if connected:
                    # Get additional info if connected
                    balance = await self.get_balance(exchange_name)
                    if balance:
                        exchange_info["total_balance_usd"] = self._calculate_total_balance_usd(balance)
                
            except Exception as e:
                exchange_info = {
                    "name": exchange_name,
                    "connected": False,
                    "status": f"Error: {str(e)}",
                    "error": str(e)
                }
            
            exchange_list.append(exchange_info)
        
        return exchange_list
    
    async def test_connection(self, exchange_name: str) -> bool:
        """Test connection to specific exchange"""
        return await self._test_exchange_connection(exchange_name)
    
    async def _test_exchange_connection(self, exchange_name: str) -> bool:
        """Internal method to test exchange connection"""
        if exchange_name not in self.exchanges:
            return False
        
        try:
            client = self.exchanges[exchange_name]
            
            if hasattr(client, 'ping'):
                result = await client.ping()
                return result is not None
            else:
                # Fallback: try to get server time or balance
                if hasattr(client, 'get_server_time'):
                    result = await client.get_server_time()
                    return result is not None
                elif hasattr(client, 'get_balance'):
                    result = await client.get_balance()
                    return result is not None
            
            return False
            
        except Exception as e:
            logger.error(f"Connection test failed for {exchange_name}: {e}")
            return False
    
    async def get_balance(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """Get balance from specific exchange"""
        if exchange_name not in self.exchanges:
            return None
        
        try:
            client = self.exchanges[exchange_name]
            return await client.get_balance()
        except Exception as e:
            logger.error(f"Failed to get balance from {exchange_name}: {e}")
            return None
    
    async def get_all_balances(self) -> Dict[str, Any]:
        """Get balances from all connected exchanges"""
        balances = {}
        
        tasks = []
        for exchange_name in self.exchanges:
            task = asyncio.create_task(
                self.get_balance(exchange_name), 
                name=f"balance_{exchange_name}"
            )
            tasks.append((exchange_name, task))
        
        for exchange_name, task in tasks:
            try:
                balance = await task
                if balance:
                    balances[exchange_name] = balance
            except Exception as e:
                logger.error(f"Failed to get balance from {exchange_name}: {e}")
                balances[exchange_name] = {"error": str(e)}
        
        return balances
    
    async def get_ticker(self, exchange_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get ticker data for symbol from specific exchange"""
        if exchange_name not in self.exchanges:
            return None
        
        try:
            client = self.exchanges[exchange_name]
            return await client.get_ticker(symbol)
        except Exception as e:
            logger.error(f"Failed to get ticker {symbol} from {exchange_name}: {e}")
            return None
    
    async def get_all_tickers(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get ticker data for symbols from all exchanges"""
        tickers = {}
        
        for exchange_name in self.exchanges:
            tickers[exchange_name] = {}
            
            for symbol in symbols:
                try:
                    ticker = await self.get_ticker(exchange_name, symbol)
                    if ticker:
                        tickers[exchange_name][symbol] = ticker
                except Exception as e:
                    logger.error(f"Failed to get {symbol} from {exchange_name}: {e}")
                    tickers[exchange_name][symbol] = {"error": str(e)}
        
        return tickers
    
    async def get_exchange_info(self, exchange_name: str) -> Optional[Dict[str, Any]]:
        """Get exchange information and trading rules"""
        if exchange_name not in self.exchanges:
            return None
        
        try:
            client = self.exchanges[exchange_name]
            
            # Get basic exchange info
            info = {
                "name": exchange_name,
                "display_name": self.exchange_configs["exchanges"][exchange_name]["name"],
                "type": self.exchange_configs["exchanges"][exchange_name]["type"],
                "features": self.exchange_configs["exchanges"][exchange_name]["supported_features"],
                "rate_limits": self.exchange_configs["exchanges"][exchange_name]["rate_limits"],
                "connected": await self._test_exchange_connection(exchange_name)
            }
            
            # Get exchange-specific info if available
            if hasattr(client, 'get_exchange_info'):
                exchange_data = await client.get_exchange_info()
                if exchange_data:
                    info.update(exchange_data)
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get exchange info for {exchange_name}: {e}")
            return {"name": exchange_name, "error": str(e)}
    
    async def place_order(self, exchange_name: str, symbol: str, side: str, 
                         order_type: str, quantity: float, price: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Place order on specific exchange"""
        if exchange_name not in self.exchanges:
            return None
        
        try:
            client = self.exchanges[exchange_name]
            
            if hasattr(client, 'place_order'):
                return await client.place_order(
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price
                )
            else:
                logger.warning(f"Trading not supported for {exchange_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to place order on {exchange_name}: {e}")
            return {"error": str(e)}
    
    async def get_order_status(self, exchange_name: str, order_id: str, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order status from specific exchange"""
        if exchange_name not in self.exchanges:
            return None
        
        try:
            client = self.exchanges[exchange_name]
            
            if hasattr(client, 'get_order'):
                return await client.get_order(order_id, symbol)
            else:
                logger.warning(f"Order tracking not supported for {exchange_name}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get order status from {exchange_name}: {e}")
            return {"error": str(e)}
    
    async def remove_exchange(self, exchange_name: str) -> bool:
        """Remove exchange from manager"""
        if exchange_name in self.exchanges:
            try:
                client = self.exchanges[exchange_name]
                
                # Close any open connections
                if hasattr(client, 'close'):
                    await client.close()
                
                del self.exchanges[exchange_name]
                logger.info(f"Removed {exchange_name} from exchange manager")
                return True
                
            except Exception as e:
                logger.error(f"Failed to remove {exchange_name}: {e}")
                return False
        
        return False
    
    def _calculate_total_balance_usd(self, balance: Dict[str, Any]) -> float:
        """Calculate total balance in USD (simplified)"""
        # This is a simplified calculation
        # In a real implementation, you'd need current prices
        total_usd = 0.0
        
        if isinstance(balance, dict):
            for asset, amount in balance.items():
                if isinstance(amount, (int, float)):
                    # Simplified conversion - in reality you'd need exchange rates
                    if asset.upper() in ["USD", "USDT", "USDC", "BUSD"]:
                        total_usd += float(amount)
                    elif asset.upper() == "BTC":
                        total_usd += float(amount) * 50000  # Approximate BTC price
                    elif asset.upper() == "ETH":
                        total_usd += float(amount) * 3000   # Approximate ETH price
        
        return total_usd
    
    async def close_all(self):
        """Close all exchange connections"""
        for exchange_name in list(self.exchanges.keys()):
            await self.remove_exchange(exchange_name)
    
    def get_supported_exchanges(self) -> List[str]:
        """Get list of supported exchange names"""
        return list(self.exchange_configs["exchanges"].keys())
    
    def get_iranian_exchanges(self) -> List[str]:
        """Get list of Iranian exchanges"""
        return [
            name for name, config in self.exchange_configs["exchanges"].items()
            if config["type"] == "iranian"
        ]
    
    def get_international_exchanges(self) -> List[str]:
        """Get list of international exchanges"""
        return [
            name for name, config in self.exchange_configs["exchanges"].items()
            if config["type"] == "international"
        ]