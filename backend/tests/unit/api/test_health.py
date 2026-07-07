import httpx


async def test_liveness_returns_ok(client: httpx.AsyncClient) -> None:
    response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readiness_returns_503_when_database_unavailable(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable", "checks": {"database": "error"}}
