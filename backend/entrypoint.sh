#!/bin/sh
set -e

echo "Applying database migrations..."
alembic upgrade head

if [ "${SRM_SEED_DEMO:-true}" = "true" ]; then
  echo "Seeding demo data (idempotent)..."
  python -m scripts.seed_demo
fi

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
