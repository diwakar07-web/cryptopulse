"""Database initialization script – runs all SQL schema files against PostgreSQL."""
import logging
import os
import sys
from pathlib import Path

import psycopg2

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_conn():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "cryptopulse"),
        user=os.getenv("POSTGRES_USER", "cryptopulse"),
        password=os.getenv("POSTGRES_PASSWORD", "cryptopulse_secret"),
    )


def run_sql_file(conn, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    logger.info("Applied: %s", path.name)


def main() -> None:
    schema_dir = Path(__file__).parent.parent / "database" / "schema"
    views_dir = Path(__file__).parent.parent / "database" / "views"
    procs_dir = Path(__file__).parent.parent / "database" / "procedures"

    sql_files = sorted(schema_dir.glob("*.sql")) + \
                sorted(views_dir.glob("*.sql")) + \
                sorted(procs_dir.glob("*.sql"))

    if not sql_files:
        logger.error("No SQL files found in database/ directories.")
        sys.exit(1)

    try:
        conn = get_conn()
    except psycopg2.OperationalError as exc:
        logger.error("Cannot connect to PostgreSQL: %s", exc)
        sys.exit(1)

    try:
        for path in sql_files:
            run_sql_file(conn, path)
        logger.info("Database initialization complete. %d files applied.", len(sql_files))
    except Exception as exc:
        conn.rollback()
        logger.error("Schema init failed: %s", exc)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
