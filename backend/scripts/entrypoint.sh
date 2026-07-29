#!/bin/sh
set -eu

command_name="${1:-web}"
if [ "$#" -gt 0 ]; then
    shift
fi
printf '%s' "$command_name" > /tmp/sunnekatha-process-role

case "$command_name" in
    web)
        exec gunicorn config.wsgi:application --config config/gunicorn.py "$@"
        ;;
    worker)
        exec celery -A config worker \
            --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
            --concurrency="${CELERY_WORKER_CONCURRENCY:-2}" \
            "$@"
        ;;
    beat)
        exec celery -A config beat \
            --loglevel="${CELERY_LOG_LEVEL:-INFO}" \
            --pidfile= \
            "$@"
        ;;
    migrate)
        exec python manage.py migrate --noinput "$@"
        ;;
    check)
        exec python manage.py check --deploy --fail-level WARNING "$@"
        ;;
    *)
        exec "$command_name" "$@"
        ;;
esac
