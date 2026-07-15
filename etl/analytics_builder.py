"""Analytics builder – executes SQL to populate analytics layer tables."""
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.load.loaders import get_engine

logger = logging.getLogger(__name__)

# ── Analytics SQL statements ──────────────────────────────────────────────────

_COIN_SUMMARY = text(
    """
    INSERT INTO analytics_coin_summary
        (coin_id, coin_name, symbol, avg_price, highest_price, lowest_price,
         latest_price, market_cap, circulating_supply, rolling_avg_7d, volatility,
         price_change_24h, price_change_7d, price_change_30d, snapshot_date, updated_at)
    WITH ranked AS (
        SELECT
            coin_id,
            name                                                                  AS coin_name,
            symbol,
            price,
            market_cap,
            circulating_supply,
            price_change_24h,
            price_change_7d,
            price_change_30d,
            snapshot_time::DATE                                                   AS snapshot_date,
            AVG(price) OVER (PARTITION BY coin_id
                             ORDER BY snapshot_time
                             ROWS BETWEEN 6 PRECEDING AND CURRENT ROW)           AS rolling_avg_7d,
            STDDEV(price) OVER (PARTITION BY coin_id
                                ORDER BY snapshot_time
                                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)       AS volatility,
            ROW_NUMBER() OVER (PARTITION BY coin_id, snapshot_time::DATE
                               ORDER BY snapshot_time DESC)                       AS rn
        FROM processed_market
        WHERE snapshot_time >= NOW() - INTERVAL '90 days'
    )
    SELECT
        coin_id,
        coin_name,
        symbol,
        AVG(price)           AS avg_price,
        MAX(price)           AS highest_price,
        MIN(price)           AS lowest_price,
        MAX(price) FILTER (WHERE rn = 1) AS latest_price,
        MAX(market_cap)      AS market_cap,
        MAX(circulating_supply) AS circulating_supply,
        AVG(rolling_avg_7d)  AS rolling_avg_7d,
        AVG(volatility)      AS volatility,
        AVG(price_change_24h) AS price_change_24h,
        AVG(price_change_7d)  AS price_change_7d,
        AVG(price_change_30d) AS price_change_30d,
        snapshot_date,
        NOW()                AS updated_at
    FROM ranked
    GROUP BY coin_id, coin_name, symbol, snapshot_date
    ON CONFLICT (coin_id, snapshot_date)
    DO UPDATE SET
        avg_price         = EXCLUDED.avg_price,
        highest_price     = EXCLUDED.highest_price,
        lowest_price      = EXCLUDED.lowest_price,
        latest_price      = EXCLUDED.latest_price,
        market_cap        = EXCLUDED.market_cap,
        circulating_supply = EXCLUDED.circulating_supply,
        rolling_avg_7d    = EXCLUDED.rolling_avg_7d,
        volatility        = EXCLUDED.volatility,
        price_change_24h  = EXCLUDED.price_change_24h,
        price_change_7d   = EXCLUDED.price_change_7d,
        price_change_30d  = EXCLUDED.price_change_30d,
        updated_at        = NOW()
    """
)

_MARKET_OVERVIEW = text(
    """
    INSERT INTO analytics_market_overview
        (snapshot_date, total_market_cap, total_volume, btc_price, eth_price,
         btc_dominance, eth_dominance, coin_count, updated_at)
    WITH latest AS (
        SELECT DISTINCT ON (coin_id)
            coin_id, price, market_cap, volume, snapshot_time
        FROM processed_market
        ORDER BY coin_id, snapshot_time DESC
    ),
    totals AS (
        SELECT
            CURRENT_DATE                              AS snapshot_date,
            SUM(market_cap)                           AS total_market_cap,
            SUM(volume)                               AS total_volume,
            COUNT(*)                                  AS coin_count,
            MAX(price) FILTER (WHERE coin_id = 'bitcoin')  AS btc_price,
            MAX(price) FILTER (WHERE coin_id = 'ethereum') AS eth_price,
            MAX(market_cap) FILTER (WHERE coin_id = 'bitcoin')  AS btc_cap,
            MAX(market_cap) FILTER (WHERE coin_id = 'ethereum') AS eth_cap
        FROM latest
    )
    SELECT
        snapshot_date,
        total_market_cap,
        total_volume,
        btc_price,
        eth_price,
        ROUND(btc_cap / NULLIF(total_market_cap, 0) * 100, 2) AS btc_dominance,
        ROUND(eth_cap / NULLIF(total_market_cap, 0) * 100, 2) AS eth_dominance,
        coin_count,
        NOW()                                                  AS updated_at
    FROM totals
    ON CONFLICT (snapshot_date) DO UPDATE SET
        total_market_cap = EXCLUDED.total_market_cap,
        total_volume     = EXCLUDED.total_volume,
        btc_price        = EXCLUDED.btc_price,
        eth_price        = EXCLUDED.eth_price,
        btc_dominance    = EXCLUDED.btc_dominance,
        eth_dominance    = EXCLUDED.eth_dominance,
        coin_count       = EXCLUDED.coin_count,
        updated_at       = NOW()
    """
)

