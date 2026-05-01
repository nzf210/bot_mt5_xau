# Autopilot Quickstart

## Ringkasan
Autopilot adalah lapisan orkestrasi mode operasi untuk MT5 AI Bot. Tujuannya menyederhanakan operasi tanpa langsung membuka risiko live atau auto-mutation liar.

## Mode
### `AUTOPILOT_MODE=off`
- konservatif
- tidak mengizinkan mutation besar
- training otomatis dibatasi
- cocok untuk observasi/debug

### `AUTOPILOT_MODE=semi`
- collect data
- learning cycle bisa jalan jika scheduler diaktifkan
- train/evaluate candidate saat readiness cukup
- tuning low-risk bisa disiapkan
- promotion model tetap tidak bebas

### `AUTOPILOT_MODE=full`
- semua perilaku `semi`
- dapat menjalankan bounded low-risk tuning apply
- promotion model hanya jika autopilot mengizinkan dan evaluasi merekomendasikan
- rollback signal akan menahan apply otomatis

## Scope
### `AUTOPILOT_SCOPE=observe_only`
- fokus logging/observasi

### `AUTOPILOT_SCOPE=demo_learning`
- fokus demo execution, data collection, learning

### `AUTOPILOT_SCOPE=guarded_live`
- reserved/future-facing, tidak otomatis mengaktifkan live trading

## Env utama
```env
AUTOPILOT_MODE=off
AUTOPILOT_SCOPE=demo_learning
AUTOPILOT_ALLOW_CONFIG_TUNING=true
AUTOPILOT_ALLOW_MODEL_PROMOTION=false
AUTOPILOT_REQUIRE_APPROVAL_FOR_MAJOR_CHANGES=true
AUTOPILOT_SCHEDULER_ENABLED=false
AUTOPILOT_CADENCE_HOURS=6
```

## Apa yang sekarang dipengaruhi autopilot
- learning cycle gating
- approval/apply gating
- runtime profile guardrails efektif
- local engine settings efektif
- /ops visibility

## Apa yang belum otomatis
- tidak mengaktifkan live trading
- tidak memaksa EA ke demo/live dari backend
- tidak menyalakan Windows Task Scheduler
- tidak mengubah `.env` diam-diam

## Cara pakai cepat
1. Set env autopilot sesuai mode yang diinginkan.
2. Restart backend Python.
3. Buka `/ops` dan cek blok Autopilot.
4. Jika perlu, gunakan action `Apply Autopilot Preset to Local Engine`.
5. Pastikan EA MT5 tetap di mode yang benar secara manual.
6. Jika ingin cadence learning, aktifkan scheduler host secara manual.

## Rekomendasi penggunaan
### Aman untuk sekarang
```env
AUTOPILOT_MODE=semi
AUTOPILOT_SCOPE=demo_learning
AUTOPILOT_ALLOW_CONFIG_TUNING=true
AUTOPILOT_ALLOW_MODEL_PROMOTION=false
AUTOPILOT_REQUIRE_APPROVAL_FOR_MAJOR_CHANGES=true
AUTOPILOT_SCHEDULER_ENABLED=true
AUTOPILOT_CADENCE_HOURS=6
```

### Full guarded, masih bounded
```env
AUTOPILOT_MODE=full
AUTOPILOT_SCOPE=demo_learning
AUTOPILOT_ALLOW_CONFIG_TUNING=true
AUTOPILOT_ALLOW_MODEL_PROMOTION=true
AUTOPILOT_REQUIRE_APPROVAL_FOR_MAJOR_CHANGES=false
AUTOPILOT_SCHEDULER_ENABLED=true
AUTOPILOT_CADENCE_HOURS=6
```
Gunakan hanya setelah outcome data hidup dan rollback signal sudah dipercaya.
