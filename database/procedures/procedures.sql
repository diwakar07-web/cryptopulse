-- =============================================================================
-- STORED PROCEDURES
-- =============================================================================

-- sp_cleanup_logs: Remove logs older than retention_days (default 90)
CREATE OR REPLACE PROCEDURE sp_cleanup_logs(retention_days INTEGER DEFAULT 90)
LANGUAGE plpgsql AS $$
BEGIN
    DELETE FROM etl_run_logs
    WHERE run_time < NOW() - (retention_days || ' days')::INTERVAL;

    DELETE FROM api_request_logs
    WHERE timestamp < NOW() - (retention_days || ' days')::INTERVAL;

    RAISE NOTICE 'Log cleanup complete: removed records older than % days', retention_days;
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────

-- sp_build_analytics: Wrapper to rebuild all analytics tables (called by Airflow)
CREATE OR REPLACE PROCEDURE sp_build_analytics()
LANGUAGE plpgsql AS $$
DECLARE
    v_start TIMESTAMPTZ := NOW();
BEGIN
    -- coin summary (UPSERT handled in Python analytics_builder.py)
    RAISE NOTICE 'Analytics build started at %', v_start;
    RAISE NOTICE 'Analytics build complete in % seconds', EXTRACT(EPOCH FROM NOW() - v_start);
END;
$$;

-- ─────────────────────────────────────────────────────────────────────────────

-- sp_incremental_load: Check and report on incremental load status
CREATE OR REPLACE PROCEDURE sp_incremental_load(
    OUT rows_added BIGINT,
    OUT latest_snapshot TIMESTAMPTZ
)
LANGUAGE plpgsql AS $$
BEGIN
    SELECT COUNT(*), MAX(snapshot_time)
    INTO rows_added, latest_snapshot
    FROM processed_market
    WHERE processed_time >= NOW() - INTERVAL '1 hour';

    RAISE NOTICE 'Incremental load: % rows added, latest snapshot at %',
                  rows_added, latest_snapshot;
END;
$$;