_TOP_GAINERS = text(
    """
    DELETE FROM analytics_top_gainers WHERE snapshot_date = CURRENT_DATE;
    INSERT INTO analytics_top_gainers
        (coin_id, symbol, coin_name, price, price_change_24h, market_cap, volume,
         rank_position, snapshot_date, updated_at)
    WITH latest AS (
        SELECT DISTINCT ON (coin_id)
            coin_id, symbol, name, price, price_change_24h, market_cap, volume
        FROM processed_market
        WHERE price_change_24h IS NOT NULL
        ORDER BY coin_id, snapshot_time DESC
    ),
    ranked AS (
        SELECT *,
               RANK() OVER (ORDER BY price_change_24h DESC) AS rank_position
        FROM latest
        WHERE price_change_24h > 0
    )
    SELECT coin_id, symbol, name, price, price_change_24h, market_cap, volume,
           rank_position, CURRENT_DATE, NOW()
    FROM ranked
    WHERE rank_position <= 10
    """
)

_TOP_LOSERS = text(
    """
    DELETE FROM analytics_top_losers WHERE snapshot_date = CURRENT_DATE;
    INSERT INTO analytics_top_losers
        (coin_id, symbol, coin_name, price, price_change_24h, market_cap, volume,
         rank_position, snapshot_date, updated_at)
    WITH latest AS (
        SELECT DISTINCT ON (coin_id)
            coin_id, symbol, name, price, price_change_24h, market_cap, volume
        FROM processed_market
        WHERE price_change_24h IS NOT NULL
        ORDER BY coin_id, snapshot_time DESC
    ),
    ranked AS (
        SELECT *,
               RANK() OVER (ORDER BY price_change_24h ASC) AS rank_position
        FROM latest
        WHERE price_change_24h < 0
    )
    SELECT coin_id, symbol, name, price, price_change_24h, market_cap, volume,
           rank_position, CURRENT_DATE, NOW()
    FROM ranked
    WHERE rank_position <= 10
    """
)

_VOLUME_TRENDS = text(
    """
    INSERT INTO analytics_volume_trends
        (coin_id, symbol, snapshot_date, daily_volume, avg_7d_volume,
         volume_change_pct, updated_at)
    WITH daily AS (
        SELECT
            coin_id,
            symbol,
            snapshot_time::DATE AS snapshot_date,
            AVG(volume)         AS daily_volume
        FROM processed_market
        WHERE snapshot_time >= NOW() - INTERVAL '60 days'
        GROUP BY coin_id, symbol, snapshot_time::DATE
    ),
    with_rolling AS (
        SELECT *,
               AVG(daily_volume) OVER (
                   PARTITION BY coin_id
                   ORDER BY snapshot_date
                   ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
               ) AS avg_7d_volume,
               LAG(daily_volume) OVER (PARTITION BY coin_id ORDER BY snapshot_date) AS prev_volume
        FROM daily
    )
    SELECT
        coin_id, symbol, snapshot_date, daily_volume, avg_7d_volume,
        CASE
            WHEN prev_volume > 0
            THEN ROUND((daily_volume - prev_volume) / prev_volume * 100, 2)
            ELSE NULL
        END AS volume_change_pct,
        NOW() AS updated_at
    FROM with_rolling
    ON CONFLICT (coin_id, snapshot_date) DO UPDATE SET
        daily_volume      = EXCLUDED.daily_volume,
        avg_7d_volume     = EXCLUDED.avg_7d_volume,
        volume_change_pct = EXCLUDED.volume_change_pct,
        updated_at        = NOW()
    """
)

