-- =============================================================================
-- SQL VIEWS for Power BI and ad-hoc querying
-- =============================================================================

-- vw_market_summary: Latest snapshot per coin with ranking
CREATE OR REPLACE VIEW vw_market_summary AS
WITH latest AS (
    SELECT DISTINCT ON (coin_id)
        coin_id, symbol, name, price, market_cap, volume,
        price_change_24h, price_change_7d, snapshot_time
    FROM processed_market
    ORDER BY coin_id, snapshot_time DESC
)
SELECT
    coin_id,
    symbol,
    name,
    price,
    market_cap,
    volume,
    price_change_24h,
    price_change_7d,
    snapshot_time,
    RANK()       OVER (ORDER BY market_cap DESC)       AS market_cap_rank,
    RANK()       OVER (ORDER BY price_change_24h DESC) AS gainer_rank,
    DENSE_RANK() OVER (ORDER BY volume DESC)           AS volume_rank
FROM latest;

-- ─────────────────────────────────────────────────────────────────────────────

-- vw_pipeline_health: Last 7 days pipeline execution summary
CREATE OR REPLACE VIEW vw_pipeline_health AS
SELECT
    run_time::DATE              AS run_date,
    stage,
    COUNT(*)                    AS total_runs,
    SUM(rows_processed)         AS total_rows,
    SUM(rows_rejected)          AS rejected_rows,
    ROUND(AVG(execution_time)::NUMERIC, 2) AS avg_exec_seconds,
    COUNT(*) FILTER (WHERE status = 'success') AS successes,
    COUNT(*) FILTER (WHERE status = 'failed')  AS failures
FROM etl_run_logs
WHERE run_time >= NOW() - INTERVAL '7 days'
GROUP BY run_date, stage
ORDER BY run_date DESC, stage;

-- ─────────────────────────────────────────────────────────────────────────────

-- vw_daily_volume: Aggregated daily volumes per coin with 7-day rolling average
CREATE OR REPLACE VIEW vw_daily_volume AS
WITH daily_agg AS (
    SELECT
        coin_id,
        symbol,
        snapshot_time::DATE         AS trade_date,
        AVG(volume)                 AS avg_daily_volume,
        MAX(volume)                 AS max_volume,
        MIN(volume)                 AS min_volume
    FROM processed_market
    GROUP BY coin_id, symbol, snapshot_time::DATE
)
SELECT
    coin_id,
    symbol,
    trade_date,
    avg_daily_volume,
    max_volume,
    min_volume,
    AVG(avg_daily_volume) OVER (
        PARTITION BY coin_id
        ORDER BY trade_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    )                           AS rolling_7d_avg_volume
FROM daily_agg
ORDER BY coin_id, trade_date DESC;

-- ─────────────────────────────────────────────────────────────────────────────

-- vw_sentiment_vs_btc: Fear & Greed index vs BTC daily price
CREATE OR REPLACE VIEW vw_sentiment_vs_btc AS
SELECT
    s.snapshot_date,
    s.avg_index,
    s.classification,
    ph.close_price  AS btc_close,
    ph.ma_7d        AS btc_ma7,
    LAG(ph.close_price) OVER (ORDER BY s.snapshot_date) AS btc_prev_close,
    ROUND(
        (ph.close_price - LAG(ph.close_price) OVER (ORDER BY s.snapshot_date))
        / NULLIF(LAG(ph.close_price) OVER (ORDER BY s.snapshot_date), 0) * 100,
        2
    ) AS btc_daily_change_pct
FROM analytics_sentiment s
LEFT JOIN analytics_price_history ph
    ON ph.snapshot_date = s.snapshot_date AND ph.coin_id = 'bitcoin'
ORDER BY s.snapshot_date DESC;

-- ─────────────────────────────────────────────────────────────────────────────

-- vw_api_performance: API reliability and latency stats (last 7 days)
CREATE OR REPLACE VIEW vw_api_performance AS
SELECT
    api_name,
    COUNT(*)                                            AS total_calls,
    COUNT(*) FILTER (WHERE status = 'success')          AS successful_calls,
    COUNT(*) FILTER (WHERE status = 'failed')           AS failed_calls,
    ROUND(AVG(duration)::NUMERIC, 3)                    AS avg_duration_sec,
    ROUND(MAX(duration)::NUMERIC, 3)                    AS max_duration_sec,
    ROUND(
        COUNT(*) FILTER (WHERE status = 'success')::NUMERIC / NULLIF(COUNT(*), 0) * 100,
        1
    )                                                   AS success_rate_pct
FROM api_request_logs
WHERE timestamp >= NOW() - INTERVAL '7 days'
GROUP BY api_name
ORDER BY api_name;
