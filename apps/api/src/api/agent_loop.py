"""Server-side agent loop dev-doctor: memanggil gateway OpenAI-compatible apa pun
dengan key dari pengunjung (tidak ada kredensial di server), menjalankan tool
`http_probe` dan `dns_lookup`, lalu merangkai jawaban akhir.
"""

import asyncio
import json
import socket
import time

import httpx

INSTRUCTIONS = """\
Kamu adalah dev-doctor, agen ahli debugging, koding, website, dan jaringan.
Jawab dalam bahasa user (default Bahasa Indonesia). Kamu tidak punya sandbox; gunakan
dua tool berikut untuk pengamatan:
- http_probe: cek endpoint HTTP(S) — status code, latensi, header penting.
- dns_lookup: resolusi hostname ke IPv4/IPv6.
Urutan diagnosis: DNS → TCP/TLS → HTTP → aplikasi. Format jawaban: temuan utama dulu,
lalu bukti (output tool), lalu langkah perbaikan bernomor. Jangan mengarang output
perintah yang tidak kamu jalankan. Jangan pernah minta/menampilkan rahasia (API key,
token, password).
"""

MAX_STEPS = 8

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "http_probe",
            "description": "Cek endpoint HTTP(S): status code, latensi, header penting. Untuk diagnosa website/API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL lengkap dengan https://"},
                    "timeout_seconds": {"type": "number", "description": "Batas waktu, default 10"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dns_lookup",
            "description": "Resolusi hostname ke IPv4/IPv6. Pakai ini pertama saat host tak terjangkau.",
            "parameters": {
                "type": "object",
                "properties": {"host": {"type": "string", "description": "Hostname tanpa protokol"}},
                "required": ["host"],
            },
        },
    },
]

SELECTED_HEADERS = {"server", "content-type", "content-length", "cache-control", "location"}


async def http_probe(client: httpx.AsyncClient, url: str, timeout_seconds: float = 10.0) -> dict:
    """Probe endpoint HTTP(S): status, latensi, header, cuplikan body saat error."""
    started = time.perf_counter()
    try:
        response = await client.get(url, timeout=timeout_seconds, follow_redirects=True)
        headers = {k.lower(): v for k, v in response.headers.items() if k.lower() in SELECTED_HEADERS}
        return {
            "url": url,
            "reachable": True,
            "status": response.status_code,
            "elapsed_seconds": round(time.perf_counter() - started, 3),
            "headers": headers,
            "body_snippet": response.text[:512] if response.status_code >= 400 else "",
        }
    except httpx.HTTPError as error:
        detail = getattr(error, "response", None)
        message = f"HTTP {detail.status_code}" if detail is not None else f"{type(error).__name__}"
        return {"url": url, "reachable": False, "error": message}


async def dns_lookup(host: str) -> dict:
    """Resolusi hostname ke IPv4/IPv6."""

    def resolve(family: int) -> list[str]:
        infos = socket.getaddrinfo(host, None, family=family)
        return sorted({info[4][0] for info in infos})

    result: dict = {"host": host}
    try:
        result["ipv4"] = await asyncio.to_thread(resolve, socket.AF_INET)
    except socket.gaierror as error:
        result["ipv4_error"] = str(error)
    try:
        result["ipv6"] = await asyncio.to_thread(resolve, socket.AF_INET6)
    except socket.gaierror:
        pass
    return result


async def _dispatch(client: httpx.AsyncClient, name: str, arguments: dict) -> dict:
    if name == "http_probe":
        return await http_probe(client, arguments["url"], float(arguments.get("timeout_seconds", 10.0)))
    if name == "dns_lookup":
        return await dns_lookup(arguments["host"])
    raise ValueError(f"Tool tidak dikenal: {name}")


async def run_chat(base_url: str, api_key: str, model: str, messages: list[dict]) -> tuple[str, list[dict]]:
    """Jalankan loop agent; kembalikan (jawaban_akhir, langkah_tool)."""
    base_url = base_url.rstrip("/")
    steps: list[dict] = []
    history: list[dict] = [{"role": "system", "content": INSTRUCTIONS}, *messages]

    async with httpx.AsyncClient(
        base_url=base_url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=httpx.Timeout(120.0),
    ) as client:
        for _ in range(MAX_STEPS):
            response = await client.post(
                "/chat/completions",
                json={"model": model, "messages": history, "tools": TOOLS, "temperature": 0.2},
            )
            response.raise_for_status()
            payload = response.json()
            if not payload.get("choices"):
                raise RuntimeError(f"Gateway menjawab tanpa pilihan: {json.dumps(payload)[:200]}")
            message = payload["choices"][0]["message"]
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                return message.get("content") or "", steps

            history.append({"role": "assistant", "content": message.get("content"), "tool_calls": tool_calls})
            for call in tool_calls:
                function = call["function"]
                args = json.loads(function.get("arguments") or "{}")
                try:
                    result = await _dispatch(client, function["name"], args)
                except Exception as error:
                    result = {"error": f"{type(error).__name__}: {error}"}
                steps.append({"tool": function["name"], "args": args, "result_summary": _summarize(result)})
                history.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id", function["name"]),
                        "name": function["name"],
                        "content": json.dumps(result, ensure_ascii=False)[:4000],
                    }
                )

    return "Batas langkah diagnosa tercapai sebelum jawaban akhir. Coba percakapan baru.", steps


def _summarize(result: dict) -> str:
    if not result.get("reachable", True):
        return "tak terjangkau"
    if "status" in result:
        return f"HTTP {result['status']} dalam {result.get('elapsed_seconds', '?')}s"
    if "ipv4" in result:
        return ",".join(result["ipv4"]) or "tanpa A record"
    return json.dumps(result)[:80]
