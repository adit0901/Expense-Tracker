#!/usr/bin/env bash
# Local PostgreSQL cluster for development/tests without Docker.
# Usage: scripts/dev-db.sh start|stop|status|reset
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PGBIN="${PGBIN:-/Library/PostgreSQL/18/bin}"
PGDATA="$ROOT/.local/pgdata"
PORT="${PGPORT:-54329}"
LOG="$ROOT/.local/postgres.log"
export PATH="$PGBIN:$PATH"

psql_super() { psql -h localhost -p "$PORT" -U postgres -v ON_ERROR_STOP=1 -q "$@"; }

init() {
  mkdir -p "$ROOT/.local"
  initdb -D "$PGDATA" -U postgres --auth=trust -E UTF8 --locale=C >/dev/null
  pg_ctl -D "$PGDATA" -o "-p $PORT -k /tmp" -l "$LOG" -w start >/dev/null
  psql_super -d postgres <<'SQL'
CREATE ROLE fintrack LOGIN PASSWORD 'fintrack' CREATEDB;
CREATE ROLE fintrack_app LOGIN PASSWORD 'fintrack_app';
CREATE DATABASE fintrack OWNER fintrack;
CREATE DATABASE fintrack_test OWNER fintrack;
SQL
  for db in fintrack fintrack_test; do
    psql_super -d "$db" -c "CREATE EXTENSION IF NOT EXISTS citext; CREATE EXTENSION IF NOT EXISTS pg_trgm;"
  done
  echo "Initialized cluster at $PGDATA (port $PORT)"
}

case "${1:-start}" in
  start)
    if [ ! -d "$PGDATA" ]; then init; exit 0; fi
    pg_ctl -D "$PGDATA" status >/dev/null 2>&1 || pg_ctl -D "$PGDATA" -o "-p $PORT -k /tmp" -l "$LOG" -w start >/dev/null
    echo "PostgreSQL running on port $PORT" ;;
  stop) pg_ctl -D "$PGDATA" -w stop ;;
  status) pg_ctl -D "$PGDATA" status ;;
  reset) pg_ctl -D "$PGDATA" -w stop 2>/dev/null || true; rm -rf "$PGDATA"; init ;;
  *) echo "usage: $0 start|stop|status|reset" >&2; exit 2 ;;
esac
