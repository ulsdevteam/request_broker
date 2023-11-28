#!/bin/bash

echo "Waiting for PostgreSQL..."

# Create config.py if it doesn't exist
if [ ! -f request_broker/config.py ]; then
    echo "Creating config file"
    if [[ -n $PROD ]]; then
        envsubst < request_broker/config.py.deploy > request_broker/config.py
    else
        cp request_broker/config.py.example request_broker/config.py
    fi

fi

./wait-for-it.sh $db:$SQL_PORT -- echo "Apply database migrations"
python manage.py migrate

# Collect static files
echo "Collecting static files"
python manage.py collectstatic

chmod 775 /var/www/html/request-broker/static
chown :www-data /var/www/html/request-broker/static

if [[ $AEON_API_KEY ]]; then
    echo "Starting cron"
    cron
fi

#Start server
echo "Starting server"

if [[ -n $PROD ]]; then
    apache2ctl -D FOREGROUND
else
    python manage.py runserver 0.0.0.0:${APPLICATION_PORT}
fi
