# Auto Learning Enablement Runbook

Runbook ini menyatukan roadmap menjadi langkah operasional yang bisa benar-benar dijalankan.

## Target
Membuat bot mampu menjalankan learning cycle otomatis secara aman, dengan prinsip:
- collect first
- train only when ready
- no blind auto-promotion
- easy rollback

## Current Safe Baseline
Sebelum mengaktifkan auto-learning cadence:
- active profile: `dry_run`
- kill switch: reviewed
- `EMERGENCY_STOP=true`
- ops panel healthy
- learning cycle runner healthy

## Step 1 - Verify data collection really works
Checklist:
- backend menerima analyze requests
- decision log bertambah
- closed trade result masuk
- `decision_id` ikut tersimpan bila path MT5 terbaru sudah dipakai

Verify:
```bash
python scripts/build_decision_dataset.py
python scripts/build_trade_dataset.py
python scripts/check_dataset_readiness.py
```

Pass condition:
- dataset files ada
- tidak crash
- readiness report terbentuk

## Step 2 - Verify learning runner
Run:
```bash
python scripts/run_learning_cycle.py
```

Pass condition:
- `data/learning/learning_cycle_status.json` ada
- `data/learning/learning_cycle_history.jsonl` ada
- `/ops` menampilkan learning cycle

## Step 3 - Install scheduler
Windows target:
- ikuti `WINDOWS_LEARNING_SCHEDULER.md`

Recommended starting cadence:
- every 6 hours

Why:
- cukup sering untuk observability
- tidak terlalu agresif
- readiness gate mencegah training prematur

## Step 4 - Watch readiness progression
Gunakan `/ops` untuk memantau:
- readiness level
- decision_rows
- closed_trades
- symbol_count
- timeframe_count
- session_count
- readiness notes

Interpretation:
- `insufficient_data`: kumpulkan data dulu
- `analytics_ready`: analytics mulai layak dibaca
- `training_ready`: candidate training boleh jalan
- `promotion_ready`: dataset cukup besar untuk promotion review, bukan auto-promotion liar

## Step 5 - Candidate workflow
Saat readiness mencapai `training_ready`:
- runner akan mengizinkan `train_setup_model.py`
- runner akan mengizinkan `evaluate_setup_model.py`
- promotion tetap manual approval

What to inspect:
- `models/reports/model_evaluation.json`
- `data/exports/adaptive_report.json`
- `data/exports/rollback_trigger_check.json`
- `/ops`

## Step 6 - Promotion discipline
Current rule:
- jangan auto-promote model dulu
- jangan auto-apply config besar dulu

Allowed flow for now:
1. runner prepare evidence
2. operator review candidate metrics
3. operator review rollback signals
4. operator manually decide promote/apply

## Step 7 - Migration safety
Kalau pindah RDP/host:
- gunakan `RDP_MIGRATION_CHECKLIST.md`
- start again from safe mode
- rerun `python scripts/run_learning_cycle.py`
- verify `/ops`

## What “Done” Means For Auto-Learning Foundation
Fondasi auto-learning dianggap selesai jika:
- data collection hidup
- readiness gating hidup
- scheduled learning runner hidup
- learning status terlihat di `/ops`
- candidate train/evaluate bisa jalan otomatis saat layak
- promotion masih bounded dengan approval

## What Is Explicitly Not Done Yet
Ini penting supaya tidak overclaim:
- auto-promote model fully otomatis
- auto-apply config tanpa review
- self-modifying strategy loop tanpa batas
- guaranteed profitable learning loop

## Recommendation
Use this as the operating sequence:
1. collect
2. observe
3. validate readiness
4. train candidate
5. evaluate candidate
6. manual approval
7. cautious rollout
8. rollback if needed
