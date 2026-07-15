"""Full ETL pipeline – orchestrates all stages, usable standalone or via Airflow."""
import logging
import time
import uuid
from datetime import datetime, timezone

from etl.extract.coingecko import fetch_market_data
from etl.extract.binance import fetch_exchange_prices
from etl.extract.fear_greed import fetch_fear_greed
from etl.validate.validators import (
    validate_coin_market,
    validate_exchange_prices,
    validate_fear_greed,
)
from etl.transform.transformers import (
    transform_coin_market,
    transform_exchange_prices,
    transform_fear_greed,
)
from etl.load.loaders import (
    load_raw,
    load_processed_market,
    load_processed_exchange,
    load_processed_sentiment,
    log_etl_run,
    log_api_request,
    get_engine,
)
from etl.analytics_builder import build_analytics
from etl.quality_checks import run_quality_checks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
)
logger = logging.getLogger(__name__)


def run_pipeline(pipeline_id: str | None = None) -> dict:
    """Execute the full ETL pipeline. Returns summary dict."""
    pipeline_id = pipeline_id or str(uuid.uuid4())
    engine = get_engine()
    start_total = time.perf_counter()
    summary: dict = {"pipeline_id": pipeline_id, "started_at": datetime.now(timezone.utc).isoformat()}

    # ── EXTRACT ────────────────────────────────────────────────────────────────
    logger.info("=== STAGE: EXTRACT ===")
    t = time.perf_counter()
    try:
        coin_raw = fetch_market_data()
        log_api_request("coingecko_market", "success", time.perf_counter() - t, engine)
    except Exception as exc:
        log_api_request("coingecko_market", "failed", time.perf_counter() - t, engine)
        logger.error("CoinGecko extract failed: %s", exc)
        coin_raw = None

    t = time.perf_counter()
    try:
        exchange_raw = fetch_exchange_prices()
        log_api_request("binance_klines", "success", time.perf_counter() - t, engine)
    except Exception as exc:
        log_api_request("binance_klines", "failed", time.perf_counter() - t, engine)
        logger.error("Binance extract failed: %s", exc)
        exchange_raw = None

    t = time.perf_counter()
    try:
        fg_raw = fetch_fear_greed()
        log_api_request("fear_greed", "success", time.perf_counter() - t, engine)
    except Exception as exc:
        log_api_request("fear_greed", "failed", time.perf_counter() - t, engine)
        logger.error("Fear & Greed extract failed: %s", exc)
        fg_raw = None

    # ── VALIDATE ───────────────────────────────────────────────────────────────
    logger.info("=== STAGE: VALIDATE ===")
    import pandas as pd
    coin_valid = validate_coin_market(coin_raw) if coin_raw is not None else None
    exchange_valid = validate_exchange_prices(exchange_raw) if exchange_raw is not None else None
    fg_valid = validate_fear_greed(fg_raw) if fg_raw is not None else None

    # ── LOAD RAW ───────────────────────────────────────────────────────────────
    logger.info("=== STAGE: LOAD RAW ===")
    t = time.perf_counter()
    raw_counts = load_raw(
        coin_df=coin_valid.valid_df if coin_valid else pd.DataFrame(),
        exchange_df=exchange_valid.valid_df if exchange_valid else pd.DataFrame(),
        fg_df=fg_valid.valid_df if fg_valid else pd.DataFrame(),
    )
    log_etl_run(pipeline_id, "load_raw", "success",
                sum(raw_counts.values()), 0, time.perf_counter() - t, engine=engine)

    # ── TRANSFORM ──────────────────────────────────────────────────────────────
    logger.info("=== STAGE: TRANSFORM ===")
    coin_tf = transform_coin_market(coin_valid.valid_df) if coin_valid else pd.DataFrame()
    exchange_tf = transform_exchange_prices(exchange_valid.valid_df) if exchange_valid else pd.DataFrame()
    fg_tf = transform_fear_greed(fg_valid.valid_df) if fg_valid else pd.DataFrame()

    # ── LOAD PROCESSED ─────────────────────────────────────────────────────────
    logger.info("=== STAGE: LOAD PROCESSED ===")
    t = time.perf_counter()
    pm_rows = load_processed_market(coin_tf, engine)
    pe_rows = load_processed_exchange(exchange_tf, engine)
    ps_rows = load_processed_sentiment(fg_tf, engine)
    total_proc = pm_rows + pe_rows + ps_rows
    rejected = sum([
        len(coin_valid.rejected_df) if coin_valid else 0,
        len(exchange_valid.rejected_df) if exchange_valid else 0,
        len(fg_valid.rejected_df) if fg_valid else 0,
    ])
    log_etl_run(pipeline_id, "load_processed", "success", total_proc, rejected,
                time.perf_counter() - t, engine=engine)

    # ── BUILD ANALYTICS ────────────────────────────────────────────────────────
    logger.info("=== STAGE: BUILD ANALYTICS ===")
    t = time.perf_counter()
    try:
        build_analytics(engine)
        log_etl_run(pipeline_id, "build_analytics", "success", 0, 0,
                    time.perf_counter() - t, engine=engine)
    except Exception as exc:
        log_etl_run(pipeline_id, "build_analytics", "failed", 0, 0,
                    time.perf_counter() - t, error_message=str(exc), engine=engine)
        logger.error("Analytics build failed: %s", exc)

    # ── QUALITY CHECKS ─────────────────────────────────────────────────────────
    logger.info("=== STAGE: QUALITY CHECKS ===")
    qc = run_quality_checks(engine)
    summary["quality_passed"] = qc.passed

    # ── FINAL LOG ──────────────────────────────────────────────────────────────
    total_elapsed = time.perf_counter() - start_total
    log_etl_run(pipeline_id, "full_pipeline", "success", total_proc, rejected,
                total_elapsed, engine=engine)

    summary.update({
        "raw_rows": raw_counts,
        "processed_market_rows": pm_rows,
        "processed_exchange_rows": pe_rows,
        "processed_sentiment_rows": ps_rows,
        "rejected_rows": rejected,
        "elapsed_seconds": round(total_elapsed, 2),
    })
    logger.info("Pipeline complete in %.2fs: %s", total_elapsed, summary)
    return summary


if __name__ == "__main__":
    run_pipeline()
