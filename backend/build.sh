#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate

echo "Seeding event types..."
python manage.py seed_event_types
