"""Binance Public API extractor – OHLC klines + latest prices."""
import logging
from datetime import datetime, timezone

import pandas as pd

from config.settings import APIConfig, ETLConfig
from etl.extract.http_client import get_json

logger = logging.getLogger(__name__)

BASE = APIConfig.binance_base
SOURCE = "binance"


def fetch_klines(symbol: str, interval: str = "1h", limit: int = 24) -> list[dict]:
    """Fetch OHLCV klines for a single symbol."""
    url = f"{BASE}/klines"
    data = get_json(url, params={"symbol": symbol, "interval": interval, "limit": limit})
    rows = []
    for candle in data:
        rows.append(
            {
                "symbol": symbol,
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
                "timestamp": datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                "source": SOURCE,
            }
        )
    return rows


def fetch_exchange_prices() -> pd.DataFrame:
    """Fetch OHLC kline data for all configured Binance pairs."""
    all_rows: list[dict] = []
    for symbol in ETLConfig.binance_symbols:
        try:
            rows = fetch_klines(symbol)
            all_rows.extend(rows)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Binance klines failed for %s: %s", symbol, exc)
    df = pd.DataFrame(all_rows)
    logger.info("Binance exchange: %d rows extracted", len(df))
    return df


def fetch_ticker_prices() -> pd.DataFrame:
    """Fetch current best prices for all configured symbols."""
    url = f"{BASE}/ticker/price"
    data = get_json(url)
    wanted = set(ETLConfig.binance_symbols)
    snapshot_time = datetime.now(timezone.utc)
    rows = [
        {
            "symbol": item["symbol"],
            "price": float(item["price"]),
            "snapshot_time": snapshot_time,
            "source": SOURCE,
        }
        for item in data
        if item["symbol"] in wanted
    ]
    df = pd.DataFrame(rows)
    logger.info("Binance ticker: %d rows extracted", len(df))
    return df
