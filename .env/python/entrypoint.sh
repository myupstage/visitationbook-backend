#!/bin/sh
echo "WORKDIR " $(pwd)
echo "DJANGO LAUNCH SERVER ..."

gunicorn --timeout=600 --workers=2 visitationbook.wsgi:application --bind 0.0.0.0:8000

exec "$@"
