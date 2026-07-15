"""Data quality checker – queries analytics tables to detect issues."""
import logging
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from etl.load.loaders import get_engine

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    duplicate_rows: int
    null_prices: int
    negative_values: int
    missing_snapshots: int
    passed: bool


def run_quality_checks(engine: Optional[Engine] = None) -> QualityReport:
    engine = engine or get_engine()

    with engine.connect() as conn:
        dup = conn.execute(
            text(
                """
                SELECT COUNT(*) AS cnt FROM (
                    SELECT coin_id, snapshot_time, source, COUNT(*) AS c
                    FROM raw_coin_market
                    GROUP BY coin_id, snapshot_time, source
                    HAVING COUNT(*) > 1
                ) t
                """
            )
        ).scalar()

        null_p = conn.execute(
            text("SELECT COUNT(*) FROM processed_market WHERE price IS NULL")
        ).scalar()

        neg = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM processed_market
                WHERE price < 0 OR market_cap < 0 OR volume < 0
                """
            )
        ).scalar()

        # Missing snapshots: coins with no data in last 2 hours
        missing = conn.execute(
            text(
                """
                SELECT COUNT(DISTINCT coin_id) FROM processed_market
                WHERE coin_id NOT IN (
                    SELECT DISTINCT coin_id FROM processed_market
                    WHERE snapshot_time >= NOW() - INTERVAL '2 hours'
                )
                """
            )
        ).scalar()

    passed = dup == 0 and null_p == 0 and neg == 0

    report = QualityReport(
        duplicate_rows=int(dup or 0),
        null_prices=int(null_p or 0),
        negative_values=int(neg or 0),
        missing_snapshots=int(missing or 0),
        passed=passed,
    )
    logger.info(
        "Quality check: duplicates=%d nulls=%d negatives=%d missing=%d passed=%s",
        report.duplicate_rows, report.null_prices,
        report.negative_values, report.missing_snapshots, report.passed,
    )
    return report
