from conftest import build_app
from api.agent_loop import dns_lookup
from fastapi.testclient import TestClient


def test_chat_rejects_unknown_key_format(client: TestClient) -> None:
    res = client.post(
        "/api/chat/run",
        json={"api_key": "bukan-format", "messages": [{"role": "user", "content": "ping"}]},
    )
    assert res.status_code == 422


def test_chat_requires_messages(client: TestClient) -> None:
    res = client.post(
        "/api/chat/run",
        json={"api_key": "sk-or-v1-000000000000000000000000", "messages": []},
    )
    assert res.status_code == 422


def test_index_serves_chat_page() -> None:
    res = TestClient(build_app()).get("/")
    assert res.status_code == 200
    assert b"dev-doctor" in res.content


def test_dns_lookup_reports_unknown_host() -> None:
    import asyncio

    result = asyncio.run(dns_lookup("host-tak-ada-sama-sekali.invalid"))
    assert "ipv4_error" in result
