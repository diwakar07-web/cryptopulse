-- =============================================================================
-- PROCESSED LAYER: Clean, standardized, deduplicated datasets
-- =============================================================================

CREATE TABLE IF NOT EXISTS processed_market (
    id                  BIGSERIAL PRIMARY KEY,
    coin_id             TEXT        NOT NULL,
    symbol              TEXT        NOT NULL,
    name                TEXT,
    price               NUMERIC(24, 8) NOT NULL CHECK (price >= 0),
    market_cap          NUMERIC(30, 2) CHECK (market_cap >= 0),
    volume              NUMERIC(30, 2) CHECK (volume >= 0),
    circulating_supply  NUMERIC(30, 4),
    price_change_24h    NUMERIC(10, 4),
    price_change_7d     NUMERIC(10, 4),
    price_change_30d    NUMERIC(10, 4),
    snapshot_time       TIMESTAMPTZ NOT NULL,
    source              TEXT        NOT NULL,
    processed_time      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_pm_coin_snap_src
    ON processed_market (coin_id, snapshot_time, source);
CREATE INDEX IF NOT EXISTS idx_pm_coin_id
    ON processed_market (coin_id);
CREATE INDEX IF NOT EXISTS idx_pm_snapshot
    ON processed_market (snapshot_time DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS processed_exchange (
    id              BIGSERIAL PRIMARY KEY,
    symbol          TEXT          NOT NULL,
    open            NUMERIC(24,8) NOT NULL CHECK (open >= 0),
    high            NUMERIC(24,8) NOT NULL CHECK (high >= 0),
    low             NUMERIC(24,8) NOT NULL CHECK (low >= 0),
    close           NUMERIC(24,8) NOT NULL CHECK (close >= 0),
    volume          NUMERIC(30,4) NOT NULL CHECK (volume >= 0),
    timestamp       TIMESTAMPTZ   NOT NULL,
    source          TEXT          NOT NULL,
    processed_time  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_pe_sym_ts_src
    ON processed_exchange (symbol, timestamp, source);
CREATE INDEX IF NOT EXISTS idx_pe_symbol
    ON processed_exchange (symbol);
CREATE INDEX IF NOT EXISTS idx_pe_timestamp
    ON processed_exchange (timestamp DESC);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS processed_sentiment (
    id              BIGSERIAL PRIMARY KEY,
    index_value     SMALLINT    NOT NULL CHECK (index_value BETWEEN 0 AND 100),
    classification  TEXT        NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    source          TEXT        NOT NULL,
    processed_time  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS uidx_ps_ts_src
    ON processed_sentiment (timestamp, source);
CREATE INDEX IF NOT EXISTS idx_ps_timestamp
    ON processed_sentiment (timestamp DESC);
