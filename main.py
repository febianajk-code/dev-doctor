import asyncio
import os
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from typing import Literal

from mistralai import agents

MAX_BODY_SNIPPET = 512

OPENROUTER_BASE_URL = os.environ.get("DEV_DOCTOR_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODELS = {
    "mistral": "mistral-medium-latest",
    "openrouter": "mistralai/mistral-small-3.2-24b-instruct:free",
}
BACKEND = os.environ.get("DEV_DOCTOR_BACKEND", "mistral").strip().lower()
_model_env = os.environ.get("DEV_DOCTOR_MODEL", "").strip()
if not _model_env:
    if BACKEND == "openrouter" and os.environ.get("DEV_DOCTOR_BASE_URL", "").strip():
        _model_env = "cohere/command-a"
    else:
        _model_env = DEFAULT_MODELS.get(BACKEND, DEFAULT_MODELS["mistral"])
MODEL = _model_env

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
        result["ipv4"] = sorted({address[4][0] for address in socket.getaddrinfo(host, None, family=socket.AF_INET)})
    except socket.gaierror as error:
        result["ipv4_error"] = str(error)
    try:
        result["ipv6"] = sorted({address[4][0] for address in socket.getaddrinfo(host, None, family=socket.AF_INET6)})
    except socket.gaierror:
        pass
    return result


def _docker_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        return subprocess.run(
            [docker, "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10
        ).returncode == 0
    except Exception:
        return False


def _completion_config():
    if BACKEND != "openrouter":
        return None
    from mistralai.vibe.harness.runtime.completion import CompletionConfigBase, CompletionProvider
    from mistralai.vibe.harness.runtime.completion.providers.openai import OpenAICompletionProvider

    class OpenRouterConfig(CompletionConfigBase):
        type: Literal["openrouter_dev_doctor"] = "openrouter_dev_doctor"
        model: str = MODEL
        base_url: str = OPENROUTER_BASE_URL
        api_key_env_var: str = "OPENROUTER_API_KEY"
        context_window: int = 131_072
        max_output_tokens: int = 8_192

        def build_provider(self) -> CompletionProvider:
            return OpenAICompletionProvider(
                api_key=os.environ[self.api_key_env_var],
                model=self.model,
                base_url=self.base_url,
            )

    return OpenRouterConfig(model=MODEL)


_agent_kwargs = dict(
    model=MODEL,
    name="dev-doctor",
    instructions=INSTRUCTIONS,
    tools=[http_probe, dns_lookup],
)

if BACKEND == "openrouter":
    _agent_kwargs["completion"] = _completion_config()
    if _docker_available():
        _agent_kwargs["environment"] = agents.LocalDockerSandbox(network=agents.Network.all())
else:
    _agent_kwargs["environment"] = agents.MistralSandbox(network=agents.Network.all())

agent = agents.Agent(**_agent_kwargs)


async def main() -> None:
    result = await agent.run("Cek https://example.com dan jelaskan kondisinya.")
    if isinstance(result, agents.Completed):
        print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