_PRICE_HISTORY = text(
    """
    INSERT INTO analytics_price_history
        (coin_id, symbol, snapshot_date, open_price, close_price, high_price,
         low_price, avg_price, ma_7d, ma_30d, updated_at)
    WITH daily AS (
        SELECT
            coin_id,
            symbol,
            snapshot_time::DATE AS snapshot_date,
            FIRST_VALUE(price) OVER (
                PARTITION BY coin_id, snapshot_time::DATE
                ORDER BY snapshot_time
            ) AS open_price,
            LAST_VALUE(price) OVER (
                PARTITION BY coin_id, snapshot_time::DATE
                ORDER BY snapshot_time
                ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
            ) AS close_price,
            MAX(price) OVER (PARTITION BY coin_id, snapshot_time::DATE) AS high_price,
            MIN(price) OVER (PARTITION BY coin_id, snapshot_time::DATE) AS low_price,
            AVG(price) OVER (PARTITION BY coin_id, snapshot_time::DATE) AS avg_price
        FROM processed_market
        WHERE snapshot_time >= NOW() - INTERVAL '365 days'
    ),
    deduped AS (
        SELECT DISTINCT ON (coin_id, snapshot_date)
            coin_id, symbol, snapshot_date, open_price, close_price, high_price, low_price, avg_price
        FROM daily
        ORDER BY coin_id, snapshot_date
    ),
    with_ma AS (
        SELECT *,
               AVG(avg_price) OVER (PARTITION BY coin_id ORDER BY snapshot_date
                                    ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ma_7d,
               AVG(avg_price) OVER (PARTITION BY coin_id ORDER BY snapshot_date
                                    ROWS BETWEEN 29 PRECEDING AND CURRENT ROW) AS ma_30d
        FROM deduped
    )
    SELECT coin_id, symbol, snapshot_date, open_price, close_price, high_price, low_price,
           avg_price, ma_7d, ma_30d, NOW() AS updated_at
    FROM with_ma
    ON CONFLICT (coin_id, snapshot_date) DO UPDATE SET
        open_price  = EXCLUDED.open_price,
        close_price = EXCLUDED.close_price,
        high_price  = EXCLUDED.high_price,
        low_price   = EXCLUDED.low_price,
        avg_price   = EXCLUDED.avg_price,
        ma_7d       = EXCLUDED.ma_7d,
        ma_30d      = EXCLUDED.ma_30d,
        updated_at  = NOW()
    """
)

_SENTIMENT = text(
    """
    INSERT INTO analytics_sentiment
        (snapshot_date, avg_index, classification, min_index, max_index, updated_at)
    WITH daily AS (
        SELECT
            timestamp::DATE AS snapshot_date,
            AVG(index_value) AS avg_index,
            MIN(index_value) AS min_index,
            MAX(index_value) AS max_index
        FROM processed_sentiment
        WHERE timestamp >= NOW() - INTERVAL '90 days'
        GROUP BY timestamp::DATE
    )
    SELECT
        snapshot_date,
        ROUND(avg_index) AS avg_index,
        CASE
            WHEN avg_index <= 25 THEN 'Extreme Fear'
            WHEN avg_index <= 45 THEN 'Fear'
            WHEN avg_index <= 55 THEN 'Neutral'
            WHEN avg_index <= 75 THEN 'Greed'
            ELSE 'Extreme Greed'
        END AS classification,
        min_index,
        max_index,
        NOW() AS updated_at
    FROM daily
    ON CONFLICT (snapshot_date) DO UPDATE SET
        avg_index      = EXCLUDED.avg_index,
        classification = EXCLUDED.classification,
        min_index      = EXCLUDED.min_index,
        max_index      = EXCLUDED.max_index,
        updated_at     = NOW()
    """
)

_PIPELINE_HEALTH = text(
    """
    INSERT INTO analytics_pipeline_health
        (snapshot_date, total_runs, successful_runs, failed_runs, avg_execution_time,
         total_rows_processed, total_rows_rejected, updated_at)
    SELECT
        run_time::DATE                              AS snapshot_date,
        COUNT(*)                                   AS total_runs,
        COUNT(*) FILTER (WHERE status = 'success') AS successful_runs,
        COUNT(*) FILTER (WHERE status = 'failed')  AS failed_runs,
        ROUND(AVG(execution_time)::NUMERIC, 2)     AS avg_execution_time,
        SUM(rows_processed)                        AS total_rows_processed,
        SUM(rows_rejected)                         AS total_rows_rejected,
        NOW()                                      AS updated_at
    FROM etl_run_logs
    WHERE run_time >= NOW() - INTERVAL '30 days'
    GROUP BY run_time::DATE
    ON CONFLICT (snapshot_date) DO UPDATE SET
        total_runs          = EXCLUDED.total_runs,
        successful_runs     = EXCLUDED.successful_runs,
        failed_runs         = EXCLUDED.failed_runs,
        avg_execution_time  = EXCLUDED.avg_execution_time,
        total_rows_processed = EXCLUDED.total_rows_processed,
        total_rows_rejected  = EXCLUDED.total_rows_rejected,
        updated_at          = NOW()
    """
)


def build_analytics(engine: Optional[Engine] = None) -> None:
    """Execute all analytics SQL inserts in sequence."""
    engine = engine or get_engine()
    steps = [
        ("coin_summary", _COIN_SUMMARY),
        ("market_overview", _MARKET_OVERVIEW),
        ("top_gainers", _TOP_GAINERS),
        ("top_losers", _TOP_LOSERS),
        ("volume_trends", _VOLUME_TRENDS),
        ("price_history", _PRICE_HISTORY),
        ("sentiment", _SENTIMENT),
        ("pipeline_health", _PIPELINE_HEALTH),
    ]
    for name, stmt in steps:
        try:
            with engine.begin() as conn:
                conn.execute(stmt)
            logger.info("Analytics built: %s", name)
        except Exception as exc:  # noqa: BLE001
            logger.error("Analytics failed for %s: %s", name, exc)
            raise
