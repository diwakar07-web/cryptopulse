-- =============================================================================
-- ANALYTICS LAYER: Reporting-optimized tables for Power BI
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics_coin_summary (
    id                  BIGSERIAL PRIMARY KEY,
    coin_id             TEXT          NOT NULL,
    coin_name           TEXT,
    symbol              TEXT,
    avg_price           NUMERIC(24,8),
    highest_price       NUMERIC(24,8),
    lowest_price        NUMERIC(24,8),
    latest_price        NUMERIC(24,8),
    market_cap          NUMERIC(30,2),
    circulating_supply  NUMERIC(30,4),
    rolling_avg_7d      NUMERIC(24,8),
    volatility          NUMERIC(24,8),
    price_change_24h    NUMERIC(10,4),
    price_change_7d     NUMERIC(10,4),
    price_change_30d    NUMERIC(10,4),
    snapshot_date       DATE          NOT NULL,
    updated_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (coin_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_acs_coin_date
    ON analytics_coin_summary (coin_id, snapshot_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_market_overview (
    id               BIGSERIAL PRIMARY KEY,
    snapshot_date    DATE          NOT NULL UNIQUE,
    total_market_cap NUMERIC(36,2),
    total_volume     NUMERIC(36,2),
    btc_price        NUMERIC(24,8),
    eth_price        NUMERIC(24,8),
    btc_dominance    NUMERIC(6,2),
    eth_dominance    NUMERIC(6,2),
    coin_count       INTEGER,
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_amo_date
    ON analytics_market_overview (snapshot_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_top_gainers (
    id               BIGSERIAL PRIMARY KEY,
    coin_id          TEXT          NOT NULL,
    symbol           TEXT,
    coin_name        TEXT,
    price            NUMERIC(24,8),
    price_change_24h NUMERIC(10,4),
    market_cap       NUMERIC(30,2),
    volume           NUMERIC(30,2),
    rank_position    INTEGER,
    snapshot_date    DATE          NOT NULL,
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_atg_date_rank
    ON analytics_top_gainers (snapshot_date DESC, rank_position);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_top_losers (
    id               BIGSERIAL PRIMARY KEY,
    coin_id          TEXT          NOT NULL,
    symbol           TEXT,
    coin_name        TEXT,
    price            NUMERIC(24,8),
    price_change_24h NUMERIC(10,4),
    market_cap       NUMERIC(30,2),
    volume           NUMERIC(30,2),
    rank_position    INTEGER,
    snapshot_date    DATE          NOT NULL,
    updated_at       TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_atl_date_rank
    ON analytics_top_losers (snapshot_date DESC, rank_position);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_volume_trends (
    id                BIGSERIAL PRIMARY KEY,
    coin_id           TEXT          NOT NULL,
    symbol            TEXT,
    snapshot_date     DATE          NOT NULL,
    daily_volume      NUMERIC(30,2),
    avg_7d_volume     NUMERIC(30,2),
    volume_change_pct NUMERIC(10,4),
    updated_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (coin_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_avt_coin_date
    ON analytics_volume_trends (coin_id, snapshot_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_price_history (
    id            BIGSERIAL PRIMARY KEY,
    coin_id       TEXT          NOT NULL,
    symbol        TEXT,
    snapshot_date DATE          NOT NULL,
    open_price    NUMERIC(24,8),
    close_price   NUMERIC(24,8),
    high_price    NUMERIC(24,8),
    low_price     NUMERIC(24,8),
    avg_price     NUMERIC(24,8),
    ma_7d         NUMERIC(24,8),
    ma_30d        NUMERIC(24,8),
    updated_at    TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (coin_id, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_aph_coin_date
    ON analytics_price_history (coin_id, snapshot_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_sentiment (
    id             BIGSERIAL PRIMARY KEY,
    snapshot_date  DATE        NOT NULL UNIQUE,
    avg_index      NUMERIC(5,2),
    classification TEXT,
    min_index      SMALLINT,
    max_index      SMALLINT,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_as_date
    ON analytics_sentiment (snapshot_date DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS analytics_pipeline_health (
    id                   BIGSERIAL PRIMARY KEY,
    snapshot_date        DATE        NOT NULL UNIQUE,
    total_runs           INTEGER,
    successful_runs      INTEGER,
    failed_runs          INTEGER,
    avg_execution_time   NUMERIC(10,2),
    total_rows_processed BIGINT,
    total_rows_rejected  BIGINT,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_aph2_date
    ON analytics_pipeline_health (snapshot_date DESC);
