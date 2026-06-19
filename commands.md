fastapi run app/main.py
pytest --benchmark-only
pytest --benchmark-skip
alembic revision --autogenerate -m "migration message"
alembic downgrade -1
alembic upgrade head
k6 run /tests/benchmark/k6_url_concurrent.ts
k6 run --vus 10 --duration 30s /tests/benchmark/k6_url_concurrent.ts