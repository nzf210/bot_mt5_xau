# Autopilot Mode Spec

## Tujuan
Menyederhanakan operasi bot dengan satu konsep mode operasi yang jelas, tanpa menghilangkan guardrail.

## Config Baru
```env
AUTOPILOT_MODE=off
AUTOPILOT_SCOPE=demo_learning
AUTOPILOT_ALLOW_CONFIG_TUNING=true
AUTOPILOT_ALLOW_MODEL_PROMOTION=false
AUTOPILOT_REQUIRE_APPROVAL_FOR_MAJOR_CHANGES=true
AUTOPILOT_SCHEDULER_ENABLED=true
AUTOPILOT_CADENCE_HOURS=6
```

## Mode
### off
- Tidak ada auto mutation
- Aman untuk observasi, debug, dan dry-run

### semi
- Auto collect data
- Auto run learning cycle jika scheduler aktif
- Auto train/evaluate candidate saat readiness cukup
- Auto prepare recommendation artifacts
- Boleh auto-apply parameter low-risk jika flag mengizinkan
- Tidak boleh auto-promote model utama
- Tidak boleh auto-enable live trading

### full
- Semua perilaku `semi`
- Boleh bounded auto-apply lebih luas jika gate kuat
- Model promotion hanya boleh jika flag promotion aktif, rollback sehat, dan approval policy mengizinkan
- Tetap tidak boleh mengaktifkan live trading secara diam-diam

## Scope
### demo_learning
- Fokus: demo execution + data collection + learning
- `ALLOW_LIVE_TRADING` tetap false

### observe_only
- Fokus: observasi dan logging tanpa execute

### guarded_live
- Scope masa depan, tidak boleh aktif hanya karena autopilot penuh tanpa guard tambahan

## Prinsip
- Safety > autonomy
- Tidak ada implicit live enable
- Perubahan besar tetap butuh approval jika flag approval aktif
- Rollback harus siap sebelum autonomy dinaikkan

## Implementasi saat ini
Sudah ada:
- config autopilot
- resolver status autopilot
- status autopilot di ops summary
- learning cycle awareness terhadap mode autopilot
- approval/apply gating dasar berdasarkan autopilot
- runtime guardrail resolver untuk mode `semi/full` pada threshold profil efektif
- runtime local-engine preset resolver untuk mode `semi/full`

Belum otomatis:
- mutate `.env`
- change active profile di host/EA
- enable scheduler dari backend
- auto-enable live trading
- policy engine penuh untuk semua edge case
