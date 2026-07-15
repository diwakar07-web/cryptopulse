"""Database loader – incremental insert with duplicate prevention."""
import logging
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.settings import DBConfig

logger = logging.getLogger(__name__)


def get_engine() -> Engine:
    return create_engine(DBConfig.url(), pool_pre_ping=True)


def _read_keys(sql: str, engine: Engine) -> pd.DataFrame:
    """Read key columns for deduplication bypassing Pandas SQL parser bugs."""
    with engine.begin() as conn:
        result = conn.execute(text(sql))
        # result.keys() works in SQLAlchemy 1.4+ 
        return pd.DataFrame(result.fetchall(), columns=result.keys())


def _write_df_to_sql(df: pd.DataFrame, table_name: str, engine: Engine) -> None:
    """Write DataFrame to SQL bypassing Pandas to_sql connection validation."""
    if df.empty:
        return
    cols = ", ".join(df.columns)
    vals = ", ".join([f":{c}" for c in df.columns])
    sql = f"INSERT INTO {table_name} ({cols}) VALUES ({vals})"
    
    # Handle NaNs which SQLAlchemy doesn't like for numeric/null fields
    df_clean = df.where(pd.notnull(df), None)
    records = df_clean.to_dict(orient="records")
    
    with engine.begin() as conn:
        conn.execute(text(sql), records)


def _upsert_raw_coin_market(df: pd.DataFrame, engine: Engine) -> int:
    """Append-only insert; skip rows already present by (coin_id, snapshot_time, source)."""
    if df.empty:
        return 0

    cols = ["coin_id", "symbol", "name", "price", "market_cap", "volume",
            "circulating_supply", "price_change_24h", "price_change_7d",
            "price_change_30d", "snapshot_time", "source"]
    df_to_write = df[[c for c in cols if c in df.columns]].copy()

    existing = _read_keys(
        "SELECT coin_id, snapshot_time, source FROM raw_coin_market", engine
    )

    if not existing.empty:
        existing["snapshot_time"] = pd.to_datetime(existing["snapshot_time"], utc=True)
        df_to_write["snapshot_time"] = pd.to_datetime(df_to_write["snapshot_time"], utc=True)
        key = ["coin_id", "snapshot_time", "source"]
        merged = df_to_write.merge(existing[key], on=key, how="left", indicator=True)
        df_to_write = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df_to_write.empty:
        logger.info("raw_coin_market: no new rows to insert (all duplicates)")
        return 0

    _write_df_to_sql(df_to_write, "raw_coin_market", engine)
    logger.info("raw_coin_market: inserted %d rows", len(df_to_write))
    return len(df_to_write)


def _upsert_raw_exchange_prices(df: pd.DataFrame, engine: Engine) -> int:
    if df.empty:
        return 0

    cols = ["symbol", "open", "high", "low", "close", "volume", "timestamp", "source"]
    df_to_write = df[[c for c in cols if c in df.columns]].copy()

    existing = _read_keys(
        "SELECT symbol, timestamp, source FROM raw_exchange_prices", engine
    )

    if not existing.empty:
        existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
        df_to_write["timestamp"] = pd.to_datetime(df_to_write["timestamp"], utc=True)
        key = ["symbol", "timestamp", "source"]
        merged = df_to_write.merge(existing[key], on=key, how="left", indicator=True)
        df_to_write = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df_to_write.empty:
        logger.info("raw_exchange_prices: no new rows")
        return 0

    _write_df_to_sql(df_to_write, "raw_exchange_prices", engine)
    logger.info("raw_exchange_prices: inserted %d rows", len(df_to_write))
    return len(df_to_write)


def _upsert_raw_fear_greed(df: pd.DataFrame, engine: Engine) -> int:
    if df.empty:
        return 0

    cols = ["index_value", "classification", "timestamp", "source"]
    df_to_write = df[[c for c in cols if c in df.columns]].copy()

    existing = _read_keys(
        "SELECT timestamp, source FROM raw_fear_greed", engine
    )

    if not existing.empty:
        existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
        df_to_write["timestamp"] = pd.to_datetime(df_to_write["timestamp"], utc=True)
        key = ["timestamp", "source"]
        merged = df_to_write.merge(existing[key], on=key, how="left", indicator=True)
        df_to_write = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df_to_write.empty:
        logger.info("raw_fear_greed: no new rows")
        return 0

    _write_df_to_sql(df_to_write, "raw_fear_greed", engine)
    logger.info("raw_fear_greed: inserted %d rows", len(df_to_write))
    return len(df_to_write)


