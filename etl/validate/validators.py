"""Data validation engine for all pipeline datasets."""
import logging
from dataclasses import dataclass, field

import pandas as pd

from config.settings import ETLConfig

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    is_valid: bool
    valid_df: pd.DataFrame
    rejected_df: pd.DataFrame
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_coin_market(df: pd.DataFrame) -> ValidationResult:
    """Full validation for raw_coin_market data."""
    errors: list[str] = []
    warnings: list[str] = []

    required_cols = {"coin_id", "symbol", "price", "market_cap", "volume", "snapshot_time", "source"}
    missing = required_cols - set(df.columns)
    if missing:
        return ValidationResult(
            is_valid=False,
            valid_df=pd.DataFrame(),
            rejected_df=df,
            errors=[f"Missing required columns: {missing}"],
        )

    mask_valid = pd.Series([True] * len(df), index=df.index)

    # Required field non-null
    for col in ["coin_id", "symbol", "price", "market_cap", "volume"]:
        null_mask = df[col].isna()
        if null_mask.any():
            errors.append(f"Null values in '{col}': {null_mask.sum()} rows")
            mask_valid &= ~null_mask

    # Business rules – reject negatives / zero prices
    for col in ["price", "market_cap", "volume"]:
        if col in df.columns:
            bad = df[col].notna() & (df[col] < 0)
            if bad.any():
                errors.append(f"Negative values in '{col}': {bad.sum()} rows")
                mask_valid &= ~bad

    # Anomaly: price spike > threshold vs previous run (warn only)
    threshold = ETLConfig.price_spike_threshold
    if "price_change_24h" in df.columns:
        spikes = df["price_change_24h"].notna() & (df["price_change_24h"].abs() > threshold * 100)
        if spikes.any():
            warnings.append(f"Price spike anomalies detected: {spikes.sum()} rows")

    valid_df = df[mask_valid].copy()
    rejected_df = df[~mask_valid].copy()

    if not rejected_df.empty:
        rejected_df["rejection_reason"] = "; ".join(errors)

    is_valid = len(errors) == 0 or not valid_df.empty
    logger.info(
        "Coin market validation: valid=%d, rejected=%d, errors=%d",
        len(valid_df), len(rejected_df), len(errors),
    )
    return ValidationResult(is_valid=is_valid, valid_df=valid_df, rejected_df=rejected_df,
                            errors=errors, warnings=warnings)


def validate_exchange_prices(df: pd.DataFrame) -> ValidationResult:
    """Validation for raw_exchange_prices (Binance OHLCV)."""
    errors: list[str] = []
    required_cols = {"symbol", "open", "high", "low", "close", "volume", "timestamp", "source"}
    missing = required_cols - set(df.columns)
    if missing:
        return ValidationResult(
            is_valid=False, valid_df=pd.DataFrame(), rejected_df=df,
            errors=[f"Missing columns: {missing}"],
        )

    mask_valid = pd.Series([True] * len(df), index=df.index)

    for col in ["open", "high", "low", "close", "volume"]:
        bad = df[col].isna() | (df[col] < 0)
        if bad.any():
            errors.append(f"Invalid values in '{col}': {bad.sum()} rows")
            mask_valid &= ~bad

    # OHLC sanity: high >= low, close within range
    ohlc_bad = (df["high"] < df["low"]) | (df["close"] < df["low"]) | (df["close"] > df["high"])
    if ohlc_bad.any():
        errors.append(f"OHLC integrity violations: {ohlc_bad.sum()} rows")
        mask_valid &= ~ohlc_bad

    valid_df = df[mask_valid].copy()
    rejected_df = df[~mask_valid].copy()
    if not rejected_df.empty:
        rejected_df["rejection_reason"] = "; ".join(errors)

    logger.info("Exchange validation: valid=%d, rejected=%d", len(valid_df), len(rejected_df))
    return ValidationResult(is_valid=True, valid_df=valid_df, rejected_df=rejected_df, errors=errors)


def validate_fear_greed(df: pd.DataFrame) -> ValidationResult:
    """Validation for raw_fear_greed data."""
    errors: list[str] = []
    required_cols = {"index_value", "classification", "timestamp", "source"}
    missing = required_cols - set(df.columns)
    if missing:
        return ValidationResult(
            is_valid=False, valid_df=pd.DataFrame(), rejected_df=df,
            errors=[f"Missing columns: {missing}"],
        )

    mask_valid = pd.Series([True] * len(df), index=df.index)

    bad = df["index_value"].isna() | (df["index_value"] < 0) | (df["index_value"] > 100)
    if bad.any():
        errors.append(f"Invalid index_value (must be 0-100): {bad.sum()} rows")
        mask_valid &= ~bad

    valid_df = df[mask_valid].copy()
    rejected_df = df[~mask_valid].copy()
    if not rejected_df.empty:
        rejected_df["rejection_reason"] = "; ".join(errors)

    logger.info("Fear & Greed validation: valid=%d, rejected=%d", len(valid_df), len(rejected_df))
    return ValidationResult(is_valid=True, valid_df=valid_df, rejected_df=rejected_df, errors=errors)
