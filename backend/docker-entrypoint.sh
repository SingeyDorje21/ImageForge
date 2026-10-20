#!/bin/sh
set -e

# Apply database migrations before serving. Set RUN_MIGRATIONS=false to skip,
# e.g. when migrations run as a separate release step.
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running database migrations..."
  alembic upgrade head
fi

exec "$@"