def load_raw(coin_df: pd.DataFrame, exchange_df: pd.DataFrame, fg_df: pd.DataFrame) -> dict:
    engine = get_engine()
    return {
        "coin_market_rows": _upsert_raw_coin_market(coin_df, engine),
        "exchange_rows": _upsert_raw_exchange_prices(exchange_df, engine),
        "fear_greed_rows": _upsert_raw_fear_greed(fg_df, engine),
    }


def load_processed_market(df: pd.DataFrame, engine: Optional[Engine] = None) -> int:
    """Incremental load into processed_market."""
    if df.empty:
        return 0
    engine = engine or get_engine()

    existing = _read_keys(
        "SELECT coin_id, snapshot_time, source FROM processed_market", engine
    )

    if not existing.empty:
        existing["snapshot_time"] = pd.to_datetime(existing["snapshot_time"], utc=True)
        df["snapshot_time"] = pd.to_datetime(df["snapshot_time"], utc=True)
        key = ["coin_id", "snapshot_time", "source"]
        merged = df.merge(existing[key], on=key, how="left", indicator=True)
        df = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df.empty:
        return 0

    cols = ["coin_id", "symbol", "name", "price", "market_cap", "volume",
            "circulating_supply", "price_change_24h", "price_change_7d",
            "price_change_30d", "snapshot_time", "source", "processed_time"]
    df_write = df[[c for c in cols if c in df.columns]]
    _write_df_to_sql(df_write, "processed_market", engine)
    logger.info("processed_market: inserted %d rows", len(df_write))
    return len(df_write)


def load_processed_exchange(df: pd.DataFrame, engine: Optional[Engine] = None) -> int:
    if df.empty:
        return 0
    engine = engine or get_engine()

    existing = _read_keys(
        "SELECT symbol, timestamp, source FROM processed_exchange", engine
    )

    if not existing.empty:
        existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        key = ["symbol", "timestamp", "source"]
        merged = df.merge(existing[key], on=key, how="left", indicator=True)
        df = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df.empty:
        return 0

    cols = ["symbol", "open", "high", "low", "close", "volume", "timestamp", "source", "processed_time"]
    df_write = df[[c for c in cols if c in df.columns]]
    _write_df_to_sql(df_write, "processed_exchange", engine)
    logger.info("processed_exchange: inserted %d rows", len(df_write))
    return len(df_write)


def load_processed_sentiment(df: pd.DataFrame, engine: Optional[Engine] = None) -> int:
    if df.empty:
        return 0
    engine = engine or get_engine()

    existing = _read_keys(
        "SELECT timestamp, source FROM processed_sentiment", engine
    )

    if not existing.empty:
        existing["timestamp"] = pd.to_datetime(existing["timestamp"], utc=True)
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        key = ["timestamp", "source"]
        merged = df.merge(existing[key], on=key, how="left", indicator=True)
        df = merged[merged["_merge"] == "left_only"].drop(columns=["_merge"])

    if df.empty:
        return 0

    cols = ["index_value", "classification", "timestamp", "source", "processed_time"]
    df_write = df[[c for c in cols if c in df.columns]]
    _write_df_to_sql(df_write, "processed_sentiment", engine)
    logger.info("processed_sentiment: inserted %d rows", len(df_write))
    return len(df_write)


def log_etl_run(
    pipeline_id: str,
    stage: str,
    status: str,
    rows_processed: int,
    rows_rejected: int,
    execution_time: float,
    error_message: Optional[str] = None,
    engine: Optional[Engine] = None,
) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO etl_run_logs
                    (pipeline_id, stage, status, rows_processed, rows_rejected,
                     execution_time, error_message)
                VALUES
                    (:pipeline_id, :stage, :status, :rows_processed, :rows_rejected,
                     :execution_time, :error_message)
                """
            ),
            {
                "pipeline_id": pipeline_id,
                "stage": stage,
                "status": status,
                "rows_processed": rows_processed,
                "rows_rejected": rows_rejected,
                "execution_time": execution_time,
                "error_message": error_message,
            },
        )


def log_api_request(
    api_name: str,
    status: str,
    duration: float,
    engine: Optional[Engine] = None,
) -> None:
    engine = engine or get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO api_request_logs (api_name, status, duration)
                VALUES (:api_name, :status, :duration)
                """
            ),
            {"api_name": api_name, "status": status, "duration": duration},
        )
