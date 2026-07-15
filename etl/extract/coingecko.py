"""CoinGecko API extractor."""
import logging
from datetime import datetime, timezone

import pandas as pd

from config.settings import APIConfig, ETLConfig
from etl.extract.http_client import get_json

logger = logging.getLogger(__name__)

BASE = APIConfig.coingecko_base
SOURCE = "coingecko"


def fetch_market_data() -> pd.DataFrame:
    """Fetch market data for configured coins (price, cap, volume, supply)."""
    url = f"{BASE}/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(ETLConfig.coins),
        "order": "market_cap_desc",
        "per_page": 100,
        "page": 1,
        "sparkline": "false",
        "price_change_percentage": "24h,7d,30d",
    }
    data = get_json(url, params)
    snapshot_time = datetime.now(timezone.utc)
    rows = []
    for item in data:
        rows.append(
            {
                "coin_id": item.get("id"),
                "symbol": item.get("symbol", "").upper(),
                "name": item.get("name"),
                "price": item.get("current_price"),
                "market_cap": item.get("market_cap"),
                "volume": item.get("total_volume"),
                "circulating_supply": item.get("circulating_supply"),
                "price_change_24h": item.get("price_change_percentage_24h"),
                "price_change_7d": item.get("price_change_percentage_7d_in_currency"),
                "price_change_30d": item.get("price_change_percentage_30d_in_currency"),
                "snapshot_time": snapshot_time,
                "source": SOURCE,
            }
        )
    df = pd.DataFrame(rows)
    logger.info("CoinGecko market: %d rows extracted", len(df))
    return df


def fetch_trending() -> pd.DataFrame:
    """Fetch trending coins from CoinGecko."""
    url = f"{BASE}/search/trending"
    data = get_json(url)
    snapshot_time = datetime.now(timezone.utc)
    rows = []
    for item in data.get("coins", []):
        coin = item.get("item", {})
        rows.append(
            {
                "coin_id": coin.get("id"),
                "symbol": coin.get("symbol", "").upper(),
                "name": coin.get("name"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "snapshot_time": snapshot_time,
                "source": SOURCE,
            }
        )
    df = pd.DataFrame(rows)
    logger.info("CoinGecko trending: %d rows extracted", len(df))
    return df
