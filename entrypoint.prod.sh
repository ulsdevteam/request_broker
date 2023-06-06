#!/bin/bash

./wait-for-it.sh db:${SQL_PORT} -- echo "Apply database migrations"
python manage.py migrate

#Start cron
echo "Starting cron"
cron

#Start server
echo "Starting server"
apache2ctl -D FOREGROUND
