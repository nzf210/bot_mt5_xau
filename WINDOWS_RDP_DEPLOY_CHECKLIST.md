# Windows RDP Deploy Checklist - MT5 AI Bot

Checklist ini untuk target runtime Windows RDP, dengan prioritas provider berbasis CLI/session-auth, bukan API key.

## 1. Persiapan mesin
- [ ] Pastikan Windows update dasar sudah selesai
- [ ] Pastikan Python 3.10+ terpasang (`py --version`)
- [ ] Pastikan Node.js + npm terpasang (`node -v`, `npm -v`)
- [ ] Pastikan MT5 sudah terpasang jika bot akan dihubungkan langsung
- [ ] Pastikan akun RDP yang dipakai punya akses login browser untuk auth CLI

## 2. Ambil project
- [ ] Copy atau clone folder `mt5_ai_bot` ke mesin Windows
- [ ] Buka PowerShell di folder project

## 3. Siapkan Python env
```powershell
cd mt5_ai_bot
py -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```
- [ ] Verifikasi `pip install -r requirements.txt` sukses

Jika activation diblok:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\activate
```

## 4. Install Gemini CLI
- [ ] Install Gemini CLI sesuai metode yang berlaku di mesin target
- [ ] Verifikasi `gemini --version`
- [ ] Login/auth Gemini CLI di mesin itu
- [ ] Verifikasi Gemini CLI bisa dipanggil dari terminal RDP session

## 5. Install Codex CLI
```powershell
npm install -g @openai/codex
```
- [ ] Verifikasi `codex --version`

## 6. Login Codex via ChatGPT session
- [ ] Jalankan `codex`
- [ ] Pilih sign in with ChatGPT
- [ ] Selesaikan login di browser
- [ ] Jika browser callback tidak nyaman di RDP/headless-ish setup, coba device auth:
```powershell
codex login --device-auth
```
- [ ] Pastikan session login tersimpan dan `codex` bisa dibuka lagi tanpa error auth langsung

## 7. Konfigurasi env bot
```powershell
copy .env.example .env
```
Edit `.env` minimal menjadi seperti ini:
```env
GEMINI_PROVIDER_PRIORITY=gemini_cli,openai_cli,gemini_api
GEMINI_CLI_ENABLED=true
OPENAI_CLI_ENABLED=true
GEMINI_API_ENABLED=false
EMERGENCY_STOP=true
ALLOW_LIVE_TRADING=false
ENABLE_VISION=false
```

Catatan:
- `OPENAI_CLI_ENABLED=true` hanya setelah `codex` benar-benar terpasang dan login sukses
- `GEMINI_API_ENABLED=false` direkomendasikan untuk mode non-API-first
- untuk fase awal, tetap mulai dari `EMERGENCY_STOP=true`

## 8. Jalankan API
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
- [ ] Pastikan server start tanpa traceback

## 9. Smoke test endpoint
```powershell
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/ops/summary
```
- [ ] `/health` return 200
- [ ] `/ops/summary` return 200

## 10. Smoke test control panel
- [ ] Buka `http://127.0.0.1:8000/ops`
- [ ] Pastikan panel tampil
- [ ] Pastikan provider list menampilkan `gemini_cli`, `openai_cli`, `gemini_api`
- [ ] Pastikan profile selector berfungsi
- [ ] Pastikan kill switch action berfungsi

## 11. Verifikasi provider readiness
Di panel `/ops` atau dari `/ops/summary`, cek:
- [ ] `gemini_cli` status `ready`
- [ ] `openai_cli` status `ready` jika Codex CLI sudah terpasang + login
- [ ] `gemini_api` boleh `not_ready` bila memang dinonaktifkan

Jika `openai_cli` belum ready:
- cek `codex --version`
- cek login Codex masih aktif
- restart terminal RDP session lalu coba lagi

## 12. Test analyze path
```powershell
curl -X POST http://127.0.0.1:8000/analyze ^
  -H "Content-Type: application/json" ^
  --data @data/sample_market_request.json
```
- [ ] Pastikan endpoint merespons JSON valid
- [ ] Cek event log/provider selection bila perlu

## 13. Mode aman sebelum MT5 live wiring
- [ ] Active profile = `dry_run`
- [ ] Kill switch = `false` hanya kalau memang mau test flow end-to-end
- [ ] `EMERGENCY_STOP=true` untuk test awal
- [ ] Jangan aktifkan live trading dulu

## 14. Wiring ke MT5
- [ ] Tambahkan `http://127.0.0.1:8000` ke allowed WebRequest URLs di MT5
- [ ] Copy `mt5/AiTraderEA.mq5` ke folder Experts
- [ ] Compile di MetaEditor
- [ ] Attach EA ke satu chart dulu
- [ ] Start dari `DryRun=true`

## 15. Setelah stabil
Baru pertimbangkan langkah bertahap:
- [ ] `profile=demo`
- [ ] `EMERGENCY_STOP=false`
- [ ] validasi hasil demo
- [ ] baru diskusikan live kecil

## Troubleshooting singkat
### `openai_cli` not ready
- `codex` belum terinstall
- login ChatGPT belum selesai
- terminal belum restart setelah install

### `gemini_cli` not ready
- Gemini CLI belum terinstall
- login Gemini belum aktif di user session yang sama

### panel tampil tapi action gagal
- cek `python-multipart` terinstall
- cek server log FastAPI

### venv gagal dibuat
- install Python yang lengkap, termasuk `venv`
- atau reinstall Python dari installer resmi dengan pip/venv enabled

## Recommended first boot state
```env
GEMINI_PROVIDER_PRIORITY=gemini_cli,openai_cli,gemini_api
GEMINI_CLI_ENABLED=true
OPENAI_CLI_ENABLED=true
GEMINI_API_ENABLED=false
EMERGENCY_STOP=true
ALLOW_LIVE_TRADING=false
ENABLE_VISION=false
```
