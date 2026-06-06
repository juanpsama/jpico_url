import random

from fastapi.testclient import TestClient
from sqlmodel import Session


class TestUrlMapBenchmark:

    def test_url_response(
        self, benchmark, client: TestClient, session: Session, seeded_db
    ):
        generate_short_code = seeded_db["generate_short_code"]
        start = seeded_db["start"]
        total = seeded_db["total"]
        def make_request():
            # This code may or not be adding a couple microsecons to the benchmark
            # Take into account for future analisis of the results
            counter = random.randint(start, total)
            short_code = generate_short_code(counter)
            
            response = client.get(f"/{short_code}")
            assert response.status_code == 302

        benchmark(make_request)
