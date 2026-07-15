#!/bin/bash
# Wait for PostgreSQL to be ready, then initialize the schema.
set -e

PGREADY_CMD="pg_isready -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-cryptopulse}"

echo "Waiting for PostgreSQL..."
until $PGREADY_CMD; do
  sleep 2
done

echo "PostgreSQL is ready. Running schema initialization..."

export PGPASSWORD="${POSTGRES_PASSWORD:-cryptopulse_secret}"
PSQL="psql -h ${POSTGRES_HOST:-postgres} -p ${POSTGRES_PORT:-5432} -U ${POSTGRES_USER:-cryptopulse} -d ${POSTGRES_DB:-cryptopulse}"

$PSQL -f /docker-entrypoint-initdb.d/01_raw.sql
$PSQL -f /docker-entrypoint-initdb.d/02_processed.sql
$PSQL -f /docker-entrypoint-initdb.d/03_analytics.sql
$PSQL -f /docker-entrypoint-initdb.d/04_logs.sql
$PSQL -f /docker-entrypoint-initdb.d/05_views.sql
$PSQL -f /docker-entrypoint-initdb.d/06_procedures.sql

echo "Schema initialization complete."
