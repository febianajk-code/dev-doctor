"""Tanpa model dan tanpa API key: cek alat secara langsung dan jalankan agen
dengan model skrip (agents.testing.ScriptedModel)."""

import socket

import pytest
from mistralai import agents

import main


@pytest.fixture(autouse=True)
def no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tes yang lupa override() akan gagal, bukan memanggil model."""
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
    monkeypatch.delenv("MISTRAL_CLIENT_API_KEY", raising=False)


async def test_dns_lookup_resolves_real_host():
    result = await main.dns_lookup("example.com")
    assert result["ipv4"], "example.com harus punya alamat IPv4"
    assert all(socket.inet_pton(socket.AF_INET, address) for address in result["ipv4"])


async def test_http_probe_reports_status():
    result = await main.http_probe("https://example.com")
    assert result["reachable"] is True
    assert result["status"] == 200
    assert result["elapsed_seconds"] >= 0


async def test_http_probe_reports_unreachable_host():
    result = await main.http_probe("https://host-yang-tidak-ada.invalid", timeout_seconds=3)
    assert result["reachable"] is False
    assert "error" in result


async def test_agent_runs_to_completion_without_api_key():
    scripted = agents.testing.ScriptedModel(
        [agents.testing.reply("OK.")]
    )
    offline_agent = agents.Agent(
        model=main.MODEL,
        name="dev-doctor-offline",
        instructions=main.INSTRUCTIONS,
        tools=[main.http_probe, main.dns_lookup],
    ).override(model=scripted)
    result = await offline_agent.run("ping")
    assert isinstance(result, agents.Completed)
    assert result.text == "OK."
