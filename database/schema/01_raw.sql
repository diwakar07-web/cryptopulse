-- =============================================================================
-- RAW LAYER: Immutable append-only storage of API responses
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw_coin_market (
    id                  BIGSERIAL PRIMARY KEY,
    coin_id             TEXT        NOT NULL,
    symbol              TEXT        NOT NULL,
    name                TEXT,
    price               NUMERIC(24, 8),
    market_cap          NUMERIC(30, 2),
    volume              NUMERIC(30, 2),
    circulating_supply  NUMERIC(30, 4),
    price_change_24h    NUMERIC(10, 4),
    price_change_7d     NUMERIC(10, 4),
    price_change_30d    NUMERIC(10, 4),
    snapshot_time       TIMESTAMPTZ NOT NULL,
    source              TEXT        NOT NULL DEFAULT 'coingecko',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rcm_coin_snap
    ON raw_coin_market (coin_id, snapshot_time);
CREATE INDEX IF NOT EXISTS idx_rcm_source
    ON raw_coin_market (source);
CREATE INDEX IF NOT EXISTS idx_rcm_created
    ON raw_coin_market (created_at);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw_exchange_prices (
    id          BIGSERIAL PRIMARY KEY,
    symbol      TEXT        NOT NULL,
    open        NUMERIC(24, 8),
    high        NUMERIC(24, 8),
    low         NUMERIC(24, 8),
    close       NUMERIC(24, 8),
    volume      NUMERIC(30, 4),
    timestamp   TIMESTAMPTZ NOT NULL,
    source      TEXT        NOT NULL DEFAULT 'binance',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rep_symbol_ts
    ON raw_exchange_prices (symbol, timestamp);
CREATE INDEX IF NOT EXISTS idx_rep_source
    ON raw_exchange_prices (source);

-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS raw_fear_greed (
    id              BIGSERIAL PRIMARY KEY,
    index_value     SMALLINT    NOT NULL CHECK (index_value BETWEEN 0 AND 100),
    classification  TEXT        NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    source          TEXT        NOT NULL DEFAULT 'alternative_me',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rfg_timestamp
    ON raw_fear_greed (timestamp);
