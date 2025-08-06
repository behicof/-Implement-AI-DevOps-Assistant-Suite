"""
Unit tests for exchange clients
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from ai_devops.exchanges.binance import BinanceClient
from ai_devops.exchanges.wallex import WallexClient


class TestBinanceClient:
    """Test Binance exchange client"""
    
    def test_initialization(self):
        """Test Binance client initialization"""
        client = BinanceClient(
            api_key="test_key",
            api_secret="test_secret",
            testnet=True
        )
        
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert client.testnet is True
        assert "testnet" in client.base_url
    
    def test_signature_generation(self):
        """Test signature generation"""
        client = BinanceClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        params = {"symbol": "BTCUSDT", "side": "BUY"}
        signature = client._generate_signature(params)
        
        assert isinstance(signature, str)
        assert len(signature) == 64  # HMAC SHA256 hex digest length
    
    @pytest.mark.asyncio
    async def test_ping(self):
        """Test ping functionality"""
        client = BinanceClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = {}
            
            result = await client.ping()
            
            mock_request.assert_called_once_with('GET', '/api/v3/ping')
            assert result == {}
    
    @pytest.mark.asyncio
    async def test_get_ticker(self):
        """Test ticker retrieval"""
        client = BinanceClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        mock_response = {
            "symbol": "BTCUSDT",
            "price": "50000.00",
            "priceChangePercent": "2.5"
        }
        
        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.get_ticker("BTCUSDT")
            
            mock_request.assert_called_once_with(
                'GET', '/api/v3/ticker/24hr', {'symbol': 'BTCUSDT'}
            )
            assert result == mock_response


class TestWallexClient:
    """Test Wallex exchange client (Iranian)"""
    
    def test_initialization(self):
        """Test Wallex client initialization"""
        client = WallexClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        assert client.api_key == "test_key"
        assert client.api_secret == "test_secret"
        assert "wallex.ir" in client.base_url
    
    @pytest.mark.asyncio
    async def test_get_exchange_info(self):
        """Test exchange info retrieval"""
        client = WallexClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        mock_response = {
            "BTC": {"stats": {"lastTradePrice": "500000000"}},
            "ETH": {"stats": {"lastTradePrice": "30000000"}}
        }
        
        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.get_exchange_info()
            
            assert result["name"] == "Wallex"
            assert result["type"] == "iranian"
            assert result["base_currency"] == "IRT"
            assert "BTC" in result["supported_currencies"]
            assert "ETH" in result["supported_currencies"]
    
    @pytest.mark.asyncio
    async def test_get_ticker_irt_pair(self):
        """Test ticker retrieval for IRT pairs"""
        client = WallexClient(
            api_key="test_key",
            api_secret="test_secret"
        )
        
        mock_response = {
            "BTC": {
                "stats": {
                    "lastTradePrice": "500000000",
                    "dayChangePercent": "2.5",
                    "dayTradedAmount": "1000000000"
                }
            }
        }
        
        with patch.object(client, '_request') as mock_request:
            mock_request.return_value = mock_response
            
            result = await client.get_ticker("BTC/IRT")
            
            assert result["symbol"] == "BTC/IRT"
            assert result["lastPrice"] == "500000000"
            assert result["priceChangePercent"] == "2.5"
            assert result["volume"] == "1000000000"