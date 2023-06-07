#!/bin/bash

echo "Waiting for PostgreSQL..."

# Create config.py if it doesn't exist
if [ ! -f request_broker/config.py ]; then
    echo "Creating config file"
    cp request_broker/config.py.example request_broker/config.py
fi

./wait-for-it.sh db:${SQL_PORT} -- echo "Apply database migrations"
python manage.py migrate

#Start server
echo "Starting server"
python manage.py runserver 0.0.0.0:${APPLICATION_PORT}
