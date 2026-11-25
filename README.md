# dev-doctor

Agent khusus **debugging, koding, website, dan jaringan**, dibangun dengan
Mistral Agents SDK (`mistralai-agents`), plus **web chat UI** untuk memakai
agent langsung dari browser.

## Struktur monorepo

```
apps/agent/   # agent dev-doctor (Mistral Agents SDK, tools http_probe + dns_lookup)
apps/api/     # web app (FastAPI): chat UI di "/" dan POST /api/chat/run
```

## Kemampuan agent

- **Debugging** — pacari akar masalah, reproduksi minimal, perbaikan + cara verifikasi.
- **Koding** — baca file, jalankan kode & test di sandbox, tampilkan patch.
- **Website** — probe endpoint (`http_probe`: status, latensi, header), diagnosa DNS → TCP → TLS → HTTP.
- **Jaringan** — sandbox dengan akses jaringan penuh: `curl`, `dig`, `ping`, dsb.

| Alat | Fungsi |
| --- | --- |
| `http_probe` | Cek endpoint HTTP(S): status code, latensi, header penting, cuplikan body saat error |
| `dns_lookup` | Resolusi hostname ke IPv4/IPv6 |

## Menjalankan agent (apps/agent)

1. Salin `apps/agent/.env.example` menjadi `apps/agent/.env` dan pilih salah satu backend:

   - **Mistral** (default): isi `MISTRAL_API_KEY`
     (butuh role `cloud_user` untuk `MistralSandbox`).
   - **Gateway OpenAI-compatible** (Xkiro / OpenRouter, mendukung model gratis):
     isi `OPENROUTER_API_KEY`, set `DEV_DOCTOR_BACKEND=openrouter` dan
     `DEV_DOCTOR_BASE_URL` (Xkiro: `https://api.xkiro.com/v1`).

   Model lain bisa di-set lewat `DEV_DOCTOR_MODEL` (misal `cohere/command-a`).
2. Jalankan:

```bash
cd apps/agent
uv sync
uv run --env-file .env agents chat
```

## Web app (apps/api)

- `GET /` — chat UI (dark theme, Bahasa Indonesia). API key pengunjung disimpan
  di localStorage browser, **tidak pernah** disimpan di server.
- `POST /api/chat/run` — body `{api_key, base_url, model, messages}`; server
  menjalankan loop agent + tools dan mengembalikan `{reply, steps}`.

### Pengembangan

```bash
uv sync --all-packages
uv run pytest apps/api/tests -q
```

### Deploy (Mistral Apps)

```bash
mistral deploy
```

## Tes agent (tanpa API key)

```bash
cd apps/agent
uv run pytest tests/ -q
```

## Deploy agent terkelola

```bash
cd apps/agent
uv run --env-file .env agents deploy
```

Deploy mendaftarkan agent sebagai workflow bernama `dev-doctor`. Panggil dengan
`agents.Agent.load_from(agent_name="dev-doctor")`.
