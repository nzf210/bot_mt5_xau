# RDP Migration Checklist

Checklist ini menjawab pertanyaan: kalau tiba-tiba pindah ke Windows RDP/host baru, file mana yang wajib ikut, mana yang optional, dan mana yang jangan ikut dicopy mentah.

## Prinsip
Tujuannya ada 3:
1. bot bisa jalan lagi
2. histori penting tidak hilang
3. runtime state lama tidak bikin host baru kacau

## WAJIB COPY
Ini yang sebaiknya ikut dipindahkan.

### 1. Source code dan docs
Copy seluruh project source:
- `app/`
- `scripts/`
- `mt5/`
- `requirements.txt`
- `README.md`
- `SOP.md`
- `CHECKLIST_DAILY.md`
- `CHECKLIST_WEEKLY_ADAPTIVE.md`
- `DATASET_THRESHOLD_PLAN.md`
- `PAIR_SESSION_GUARDRAIL_AUDIT.md`
- `PAIR_SESSION_GUARDRAIL_DESIGN.md`
- `AUTONOMY_ROADMAP.md`
- `LEARNING_LOOP_BACKLOG.md`
- `WINDOWS_RDP_DEPLOY_CHECKLIST.md`
- `WINDOWS_LEARNING_SCHEDULER.md`

### 2. Environment / config basis
- `.env` if you want the exact same runtime configuration
- `.env.example` as fallback reference

Catatan:
- `.env` sangat penting kalau berisi path, provider mode, symbol policy, session allowlist, dan toggle operasional lain
- tapi `.env` juga sensitif, jadi jangan sebar sembarangan

### 3. Durable data yang berguna untuk learning/ops continuity
- `data/bot_state.sqlite3`
- `data/training/decision_dataset.csv`
- `data/training/trade_outcome_dataset.csv`
- `data/exports/dataset_readiness.json`
- `data/exports/adaptive_report.json`
- `data/exports/rollback_trigger_check.json`
- `data/learning/learning_cycle_status.json`
- `data/learning/learning_cycle_history.jsonl`

Kalau ada log keputusan mentah di path lain yang dipakai `.env`, file itu juga wajib ikut.

### 4. Model artifacts kalau ingin continuity model
- `models/current/`
- `models/candidates/`
- `models/reports/`

Kalau model tidak ikut dicopy, bot masih bisa jalan, tapi continuity learning/evaluation hilang.

## OPTIONAL COPY
Ini berguna, tapi tidak selalu wajib.

- `data/sample_market_request.json`
- `data/sample_news_events.json`
- `data/sample_trade_result.json`
- `recommended_config.env` jika nanti file itu dipakai workflow review
- arsip log tambahan jika kamu ingin audit historis

## JANGAN COPY MENTAH TANPA DIPIKIR
Ini justru bisa bikin host baru bingung atau membawa state yang tidak diinginkan.

### 1. Python environment
- `.venv/`
- `__pycache__/`
- `*.pyc`

Lebih aman install ulang dependency di host baru.

### 2. Runtime toggles yang sangat situasional
Pertimbangkan reset/manual review sebelum dipakai di host baru:
- `data/active_profile.json`
- `data/kill_switch.json`

Alasannya:
- profile aktif lama bisa tidak cocok dengan niat deploy baru
- kill switch lama bisa bikin sistem terlihat rusak padahal hanya carry-over state

Best practice setelah migrasi:
- set manual ke mode aman, misalnya `dry_run`
- review kill switch secara eksplisit
- pastikan `EMERGENCY_STOP=true` dulu di awal

### 3. File output yang regenerable jika mau pindahan bersih
Boleh dicopy, boleh direbuild:
- `data/exports/*`
- `data/learning/*`
- `models/reports/*`

Kalau targetmu audit continuity, copy.
Kalau targetmu clean boot, regenerate.

## Practical Minimum Set
Kalau buru-buru dan hanya mau bot cepat hidup lagi di host baru, minimum yang sangat disarankan:
- `app/`
- `scripts/`
- `mt5/`
- `.env`
- `requirements.txt`
- `data/bot_state.sqlite3`
- decision log mentah yang dipakai runtime
- `models/current/` jika model aktif mau dipertahankan

## Best Practice Setelah Pindah
1. Install Python dependency fresh
2. Copy source + `.env`
3. Copy DB/data/model yang memang mau dipertahankan
4. Review path di `.env`
5. Start in safe mode:
   - active profile = `dry_run`
   - kill switch reviewed
   - `EMERGENCY_STOP=true`
6. Jalankan:
   - health check
   - `/ops`
   - `scripts/run_learning_cycle.py`
7. Baru setelah itu cek koneksi MT5/live execution

## Recommendation
Kalau pindah RDP mendadak, strategi terbaik bukan copy seluruh folder mentah, tapi:
- copy source
- copy `.env`
- copy DB/dataset/model penting
- reset runtime toggles situasional
- boot dalam mode aman
