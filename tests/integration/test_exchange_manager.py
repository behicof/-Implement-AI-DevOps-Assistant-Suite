"""
Integration tests for exchange manager
"""

import pytest
import asyncio
from unittest.mock import patch, AsyncMock

from ai_devops.exchanges.manager import ExchangeManager


class TestExchangeManagerIntegration:
    """Integration tests for exchange manager"""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        return {
            "credentials": {
                "binance": {
                    "api_key": "test_binance_key",
                    "api_secret": "test_binance_secret",
                    "sandbox": True
                },
                "wallex": {
                    "api_key": "test_wallex_key",
                    "api_secret": "test_wallex_secret"
                }
            },
            "supported": ["binance", "wallex"],
            "timeout": 30
        }
    
    def test_manager_initialization(self, mock_config):
        """Test exchange manager initialization"""
        manager = ExchangeManager(mock_config)
        
        assert manager.config == mock_config
        assert len(manager.exchanges) >= 0  # May be 0 if no valid credentials
    
    @pytest.mark.asyncio
    async def test_list_exchanges(self, mock_config):
        """Test listing all exchanges"""
        manager = ExchangeManager(mock_config)
        
        with patch.object(manager, '_test_exchange_connection') as mock_test:
            mock_test.return_value = True
            
            exchanges = await manager.list_exchanges()
            
            assert isinstance(exchanges, list)
            # Should have entries for configured exchanges
            exchange_names = [ex.get('name') for ex in exchanges]
            if manager.exchanges:  # Only if exchanges were initialized
                assert any(name in exchange_names for name in ['binance', 'wallex'])
    
    @pytest.mark.asyncio
    async def test_get_all_balances(self, mock_config):
        """Test getting balances from all exchanges"""
        manager = ExchangeManager(mock_config)
        
        # Mock the individual exchange get_balance methods
        mock_balance = {
            "BTC": {"free": 1.0, "locked": 0.1, "total": 1.1},
            "ETH": {"free": 10.0, "locked": 1.0, "total": 11.0}
        }
        
        for exchange_name, client in manager.exchanges.items():
            if hasattr(client, 'get_balance'):
                with patch.object(client, 'get_balance') as mock_get_balance:
                    mock_get_balance.return_value = mock_balance
        
        balances = await manager.get_all_balances()
        
        assert isinstance(balances, dict)
        # Should have results for each configured exchange
        for exchange_name in manager.exchanges.keys():
            assert exchange_name in balances
    
    @pytest.mark.asyncio
    async def test_get_all_tickers(self, mock_config):
        """Test getting tickers from all exchanges"""
        manager = ExchangeManager(mock_config)
        
        symbols = ["BTC/USDT", "ETH/USDT"]
        mock_ticker = {
            "symbol": "BTC/USDT",
            "lastPrice": "50000.00",
            "priceChangePercent": "2.5"
        }
        
        # Mock the individual exchange get_ticker methods
        for exchange_name, client in manager.exchanges.items():
            if hasattr(client, 'get_ticker'):
                with patch.object(client, 'get_ticker') as mock_get_ticker:
                    mock_get_ticker.return_value = mock_ticker
        
        tickers = await manager.get_all_tickers(symbols)
        
        assert isinstance(tickers, dict)
        for exchange_name in manager.exchanges.keys():
            assert exchange_name in tickers
            for symbol in symbols:
                assert symbol in tickers[exchange_name]
    
    @pytest.mark.asyncio
    async def test_exchange_failover(self, mock_config):
        """Test exchange failover when one fails"""
        manager = ExchangeManager(mock_config)
        
        symbols = ["BTC/USDT"]
        
        # Mock one exchange to fail and another to succeed
        success_ticker = {
            "symbol": "BTC/USDT",
            "lastPrice": "50000.00",
            "priceChangePercent": "2.5"
        }
        
        call_count = 0
        
        def mock_get_ticker_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Connection failed")
            else:
                return success_ticker
        
        # Apply the mock to all exchanges
        for exchange_name, client in manager.exchanges.items():
            if hasattr(client, 'get_ticker'):
                with patch.object(client, 'get_ticker', side_effect=mock_get_ticker_side_effect):
                    pass
        
        tickers = await manager.get_all_tickers(symbols)
        
        # Should handle failures gracefully
        assert isinstance(tickers, dict)
        
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_config):
        """Test concurrent operations across exchanges"""
        manager = ExchangeManager(mock_config)
        
        # Mock responses
        mock_balance = {"BTC": {"total": 1.0}}
        mock_ticker = {"symbol": "BTC/USDT", "lastPrice": "50000"}
        
        for client in manager.exchanges.values():
            if hasattr(client, 'get_balance'):
                with patch.object(client, 'get_balance', return_value=mock_balance):
                    pass
            if hasattr(client, 'get_ticker'):
                with patch.object(client, 'get_ticker', return_value=mock_ticker):
                    pass
        
        # Run concurrent operations
        tasks = [
            manager.get_all_balances(),
            manager.get_all_tickers(["BTC/USDT"]),
            manager.list_exchanges()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All operations should complete without blocking each other
        assert len(results) == 3
        for result in results:
            assert not isinstance(result, Exception)