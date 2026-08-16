#!/bin/bash
set -euo pipefail

python manage.py migrate --noinput

# exec so gunicorn is PID 1 and receives SIGTERM directly, allowing Fly to
# shut workers down gracefully instead of killing them.
exec gunicorn Handout.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
