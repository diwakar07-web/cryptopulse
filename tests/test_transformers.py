"""Tests for ETL transformation functions."""
import pandas as pd
import pytest
from datetime import datetime, timezone

from etl.transform.transformers import (
    transform_coin_market,
    transform_exchange_prices,
    transform_fear_greed,
)


class TestTransformCoinMarket:

    def test_returns_dataframe(self, sample_coin_df):
        result = transform_coin_market(sample_coin_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2

    def test_adds_processed_time_column(self, sample_coin_df):
        result = transform_coin_market(sample_coin_df)
        assert "processed_time" in result.columns

    def test_snapshot_time_is_utc(self, sample_coin_df):
        result = transform_coin_market(sample_coin_df)
        assert result["snapshot_time"].dt.tz is not None

    def test_price_is_numeric(self, sample_coin_df):
        sample_coin_df["price"] = "45000"  # string input
        result = transform_coin_market(sample_coin_df)
        assert pd.api.types.is_numeric_dtype(result["price"])

    def test_null_price_rows_dropped(self, sample_coin_df):
        sample_coin_df.loc[0, "price"] = None
        result = transform_coin_market(sample_coin_df)
        assert len(result) == 1

    def test_empty_input_returns_empty(self):
        result = transform_coin_market(pd.DataFrame())
        assert result.empty

    def test_price_change_columns_coerced(self, sample_coin_df):
        sample_coin_df["price_change_24h"] = "abc"  # non-numeric
        result = transform_coin_market(sample_coin_df)
        assert result["price_change_24h"].isna().all()


class TestTransformExchange:

    def test_returns_dataframe(self, sample_exchange_df):
        result = transform_exchange_prices(sample_exchange_df)
        assert isinstance(result, pd.DataFrame)

    def test_timestamp_is_utc(self, sample_exchange_df):
        result = transform_exchange_prices(sample_exchange_df)
        assert result["timestamp"].dt.tz is not None

    def test_adds_processed_time(self, sample_exchange_df):
        result = transform_exchange_prices(sample_exchange_df)
        assert "processed_time" in result.columns

    def test_empty_returns_empty(self):
        result = transform_exchange_prices(pd.DataFrame())
        assert result.empty


class TestTransformFearGreed:

    def test_returns_dataframe(self, sample_fg_df):
        result = transform_fear_greed(sample_fg_df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_adds_processed_time(self, sample_fg_df):
        result = transform_fear_greed(sample_fg_df)
        assert "processed_time" in result.columns

    def test_index_value_numeric(self, sample_fg_df):
        sample_fg_df["index_value"] = "62"
        result = transform_fear_greed(sample_fg_df)
        assert pd.api.types.is_numeric_dtype(result["index_value"])
