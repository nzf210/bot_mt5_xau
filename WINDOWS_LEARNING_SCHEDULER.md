# Windows Learning Scheduler

Panduan ini untuk menjalankan learning cycle secara terjadwal di Windows RDP menggunakan Task Scheduler.

## Goal
Menjalankan pipeline berikut secara otomatis:
- build decision dataset
- build trade dataset
- check dataset readiness
- run adaptive analytics
- check rollback trigger
- train/evaluate candidate model hanya jika readiness mengizinkan

Runner utamanya:
- `scripts/run_learning_cycle.py`

## Recommended Frequency
- Every 6 hours untuk analytics + readiness monitoring
- Daily untuk training cadence awal juga masih aman, tapi runner ini sudah punya gate internal, jadi eksekusi lebih sering tidak otomatis melatih model bila data belum cukup

## Basic Command
Gunakan Python yang memang dipakai bot di Windows.

Example:
```powershell
cd C:\path\to\mt5_ai_bot
python scripts\run_learning_cycle.py
```

## Outputs
Runner akan menulis:
- `data/learning/learning_cycle_status.json`
- `data/learning/learning_cycle_history.jsonl`

Dan tetap memakai output yang sudah ada:
- `data/exports/dataset_readiness.json`
- `data/exports/adaptive_report.json`
- `data/exports/rollback_trigger_check.json`
- `models/reports/model_evaluation.json`

## Task Scheduler Setup
1. Open Task Scheduler
2. Create Task
3. General:
   - Name: `MT5 AI Bot Learning Cycle`
   - Run whether user is logged on or not (optional, if needed)
4. Triggers:
   - New Trigger
   - Daily
   - Repeat task every: `6 hours`
5. Actions:
   - Program/script: path to `python.exe`
   - Add arguments: `scripts\run_learning_cycle.py`
   - Start in: `C:\path\to\mt5_ai_bot`
6. Conditions/Settings:
   - Allow task to be run on demand
   - If task fails, restart every 30 minutes, up to 3 times

## Safety Notes
- Runner ini **tidak auto-promote model**
- Runner ini **tidak auto-apply config baru**
- Promotion tetap manual approval
- Training/evaluation hanya jalan jika readiness level sudah `training_ready` atau `promotion_ready`

## Suggested Next Integration
Setelah scheduler ini aktif, tahap berikutnya adalah menampilkan isi `learning_cycle_status.json` ke `/ops` panel.
