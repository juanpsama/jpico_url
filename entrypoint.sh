#!/bin/sh
set -e

alembic upgrade head

fastapi run app/main.py --port 8000
