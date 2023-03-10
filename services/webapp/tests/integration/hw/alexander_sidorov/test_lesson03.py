import httpx
import pytest

pytestmark = [
    pytest.mark.anyio,
    pytest.mark.integration,
]


async def test_lesson03_happy(web_client: httpx.AsyncClient) -> None:
    resp: httpx.Response = await web_client.get("/~/alexander_sidorov")
    assert resp.status_code == 200
    assert "Hello from Alexander Sidorov" in resp.text


async def test_lesson03_fail_path(web_client: httpx.AsyncClient) -> None:
    resp: httpx.Response = await web_client.get("/~/alexander_sidorov/")
    assert resp.status_code == 200
    assert "Hello from Alexander Sidorov" not in resp.text
