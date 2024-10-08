 #!/bin/bash

./wait-for-it.sh $db:${SQL_PORT} -- echo "Apply database migrations"
python manage.py migrate

# Collect static files
echo "Collecting static files"
python manage.py collectstatic

#Start cron
echo "Starting cron"
cron

#Start server
echo "Starting server"
apache2ctl -D FOREGROUND
