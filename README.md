# dev-doctor

Agent khusus **debugging, koding, website, dan jaringan**, dibangun dengan
Mistral Agents SDK (`mistralai-agents`).

## Kemampuan

- **Debugging** — pacari akar masalah, reproduksi minimal, perbaikan + cara verifikasi.
- **Koding** — baca file, jalankan kode & test di sandbox, tampilkan patch.
- **Website** — probe endpoint (`http_probe`: status, latensi, header), diagnosa DNS → TCP → TLS → HTTP.
- **Jaringan** — sandbox dengan akses jaringan penuh: `curl`, `dig`, `ping`, dsb.

## Alat bawaan (custom tools)

| Alat | Fungsi |
| --- | --- |
| `http_probe` | Cek endpoint HTTP(S): status code, latensi, header penting, cuplikan body saat error |
| `dns_lookup` | Resolusi hostname ke IPv4/IPv6 |

## Menjalankan

1. Salin `.env.example` menjadi `.env` dan isi `MISTRAL_API_KEY`
   (butuh role `cloud_user` untuk `MistralSandbox`).
2. Jalankan:

```bash
uv sync
uv run --env-file .env agents chat
```

## Tes offline (tanpa API key)

```bash
uv run pytest tests/
```

## Deploy terkelola

```bash
uv run --env-file .env agents deploy
```

Deploy mendaftarkan agent sebagai workflow bernama `dev-doctor`. Karena
sandbox-nya memakai identitas sesi (on-behalf-of), deployment otomatis
*hardened*. Panggil dengan `agents.Agent.load_from(agent_name="dev-doctor")`.
