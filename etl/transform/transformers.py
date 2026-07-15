"""Data transformation – clean, standardize, derive calculated columns."""
import logging
from datetime import datetime, timezone

import pandas as pd

logger = logging.getLogger(__name__)


def transform_coin_market(df: pd.DataFrame) -> pd.DataFrame:
    """Produce processed_market table from raw_coin_market data."""
    if df.empty:
        return df

    out = df[
        ["coin_id", "symbol", "name", "price", "market_cap", "volume",
         "circulating_supply", "price_change_24h", "price_change_7d",
         "price_change_30d", "snapshot_time", "source"]
    ].copy()

    # Normalize types
    out["price"] = pd.to_numeric(out["price"], errors="coerce")
    out["market_cap"] = pd.to_numeric(out["market_cap"], errors="coerce")
    out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
    out["circulating_supply"] = pd.to_numeric(out["circulating_supply"], errors="coerce")
    out["price_change_24h"] = pd.to_numeric(out["price_change_24h"], errors="coerce")
    out["price_change_7d"] = pd.to_numeric(out["price_change_7d"], errors="coerce")
    out["price_change_30d"] = pd.to_numeric(out["price_change_30d"], errors="coerce")

    # Ensure UTC timestamps
    if out["snapshot_time"].dt.tz is None:
        out["snapshot_time"] = out["snapshot_time"].dt.tz_localize("UTC")
    else:
        out["snapshot_time"] = out["snapshot_time"].dt.tz_convert("UTC")

    out["processed_time"] = datetime.now(timezone.utc)

    # Drop full-null rows on key fields
    out.dropna(subset=["coin_id", "price", "market_cap"], inplace=True)

    logger.info("Transformed coin market: %d rows", len(out))
    return out


def transform_exchange_prices(df: pd.DataFrame) -> pd.DataFrame:
    """Produce processed_exchange from raw_exchange_prices."""
    if df.empty:
        return df

    out = df.copy()
    for col in ["open", "high", "low", "close", "volume"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    if out["timestamp"].dt.tz is None:
        out["timestamp"] = out["timestamp"].dt.tz_localize("UTC")
    else:
        out["timestamp"] = out["timestamp"].dt.tz_convert("UTC")

    out["processed_time"] = datetime.now(timezone.utc)
    out.dropna(subset=["symbol", "close", "volume"], inplace=True)

    logger.info("Transformed exchange prices: %d rows", len(out))
    return out


def transform_fear_greed(df: pd.DataFrame) -> pd.DataFrame:
    """Produce processed_sentiment from raw_fear_greed."""
    if df.empty:
        return df

    out = df.copy()
    out["index_value"] = pd.to_numeric(out["index_value"], errors="coerce")

    if out["timestamp"].dt.tz is None:
        out["timestamp"] = out["timestamp"].dt.tz_localize("UTC")
    else:
        out["timestamp"] = out["timestamp"].dt.tz_convert("UTC")

    out["processed_time"] = datetime.now(timezone.utc)
    out.dropna(subset=["index_value", "timestamp"], inplace=True)

    logger.info("Transformed fear & greed: %d rows", len(out))
    return out
