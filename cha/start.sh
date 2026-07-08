#!/bin/sh
set -e

echo "Starting database setup..."

python seed.py

echo "Starting Gunicorn..."

exec gunicorn -c gunicorn.conf.py app:app
