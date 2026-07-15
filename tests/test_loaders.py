"""Tests for incremental loading logic."""
import pandas as pd
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

from etl.load.loaders import (
    _upsert_raw_coin_market,
    _upsert_raw_exchange_prices,
    _upsert_raw_fear_greed,
)


class TestIncrementalLoadCoinMarket:

    def _make_df(self, coin_id="bitcoin", extra=False):
        rows = [
            {
                "coin_id": coin_id,
                "symbol": "BTC",
                "name": "Bitcoin",
                "price": 45000.0,
                "market_cap": 850e9,
                "volume": 28e9,
                "circulating_supply": 19.5e6,
                "price_change_24h": 2.5,
                "price_change_7d": -1.2,
                "price_change_30d": 15.0,
                "snapshot_time": datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
                "source": "coingecko",
            }
        ]
        if extra:
            rows.append({**rows[0], "snapshot_time": datetime(2024, 6, 1, 13, 0, tzinfo=timezone.utc)})
        return pd.DataFrame(rows)

    def test_empty_df_returns_zero(self):
        engine = MagicMock()
        result = _upsert_raw_coin_market(pd.DataFrame(), engine)
        assert result == 0

    def test_new_rows_inserted(self):
        engine = MagicMock()
        existing = pd.DataFrame(columns=["coin_id", "snapshot_time", "source"])

        with patch("etl.load.loaders.pd.read_sql", return_value=existing), \
             patch("pandas.DataFrame.to_sql") as mock_to_sql:
            df = self._make_df()
            result = _upsert_raw_coin_market(df, engine)
            assert mock_to_sql.called

    def test_duplicate_rows_skipped(self):
        engine = MagicMock()
        df = self._make_df()
        existing = pd.DataFrame([
            {
                "coin_id": "bitcoin",
                "snapshot_time": datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
                "source": "coingecko",
            }
        ])
        existing["snapshot_time"] = pd.to_datetime(existing["snapshot_time"], utc=True)

        with patch("etl.load.loaders.pd.read_sql", return_value=existing), \
             patch("pandas.DataFrame.to_sql") as mock_to_sql:
            result = _upsert_raw_coin_market(df, engine)
            mock_to_sql.assert_not_called()

    def test_partial_new_rows_inserted(self):
        """When one row already exists, only the other should be inserted."""
        import pandas as pd
        from datetime import datetime, timezone
        from unittest.mock import MagicMock, patch
        from etl.load.loaders import _upsert_raw_coin_market

        engine = MagicMock()
        t1 = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
        t2 = datetime(2024, 6, 1, 13, 0, tzinfo=timezone.utc)
        base = {
            "coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin",
            "price": 45000.0, "market_cap": 850e9, "volume": 28e9,
            "circulating_supply": 19.5e6, "price_change_24h": 2.5,
            "price_change_7d": -1.2, "price_change_30d": 15.0,
            "source": "coingecko",
        }
        df = pd.DataFrame([{**base, "snapshot_time": t1}, {**base, "snapshot_time": t2}])
        df["snapshot_time"] = pd.to_datetime(df["snapshot_time"], utc=True)

        # Simulate t1 already exists in DB
        existing = pd.DataFrame([{"coin_id": "bitcoin", "snapshot_time": t1, "source": "coingecko"}])
        existing["snapshot_time"] = pd.to_datetime(existing["snapshot_time"], utc=True)

        written_dfs = []

        def fake_to_sql(self_df, name, engine_arg, **kwargs):
            written_dfs.append(self_df)

        with patch("etl.load.loaders.pd.read_sql", return_value=existing):
            with patch.object(pd.DataFrame, "to_sql", fake_to_sql):
                _upsert_raw_coin_market(df, engine)

        assert len(written_dfs) == 1
        assert len(written_dfs[0]) == 1
        assert pd.to_datetime(written_dfs[0]["snapshot_time"].iloc[0], utc=True) == t2


class TestIncrementalLoadFearGreed:

    def test_empty_df_returns_zero(self):
        result = _upsert_raw_fear_greed(pd.DataFrame(), MagicMock())
        assert result == 0

    def test_new_fg_rows_inserted(self):
        engine = MagicMock()
        df = pd.DataFrame([
            {
                "index_value": 62,
                "classification": "Greed",
                "timestamp": datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc),
                "source": "alternative_me",
            }
        ])
        existing = pd.DataFrame(columns=["timestamp", "source"])

        with patch("etl.load.loaders.pd.read_sql", return_value=existing), \
             patch("pandas.DataFrame.to_sql") as mock_to_sql:
            _upsert_raw_fear_greed(df, engine)
            assert mock_to_sql.called
