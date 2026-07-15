"""Shared pytest fixtures."""
import pandas as pd
import pytest
from datetime import datetime, timezone


@pytest.fixture
def sample_coin_df():
    """Valid coin market DataFrame fixture."""
    return pd.DataFrame([
        {
            "coin_id": "bitcoin",
            "symbol": "BTC",
            "name": "Bitcoin",
            "price": 45000.0,
            "market_cap": 850_000_000_000.0,
            "volume": 28_000_000_000.0,
            "circulating_supply": 19_500_000.0,
            "price_change_24h": 2.5,
            "price_change_7d": -1.2,
            "price_change_30d": 15.0,
            "snapshot_time": datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
            "source": "coingecko",
        },
        {
            "coin_id": "ethereum",
            "symbol": "ETH",
            "name": "Ethereum",
            "price": 2800.0,
            "market_cap": 336_000_000_000.0,
            "volume": 14_000_000_000.0,
            "circulating_supply": 120_000_000.0,
            "price_change_24h": -0.8,
            "price_change_7d": 3.1,
            "price_change_30d": 8.5,
            "snapshot_time": datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
            "source": "coingecko",
        },
    ])


@pytest.fixture
def sample_exchange_df():
    """Valid exchange price DataFrame fixture."""
    return pd.DataFrame([
        {
            "symbol": "BTCUSDT",
            "open": 44500.0,
            "high": 45500.0,
            "low": 44200.0,
            "close": 45000.0,
            "volume": 1500.0,
            "timestamp": datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
            "source": "binance",
        }
    ])


@pytest.fixture
def sample_fg_df():
    """Valid Fear & Greed DataFrame fixture."""
    return pd.DataFrame([
        {
            "index_value": 62,
            "classification": "Greed",
            "timestamp": datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc),
            "source": "alternative_me",
        }
    ])
