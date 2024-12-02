#!/bin/sh
# Relatives path from WORKDIR
# https://misc.flogisoft.com/bash/tip_colors_and_formatting
echo "WORKDIR " $(pwd)

echo "Install python requirements ..."
pip install -r requirements.txt

echo "Collect and centralize statics files ..."
python manage.py collectstatic --noinput

echo "Make Migration ..."
python manage.py makemigrations

echo "Migrate data ..."
python manage.py migrate

# python manage.py createsuperuser

# python manage.py shell

exec "$@"
