#!/bin/bash
set -e

# TEMPORARY: migrate/seed_event_types disabled to test whether psycopg
# import works at request runtime even though it fails on manage.py
# invocations during this build container. Restore once confirmed.
echo "Skipping migrate/seed_event_types for runtime diagnostic"
