"""Tests for data validation logic."""
import pandas as pd
import pytest
from datetime import datetime, timezone

from etl.validate.validators import (
    validate_coin_market,
    validate_exchange_prices,
    validate_fear_greed,
)


class TestCoinMarketValidation:

    def test_valid_data_passes(self, sample_coin_df):
        result = validate_coin_market(sample_coin_df)
        assert len(result.valid_df) == 2
        assert result.rejected_df.empty

    def test_missing_required_column_fails(self, sample_coin_df):
        df = sample_coin_df.drop(columns=["price"])
        result = validate_coin_market(df)
        assert not result.is_valid
        assert any("price" in e for e in result.errors)

    def test_negative_price_rejected(self, sample_coin_df):
        sample_coin_df.loc[0, "price"] = -100.0
        result = validate_coin_market(sample_coin_df)
        assert len(result.rejected_df) == 1
        assert len(result.valid_df) == 1

    def test_null_coin_id_rejected(self, sample_coin_df):
        sample_coin_df.loc[0, "coin_id"] = None
        result = validate_coin_market(sample_coin_df)
        assert len(result.rejected_df) == 1

    def test_negative_market_cap_rejected(self, sample_coin_df):
        sample_coin_df.loc[1, "market_cap"] = -5000.0
        result = validate_coin_market(sample_coin_df)
        assert len(result.rejected_df) == 1

    def test_empty_dataframe(self):
        result = validate_coin_market(pd.DataFrame())
        assert not result.is_valid

    def test_all_rows_rejected_returns_empty_valid(self, sample_coin_df):
        sample_coin_df["price"] = -1.0
        result = validate_coin_market(sample_coin_df)
        assert result.valid_df.empty
        assert len(result.rejected_df) == 2


class TestExchangePriceValidation:

    def test_valid_exchange_data_passes(self, sample_exchange_df):
        result = validate_exchange_prices(sample_exchange_df)
        assert len(result.valid_df) == 1

    def test_invalid_ohlc_rejected(self, sample_exchange_df):
        # high < low is invalid
        sample_exchange_df.loc[0, "high"] = 100.0
        sample_exchange_df.loc[0, "low"] = 200.0
        result = validate_exchange_prices(sample_exchange_df)
        assert len(result.rejected_df) == 1

    def test_negative_volume_rejected(self, sample_exchange_df):
        sample_exchange_df.loc[0, "volume"] = -50.0
        result = validate_exchange_prices(sample_exchange_df)
        assert len(result.rejected_df) == 1

    def test_missing_columns_fails(self, sample_exchange_df):
        df = sample_exchange_df.drop(columns=["close"])
        result = validate_exchange_prices(df)
        assert not result.is_valid


class TestFearGreedValidation:

    def test_valid_fg_data_passes(self, sample_fg_df):
        result = validate_fear_greed(sample_fg_df)
        assert len(result.valid_df) == 1

    def test_out_of_range_index_rejected(self, sample_fg_df):
        sample_fg_df.loc[0, "index_value"] = 150
        result = validate_fear_greed(sample_fg_df)
        assert len(result.rejected_df) == 1

    def test_negative_index_rejected(self, sample_fg_df):
        sample_fg_df.loc[0, "index_value"] = -5
        result = validate_fear_greed(sample_fg_df)
        assert len(result.rejected_df) == 1

    def test_missing_columns_fails(self):
        df = pd.DataFrame([{"index_value": 50}])
        result = validate_fear_greed(df)
        assert not result.is_valid
