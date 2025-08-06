"""
Test configuration for pytest
"""

import pytest
import asyncio


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_config():
    """Sample configuration for testing"""
    return {
        "version": "1.0.0",
        "github": {
            "token": "test_token",
            "timeout": 30
        },
        "exchanges": {
            "supported": ["binance", "wallex"],
            "credentials": {
                "binance": {
                    "api_key": "test_key",
                    "api_secret": "test_secret",
                    "sandbox": True
                }
            }
        },
        "ai": {
            "provider": "openai",
            "model": "gpt-4",
            "credentials": {
                "openai": {"api_key": "test_key"}
            }
        }
    }