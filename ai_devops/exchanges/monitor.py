"""
Exchange monitoring system for real-time tracking
"""

import asyncio
import logging
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

from .manager import ExchangeManager

logger = logging.getLogger(__name__)


@dataclass
class ExchangeStatus:
    """Exchange status information"""
    name: str
    connected: bool
    last_update: datetime
    response_time_ms: float
    error_count: int
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PriceAlert:
    """Price alert configuration"""
    symbol: str
    exchange: str
    threshold_percent: float
    last_price: Optional[float] = None
    triggered: bool = False
    created_at: datetime = datetime.now()


@dataclass
class MarketData:
    """Market data snapshot"""
    symbol: str
    exchange: str
    price: float
    volume: float
    change_24h: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class ExchangeMonitor:
    """Real-time exchange monitoring system"""
    
    def __init__(self, config: Dict[str, Any], exchanges: List[str]):
        self.config = config
        self.exchange_names = exchanges
        self.exchange_manager = ExchangeManager(config)
        
        # Monitoring state
        self.exchange_status: Dict[str, ExchangeStatus] = {}
        self.market_data: Dict[str, List[MarketData]] = {}
        self.price_alerts: List[PriceAlert] = []
        self.callbacks: List[Callable] = []
        
        # Configuration
        self.update_interval = config.get('update_interval', 30)  # seconds
        self.max_data_points = config.get('max_data_points', 1000)
        self.alert_threshold = config.get('price_alert_threshold', 5.0)  # percentage
        
        # Monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
    
    def add_callback(self, callback: Callable):
        """Add callback function for monitoring events"""
        self.callbacks.append(callback)
    
    def add_price_alert(self, symbol: str, exchange: str, threshold_percent: float):
        """Add price alert for symbol on exchange"""
        alert = PriceAlert(
            symbol=symbol,
            exchange=exchange, 
            threshold_percent=threshold_percent
        )
        self.price_alerts.append(alert)
        logger.info(f"Added price alert: {symbol} on {exchange} at {threshold_percent}%")
    
    async def start_monitoring(self, interval: Optional[int] = None):
        """Start continuous monitoring of exchanges"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Monitoring already running")
            return
        
        if interval:
            self.update_interval = interval
        
        logger.info(f"Starting exchange monitoring for {len(self.exchange_names)} exchanges")
        
        self._stop_event.clear()
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        return self._monitoring_task
    
    async def stop_monitoring(self):
        """Stop continuous monitoring"""
        logger.info("Stopping exchange monitoring")
        
        self._stop_event.set()
        
        if self._monitoring_task:
            try:
                await asyncio.wait_for(self._monitoring_task, timeout=10)
            except asyncio.TimeoutError:
                logger.warning("Monitoring task didn't stop gracefully, canceling")
                self._monitoring_task.cancel()
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        logger.info(f"Exchange monitoring loop started, interval: {self.update_interval}s")
        
        while not self._stop_event.is_set():
            try:
                start_time = time.time()
                
                # Update exchange statuses
                await self._update_exchange_statuses()
                
                # Collect market data
                await self._collect_market_data()
                
                # Check price alerts
                await self._check_price_alerts()
                
                # Notify callbacks
                await self._notify_callbacks()
                
                # Calculate sleep time
                elapsed = time.time() - start_time
                sleep_time = max(0, self.update_interval - elapsed)
                
                logger.debug(f"Monitoring cycle completed in {elapsed:.2f}s, sleeping {sleep_time:.2f}s")
                
                # Wait for next cycle or stop signal
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=sleep_time)
                    break  # Stop signal received
                except asyncio.TimeoutError:
                    continue  # Timeout, continue monitoring
                    
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(5)  # Brief pause on error
    
    async def _update_exchange_statuses(self):
        """Update connection status for all exchanges"""
        tasks = []
        
        for exchange_name in self.exchange_names:
            task = asyncio.create_task(
                self._check_exchange_status(exchange_name),
                name=f"status_{exchange_name}"
            )
            tasks.append(task)
        
        # Wait for all status checks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            exchange_name = self.exchange_names[i]
            
            if isinstance(result, Exception):
                logger.error(f"Status check failed for {exchange_name}: {result}")
                # Create error status
                self.exchange_status[exchange_name] = ExchangeStatus(
                    name=exchange_name,
                    connected=False,
                    last_update=datetime.now(),
                    response_time_ms=0,
                    error_count=self.exchange_status.get(exchange_name, ExchangeStatus(
                        exchange_name, False, datetime.now(), 0, 0
                    )).error_count + 1,
                    last_error=str(result)
                )
            elif result:
                self.exchange_status[exchange_name] = result
    
    async def _check_exchange_status(self, exchange_name: str) -> ExchangeStatus:
        """Check status of individual exchange"""
        start_time = time.time()
        
        try:
            # Test connection
            connected = await self.exchange_manager.test_connection(exchange_name)
            response_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Get previous status for error count
            prev_status = self.exchange_status.get(exchange_name)
            error_count = prev_status.error_count if prev_status and not connected else 0
            
            return ExchangeStatus(
                name=exchange_name,
                connected=connected,
                last_update=datetime.now(),
                response_time_ms=response_time,
                error_count=error_count,
                last_error=None if connected else "Connection test failed"
            )
            
        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            prev_status = self.exchange_status.get(exchange_name)
            error_count = (prev_status.error_count if prev_status else 0) + 1
            
            return ExchangeStatus(
                name=exchange_name,
                connected=False,
                last_update=datetime.now(),
                response_time_ms=response_time,
                error_count=error_count,
                last_error=str(e)
            )
    
    async def _collect_market_data(self):
        """Collect market data from all exchanges"""
        # Define symbols to monitor
        symbols = self._get_monitored_symbols()
        
        if not symbols:
            return
        
        tasks = []
        for exchange_name in self.exchange_names:
            for symbol in symbols:
                task = asyncio.create_task(
                    self._get_market_data(exchange_name, symbol),
                    name=f"data_{exchange_name}_{symbol}"
                )
                tasks.append(task)
        
        # Collect all market data
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in results:
            if isinstance(result, MarketData):
                key = f"{result.exchange}_{result.symbol}"
                
                if key not in self.market_data:
                    self.market_data[key] = []
                
                # Add new data point
                self.market_data[key].append(result)
                
                # Keep only recent data points
                if len(self.market_data[key]) > self.max_data_points:
                    self.market_data[key] = self.market_data[key][-self.max_data_points:]
            
            elif isinstance(result, Exception):
                logger.debug(f"Market data collection failed: {result}")
    
    def _get_monitored_symbols(self) -> List[str]:
        """Get list of symbols to monitor"""
        # Default symbols for monitoring
        default_symbols = [
            'BTC/USDT', 'ETH/USDT', 'BNB/USDT',  # International
            'BTC/IRT', 'ETH/IRT', 'USDT/IRT'     # Iranian
        ]
        
        # Add symbols from price alerts
        alert_symbols = [alert.symbol for alert in self.price_alerts]
        
        # Combine and deduplicate
        all_symbols = list(set(default_symbols + alert_symbols))
        
        return all_symbols
    
    async def _get_market_data(self, exchange_name: str, symbol: str) -> Optional[MarketData]:
        """Get market data for specific symbol from exchange"""
        try:
            ticker = await self.exchange_manager.get_ticker(exchange_name, symbol)
            
            if ticker:
                return MarketData(
                    symbol=symbol,
                    exchange=exchange_name,
                    price=float(ticker.get('lastPrice', 0)),
                    volume=float(ticker.get('volume', 0)),
                    change_24h=float(ticker.get('priceChangePercent', 0)),
                    timestamp=datetime.now()
                )
                
        except Exception as e:
            logger.debug(f"Failed to get {symbol} from {exchange_name}: {e}")
        
        return None
    
    async def _check_price_alerts(self):
        """Check price alerts and trigger notifications"""
        for alert in self.price_alerts:
            if alert.triggered:
                continue
            
            # Get current market data
            key = f"{alert.exchange}_{alert.symbol}"
            market_data = self.market_data.get(key, [])
            
            if not market_data:
                continue
            
            current_data = market_data[-1]
            current_price = current_data.price
            
            # Check if alert should trigger
            if alert.last_price:
                price_change_percent = abs(
                    (current_price - alert.last_price) / alert.last_price * 100
                )
                
                if price_change_percent >= alert.threshold_percent:
                    alert.triggered = True
                    
                    # Log alert
                    logger.warning(
                        f"Price alert triggered: {alert.symbol} on {alert.exchange} "
                        f"changed {price_change_percent:.2f}% (threshold: {alert.threshold_percent}%)"
                    )
                    
                    # Notify callbacks
                    await self._notify_alert(alert, current_data)
            
            # Update last price
            alert.last_price = current_price
    
    async def _notify_alert(self, alert: PriceAlert, market_data: MarketData):
        """Notify callbacks about triggered alert"""
        alert_data = {
            'type': 'price_alert',
            'alert': asdict(alert),
            'market_data': market_data.to_dict()
        }
        
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert_data)
                else:
                    callback(alert_data)
            except Exception as e:
                logger.error(f"Callback notification failed: {e}")
    
    async def _notify_callbacks(self):
        """Notify callbacks with current monitoring data"""
        if not self.callbacks:
            return
        
        # Prepare monitoring data
        monitoring_data = {
            'type': 'monitoring_update',
            'timestamp': datetime.now().isoformat(),
            'exchange_status': {
                name: status.to_dict() 
                for name, status in self.exchange_status.items()
            },
            'market_data': {
                key: [data.to_dict() for data in data_list[-10:]]  # Last 10 points
                for key, data_list in self.market_data.items()
            }
        }
        
        # Notify all callbacks
        for callback in self.callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(monitoring_data)
                else:
                    callback(monitoring_data)
            except Exception as e:
                logger.error(f"Callback notification failed: {e}")
    
    def get_exchange_status(self, exchange_name: str) -> Optional[ExchangeStatus]:
        """Get current status of exchange"""
        return self.exchange_status.get(exchange_name)
    
    def get_all_exchange_status(self) -> Dict[str, ExchangeStatus]:
        """Get status of all exchanges"""
        return self.exchange_status.copy()
    
    def get_market_data(self, exchange: str, symbol: str, limit: int = 100) -> List[MarketData]:
        """Get recent market data for symbol"""
        key = f"{exchange}_{symbol}"
        data = self.market_data.get(key, [])
        return data[-limit:] if limit else data
    
    def get_all_market_data(self) -> Dict[str, List[MarketData]]:
        """Get all market data"""
        return {
            key: data_list.copy() 
            for key, data_list in self.market_data.items()
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get monitoring summary"""
        total_exchanges = len(self.exchange_names)
        connected_exchanges = sum(
            1 for status in self.exchange_status.values() 
            if status.connected
        )
        
        total_alerts = len(self.price_alerts)
        triggered_alerts = sum(1 for alert in self.price_alerts if alert.triggered)
        
        # Calculate average response time
        response_times = [
            status.response_time_ms 
            for status in self.exchange_status.values()
            if status.connected
        ]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        return {
            'total_exchanges': total_exchanges,
            'connected_exchanges': connected_exchanges,
            'disconnected_exchanges': total_exchanges - connected_exchanges,
            'total_alerts': total_alerts,
            'triggered_alerts': triggered_alerts,
            'avg_response_time_ms': round(avg_response_time, 2),
            'total_market_data_points': sum(len(data) for data in self.market_data.values()),
            'monitoring_uptime_seconds': (
                datetime.now() - min(
                    (status.last_update for status in self.exchange_status.values()),
                    default=datetime.now()
                )
            ).total_seconds()
        }
    
    async def close(self):
        """Close monitoring and cleanup resources"""
        await self.stop_monitoring()
        await self.exchange_manager.close_all()
        
        logger.info("Exchange monitoring closed")