from datetime import datetime, UTC

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session

from app.core.config import settings
from app.core.db import engine, get_db_session
from app.main import app
from app.services.url_map_service import BASE62_ALPHABET, MAX_VAL, PRIME

BATCH_SIZE = 5000
TOTAL = 500000


def _encode_base62(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0] * 4
    chars = []
    while num > 0:
        remainder = num % 62
        chars.append(BASE62_ALPHABET[remainder])
        num //= 62
    while len(chars) < 4:
        chars.append(BASE62_ALPHABET[0])
    return "".join(reversed(chars))


def _generate_short_code(base_id: int) -> str:
    obfuscated_id = (base_id * PRIME) % MAX_VAL
    return _encode_base62(obfuscated_id)


def _seed_data(cur, conn, start, count):
    now = datetime.now(UTC)
    end = start + count - 1
    for batch_start in range(start, end + 1, BATCH_SIZE):
        batch_end = min(batch_start + BATCH_SIZE - 1, end)
        with cur.copy("COPY urlmap (original_url, create_date, short_url_code) FROM STDIN") as copy:
            for i in range(batch_start, batch_end + 1):
                copy.write_row([f"https://example.com/{i}", now, _generate_short_code(i)])
        conn.commit()


@pytest.fixture(scope="session", autouse=True)
def seeded_db():
    conn = psycopg.connect(
        host=settings.POSTGRES_SERVER,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )
    conn.autocommit = False
    cur = conn.cursor()
    try:
        SQLModel.metadata.create_all(engine)

        cur.execute("SELECT COALESCE(MIN(id), 1), COALESCE(MAX(id), 0), COUNT(*) FROM urlmap")
        first_id, last_id, count = cur.fetchone()

        missing = TOTAL - count
        if missing > 0:
            _seed_data(cur, conn, start=last_id + 1, count=missing)
        
    finally:
        cur.close()
        conn.close()

    yield {
        "generate_short_code": _generate_short_code,
        "start": first_id,
        "total": last_id + max(missing, 0),
    }


@pytest.fixture(scope="function")
def session():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="function")
def client(session: Session):
    def override_get_db_session():
        yield session

    app.dependency_overrides[get_db_session] = override_get_db_session
    with TestClient(app, follow_redirects=False) as client:
        yield client
    app.dependency_overrides.clear()
