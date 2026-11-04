from concurrent.futures import ThreadPoolExecutor
from time import monotonic


def test_health_endpoint_handles_parallel_smoke_load(client):
    request_count = 40
    started = monotonic()
    with ThreadPoolExecutor(max_workers=10) as pool:
        responses = list(pool.map(lambda _: client.get("/"), range(request_count)))
    elapsed = monotonic() - started

    assert len(responses) == request_count
    assert all(response.status_code == 200 for response in responses)
    assert elapsed < 30, f"{request_count} local health checks took {elapsed:.2f}s"
