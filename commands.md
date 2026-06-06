fastapi run app/main.py
pytest --benchmark-only
k6 run /tests/benchmark/k6_url_concurrent.ts
k6 run --vus 10 --duration 30s /tests/benchmark/k6_url_concurrent.ts