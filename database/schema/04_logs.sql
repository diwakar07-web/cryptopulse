-- =============================================================================
-- LOGGING LAYER: ETL run logs and API request logs
-- =============================================================================

CREATE TABLE IF NOT EXISTS etl_run_logs (
    id              BIGSERIAL PRIMARY KEY,
    pipeline_id     TEXT        NOT NULL,
    stage           TEXT        NOT NULL,
    status          TEXT        NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
    rows_processed  BIGINT      NOT NULL DEFAULT 0,
    rows_rejected   BIGINT      NOT NULL DEFAULT 0,
    execution_time  NUMERIC(10, 4),
    error_message   TEXT,
    run_time        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_erl_pipeline
    ON etl_run_logs (pipeline_id);
CREATE INDEX IF NOT EXISTS idx_erl_run_time
    ON etl_run_logs (run_time DESC);
CREATE INDEX IF NOT EXISTS idx_erl_status
    ON etl_run_logs (status);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS api_request_logs (
    id          BIGSERIAL PRIMARY KEY,
    api_name    TEXT        NOT NULL,
    status      TEXT        NOT NULL CHECK (status IN ('success', 'failed')),
    duration    NUMERIC(10, 4),
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_arl_api_name
    ON api_request_logs (api_name);
CREATE INDEX IF NOT EXISTS idx_arl_timestamp
    ON api_request_logs (timestamp DESC);
