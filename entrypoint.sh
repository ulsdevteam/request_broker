#!/bin/bash

echo "Waiting for PostgreSQL..."

# Create config.py if it doesn't exist
if [ ! -f request_broker/config.py ]; then
    echo "Creating config file"
    cp request_broker/config.py.example request_broker/config.py
fi

./wait-for-it.sh db:5432 -- echo "Apply database migrations"
python manage.py migrate

#Start server
echo "Starting server"
if [ "$1" == "apache" ]
then
    apache2ctl -D FOREGROUND
else
    python manage.py runserver 0.0.0.0:${APPLICATION_PORT}
fi
