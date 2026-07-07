from collections.abc import AsyncIterator

import httpx
import pytest

from app.domain.exceptions import ConflictError, DomainError, NotFoundError
from app.main import create_app


@pytest.fixture
async def failing_client() -> AsyncIterator[httpx.AsyncClient]:
    app = create_app()

    @app.get("/boom/not-found")
    async def _not_found() -> None:
        raise NotFoundError("Batch not found.", details={"batch_id": "42"})

    @app.get("/boom/conflict")
    async def _conflict() -> None:
        raise ConflictError("Batch already settled.")

    @app.get("/boom/domain")
    async def _domain() -> None:
        raise DomainError("Business rule violated.")

    @app.get("/boom/crash")
    async def _crash() -> None:
        raise RuntimeError("secret internal detail")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


async def test_not_found_error_maps_to_404(failing_client: httpx.AsyncClient) -> None:
    response = await failing_client.get("/boom/not-found")

    assert response.status_code == 404
    body = response.json()["error"]
    assert body["code"] == "not_found"
    assert body["message"] == "Batch not found."
    assert body["details"] == {"batch_id": "42"}


async def test_conflict_error_maps_to_409(failing_client: httpx.AsyncClient) -> None:
    response = await failing_client.get("/boom/conflict")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_generic_domain_error_maps_to_422(failing_client: httpx.AsyncClient) -> None:
    response = await failing_client.get("/boom/domain")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "domain_error"


async def test_unexpected_error_returns_500_without_leaking_details(
    failing_client: httpx.AsyncClient,
) -> None:
    response = await failing_client.get("/boom/crash")

    assert response.status_code == 500
    body = response.json()["error"]
    assert body["code"] == "internal_error"
    assert "secret" not in response.text


async def test_unknown_route_returns_error_envelope(failing_client: httpx.AsyncClient) -> None:
    response = await failing_client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "http_error"
