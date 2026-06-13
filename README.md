# jpico_url

A URL shortener built as a hands-on study-case for practicing scaling techniques and backend performance knowledge. The project explores caching strategies, database connection pool management, and load testing under high concurrency.

**Stack:** FastAPI + SQLModel + PostgreSQL + Redis + Alembic

## Benchmark results

Stress test results comparing cache-aside vs direct-database reads under 200, 1000, and 5000 concurrent VUs are documented in [tests/benchmark/k6/RESULTS.md](tests/benchmark/k6/RESULTS.md).
