# Windows CLI Provider Setup

Panduan ini menjelaskan setup provider CLI di Windows / RDP untuk mt5_ai_bot.

## Goal
Menentukan provider mana yang benar-benar siap dipakai bot di mesin Windows:
- `gemini_cli`
- `openai_cli` (opsional, hanya jika tool yang cocok memang tersedia)

## Important Reality
Bot memanggil executable CLI yang ada di mesin. Jadi provider tidak akan bekerja hanya karena flag `.env` diaktifkan.

Agar provider siap, harus lolos tiga hal:
1. tool CLI terinstall
2. tool CLI bisa dijalankan dari terminal
3. auth/login untuk tool itu sudah selesai

---

## A. Gemini CLI

### 1. Install
Gunakan metode instalasi Gemini CLI yang memang berlaku di mesin kamu. Setelah install, command ini harus berhasil:

```powershell
gemini --version
```

### 2. Login / auth
Jalankan:

```powershell
gemini
```

Kalau CLI meminta login/auth, selesaikan flow itu dulu.

### 3. Verify readiness
Minimal cek:

```powershell
gemini --version
gemini
```

Kalau dua command ini tidak bekerja, jangan anggap `gemini_cli` siap.

### 4. Recommended `.env`
Kalau Gemini CLI adalah jalur utama:

```env
GEMINI_PROVIDER_PRIORITY=gemini_cli,gemini_api
GEMINI_CLI_ENABLED=true
OPENAI_CLI_ENABLED=false
GEMINI_API_ENABLED=false
```

Kalau ingin CLI-only keras:

```env
GEMINI_PROVIDER_PRIORITY=gemini_cli
GEMINI_CLI_ENABLED=true
OPENAI_CLI_ENABLED=false
GEMINI_API_ENABLED=false
```

---

## B. OpenAI / Codex CLI Path

## Current status
Path ini bersifat **opsional** dan **tool-dependent**.
Bot saat ini punya scaffold `openai_cli`, tapi mesin harus benar-benar punya tool yang cocok.

### 1. Check whether a compatible CLI exists
Cek ini di terminal Windows:

```powershell
codex --version
openai --version
chatgpt --version
```

Interpretasi:
- jika semuanya `command not found`, maka `openai_cli` belum siap di mesin ini
- jika salah satu ada, baru lanjut ke auth/login tool tersebut

### 2. Auth/login
Auth mengikuti tool yang dipakai. Bot tidak melakukan login GPT dari dalam aplikasi.

Artinya:
- login harus terjadi di level CLI tool
- setelah tool terinstall dan login sukses, baru `OPENAI_CLI_ENABLED=true` masuk akal

### 3. Recommended `.env`
Aktifkan hanya jika tool benar-benar tersedia dan lolos verifikasi:

```env
GEMINI_PROVIDER_PRIORITY=gemini_cli,openai_cli,gemini_api
GEMINI_CLI_ENABLED=true
OPENAI_CLI_ENABLED=true
GEMINI_API_ENABLED=false
```

Kalau OpenAI/Codex CLI belum ada, **jangan** aktifkan `OPENAI_CLI_ENABLED=true`.

---

## C. Troubleshooting `/analyze` 502
Kalau backend hidup tapi `/analyze` memberi `502 Bad Gateway`, penyebab paling umum:
- provider priority menunjuk ke tool yang belum siap
- CLI belum terinstall
- CLI belum login/auth
- subprocess CLI gagal di Windows

### Quick checks
```powershell
gemini --version
codex --version
openai --version
chatgpt --version
```

### Practical rule
- kalau Gemini CLI siap, pakai Gemini dulu
- kalau OpenAI/Codex CLI tidak ada, jangan berharap fallback ke sana
- jangan enable provider yang belum lolos verifikasi command

---

## D. Operator Recommendation
Untuk start yang paling aman di Windows RDP:
1. siapkan `gemini_cli` dulu
2. pastikan `gemini --version` dan `gemini` berjalan
3. pakai `.env` yang hanya mengandalkan provider yang benar-benar siap
4. uji `/health`, `/ops`, lalu `/analyze`
5. baru pertimbangkan OpenAI/Codex path jika tool CLI yang cocok memang tersedia
