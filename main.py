import asyncio
import socket
import time
import urllib.error
import urllib.request

from mistralai import agents

MAX_BODY_SNIPPET = 512

INSTRUCTIONS = """\
Kamu adalah dev-doctor, agen ahli untuk debugging, koding, website, dan jaringan.
Jawab dalam bahasa yang dipakai user (default: Bahasa Indonesia). Prinsip kerja:

1. DEBUGGING
   - Selalu pacari akar masalah (root cause), jangan asal tempel perbaikan.
   - Reproduksi dulu, kecilkan cakupan (minimal reproduction), baru perbaiki.
   - Baca pesan error dan stack trace baris demi baris; sebutkan file dan barisnya.
   - Usulkan minimal satu cara verifikasi bahwa perbaikan benar-benar berhasil.

2. KODING
   - Kamu punya sandbox: gunakan bash untuk membaca file, menjalankan kode, dan
     menjalankan test. Jangan menebak isi file — baca dulu.
   - Ikuti gaya kode yang sudah ada di proyek user; ubah selayout mungkin.
   - Tampilkan patch/diff yang jelas, lalu jalankan test yang relevan di sandbox.

3. WEBSITE
   - Untuk masalah situs/API: probe endpoint dengan alat `http_probe` (status code,
     latensi, header penting seperti server/content-type). Gunakan bash + curl
     untuk kasus yang lebih detail: redirect, TLS, header permintaan tertentu.
   - Bedakan masalah sisi klien, jaringan, dan server (4xx vs 5xx vs timeout).

4. JARINGAN
   - Kamu punya akses jaringan penuh di sandbox. Gunakan curl, dig/nslookup,
     ping, dan sejenisnya untuk diagnosis: DNS, konektivitas, latensi, TLS.
   - Gunakan alat `dns_lookup` untuk resolusi nama, lalu sambungkan temuannya
     dengan gejala yang dilaporkan user.
   - Urutan diagnosis: DNS → konektivitas TCP → TLS → HTTP → aplikasi.

Format jawaban: temuan utama dulu, lalu bukti (output perintah/skor/latensi),
lalu langkah perbaikan konkret bernomor. Jangan pernah mengarang output perintah
yang tidak kamu jalankan. Kalau informasi kurang, tanya satu pertanyaan yang
paling menentukan. Jangan pernah minta atau tampilkan rahasia (API key, token,
password) — kalau user menempelkannya, ingatkan untuk merotasinya.
"""


@agents.tool
async def http_probe(url: str, timeout_seconds: float = 10.0) -> dict:
    """Probe an HTTP(S) endpoint and report status code, latency, and key response headers.

    Use it as the first check for any website or API problem. Returns the final status code,
    total elapsed time in seconds, selected response headers, and a short body snippet when
    the response is an error.
    """
    started = time.perf_counter()
    try:
        request = urllib.request.Request(url, method="GET", headers={"User-Agent": "dev-doctor/0.1"})
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status = response.status
            headers = {
                name.lower(): value
                for name, value in response.headers.items()
                if name.lower() in {"server", "content-type", "content-length", "cache-control", "location"}
            }
            body = response.read(MAX_BODY_SNIPPET)
    except urllib.error.HTTPError as error:
        status = error.code
        headers = {
            name.lower(): value
            for name, value in error.headers.items()
            if name.lower() in {"server", "content-type", "content-length", "cache-control", "location"}
        }
        body = error.read(MAX_BODY_SNIPPET)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"url": url, "reachable": False, "error": f"{type(error).__name__}: {error.reason if hasattr(error, 'reason') else error}"}
    return {
        "url": url,
        "reachable": True,
        "status": status,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "headers": headers,
        "body_snippet": body.decode("utf-8", errors="replace") if status >= 400 else "",
    }


@agents.tool
async def dns_lookup(host: str) -> dict:
    """Resolve a hostname to its IPv4 and IPv6 addresses.

    Use it first when a host seems unreachable, before checking TCP or HTTP.
    """
    result: dict = {"host": host}
    try:
        result["ipv4"] = [address[4][0] for address in socket.getaddrinfo(host, None, family=socket.AF_INET)]
    except socket.gaierror as error:
        result["ipv4_error"] = str(error)
    try:
        result["ipv6"] = [address[4][0] for address in socket.getaddrinfo(host, None, family=socket.AF_INET6)]
    except socket.gaierror:
        pass
    return result


agent = agents.Agent(
    model="mistral-large-4",
    name="dev-doctor",
    instructions=INSTRUCTIONS,
    tools=[http_probe, dns_lookup],
    environment=agents.MistralSandbox(network=agents.Network.all()),
)


async def main() -> None:
    result = await agent.run("Cek https://example.com dan jelaskan kondisinya.")
    if isinstance(result, agents.Completed):
        print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
