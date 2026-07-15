# CryptoPulse – Architecture

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      External APIs                           │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │
│  │  CoinGecko   │  │   Binance    │  │ Fear & Greed   │    │
│  │  /markets    │  │  /klines     │  │  /fng/         │    │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘    │
└─────────┼─────────────────┼───────────────────┼─────────────┘
          │                 │                   │
          └─────────────────┼───────────────────┘
                            │
               ┌────────────▼────────────┐
               │    Extract Service      │
               │  (etl/extract/*.py)     │
               │  • Retry / backoff      │
               │  • Rate limiting        │
               │  • JSON→DataFrame       │
               └────────────┬────────────┘
                            │
               ┌────────────▼────────────┐
               │   Validation Engine     │
               │  (etl/validate/)        │
               │  • Schema validation    │
               │  • Business rules       │
               │  • Anomaly detection    │
               │  • Duplicate detection  │
               └────────────┬────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │         PostgreSQL Raw Layer         │
          │  raw_coin_market                     │
          │  raw_exchange_prices                 │
          │  raw_fear_greed                      │
          └─────────────────┬──────────────────-┘
                            │
               ┌────────────▼────────────┐
               │  Transformation Service │
               │  (etl/transform/)       │
               │  • Clean nulls          │
               │  • UTC normalization    │
               │  • Type conversion      │
               │  • Derived columns      │
               └────────────┬────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │      PostgreSQL Processed Layer      │
          │  processed_market                    │
          │  processed_exchange                  │
          │  processed_sentiment                 │
          └─────────────────┬──────────────────-┘
                            │
               ┌────────────▼────────────┐
               │   Analytics Builder     │
               │  (etl/analytics_builder)│
               │  • CTEs                 │
               │  • Window functions     │
               │  • Moving averages      │
               │  • Rankings (RANK/DENSE)│
               │  • LAG/LEAD             │
               └────────────┬────────────┘
                            │
          ┌─────────────────▼──────────────────┐
          │      PostgreSQL Analytics Layer      │
          │  analytics_coin_summary              │
          │  analytics_market_overview           │
          │  analytics_top_gainers               │
          │  analytics_top_losers                │
          │  analytics_volume_trends             │
          │  analytics_price_history             │
          │  analytics_sentiment                 │
          │  analytics_pipeline_health           │
          └─────────────────┬──────────────────-┘
                            │
               ┌────────────▼────────────┐
               │    Power BI Dashboard   │
               │  • Executive Overview   │
               │  • Market Overview      │
               │  • Price Analysis       │
               │  • Volume Analysis      │
               │  • Sentiment            │
               │  • Top Movers           │
               │  • Pipeline Health      │
               └─────────────────────────┘

               ▲ Orchestrated by Apache Airflow ▲
```

## Database Layer Architecture

```
PostgreSQL: cryptopulse
├── Raw Layer          (immutable, append-only)
│   ├── raw_coin_market
│   ├── raw_exchange_prices
│   └── raw_fear_greed
│
├── Processed Layer    (clean, validated, deduplicated)
│   ├── processed_market
│   ├── processed_exchange
│   └── processed_sentiment
│
├── Analytics Layer    (aggregated, reporting-ready)
│   ├── analytics_coin_summary
│   ├── analytics_market_overview
│   ├── analytics_top_gainers
│   ├── analytics_top_losers
│   ├── analytics_volume_trends
│   ├── analytics_price_history
│   ├── analytics_sentiment
│   └── analytics_pipeline_health
│
├── Logging Layer
│   ├── etl_run_logs
│   └── api_request_logs
│
└── Views
    ├── vw_market_summary
    ├── vw_pipeline_health
    ├── vw_daily_volume
    ├── vw_sentiment_vs_btc
    └── vw_api_performance
```

## Airflow DAG Flow

```
extract_market_data
      │
validate_data
      │
load_raw_tables         ← Full pipeline executed here
      │
transform_data
      │
load_processed_tables
      │
build_analytics
      │
run_quality_checks
      │
generate_logs
      │
refresh_dashboard
```

Schedule: @hourly | Retries: 3 | Exponential backoff | Max active runs: 1

## Data Flow: Incremental Loading

```
Extract latest data from APIs
          │
          ▼
Read existing keys from DB
(coin_id, snapshot_time, source)
          │
          ▼
Filter: only new records
          │
          ▼
Insert into raw layer
          │
          ▼
Transform → processed layer
(same deduplication)
          │
          ▼
UPSERT into analytics layer
(ON CONFLICT DO UPDATE)
```

## SQL Techniques Demonstrated

| Technique         | Where Used                              |
|-------------------|-----------------------------------------|
| CTEs              | All analytics builders                  |
| ROW_NUMBER()      | Latest-per-coin deduplication           |
| RANK()            | Top gainers/losers ranking              |
| DENSE_RANK()      | Volume ranking in views                 |
| LAG()             | Volume change %, BTC daily change       |
| LEAD()            | Available for trend forecasting         |
| AVG() OVER()      | Rolling 7-day and 30-day averages       |
| STDDEV() OVER()   | Volatility calculation                  |
| ROWS BETWEEN      | Window frame for moving averages        |
| FIRST_VALUE()     | Open price per day                      |
| LAST_VALUE()      | Close price per day                     |
| UPSERT            | ON CONFLICT DO UPDATE in all analytics  |
| Incremental INS.  | Key-based dedup before insert           |
| Indexes           | coin_id, snapshot_time, source          |
| CHECK constraints | price≥0, volume≥0, index 0-100          |
| UNIQUE indexes    | Prevent duplicate processed records     |
