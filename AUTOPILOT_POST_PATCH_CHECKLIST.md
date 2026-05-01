# Autopilot Post-Patch Checklist

## Tujuan
Memverifikasi bahwa patch autopilot aktif dengan benar di runtime RDP dan tidak hanya berhenti di level code.

## 1. Restart backend
- [ ] Restart service / process backend Python
- [ ] Pastikan backend kembali healthy
- [ ] Buka `/health`

## 2. Verifikasi env autopilot
- [ ] `AUTOPILOT_MODE` sesuai target (`off`, `semi`, atau `full`)
- [ ] `AUTOPILOT_SCOPE` sesuai target
- [ ] `AUTOPILOT_ALLOW_CONFIG_TUNING` sesuai target
- [ ] `AUTOPILOT_ALLOW_MODEL_PROMOTION` sesuai target
- [ ] `AUTOPILOT_REQUIRE_APPROVAL_FOR_MAJOR_CHANGES` sesuai target
- [ ] `AUTOPILOT_SCHEDULER_ENABLED` sesuai target
- [ ] `AUTOPILOT_CADENCE_HOURS` sesuai target

## 3. Verifikasi panel `/ops`
- [ ] Blok **Autopilot** muncul
- [ ] Mode tampil benar
- [ ] Scope tampil benar
- [ ] Effective behavior tampil benar
- [ ] Preset guardrails tampil
- [ ] Trade Summary memiliki bagian **Close Reasons**

## 4. Apply preset autopilot
- [ ] Jalankan action **Apply Autopilot Preset to Local Engine**
- [ ] Tidak ada error
- [ ] Nilai Local Engine berubah/selaras dengan preset mode aktif

## 5. Verifikasi learning cycle
- [ ] Jalankan **Run Learning Cycle Now**
- [ ] `learning_cycle_status.json` update timestamp-nya
- [ ] Cycle menyimpan blok `autopilot`
- [ ] Reason skip train/evaluate sesuai mode/readiness
- [ ] Approval summary terbangun ulang tanpa error

## 6. Verifikasi approval behavior
- [ ] Coba prepare candidate config saat `AUTOPILOT_MODE=off` dan pastikan diblok
- [ ] Coba prepare candidate config saat `AUTOPILOT_MODE=semi/full` dan pastikan sesuai policy
- [ ] Coba apply config dan pastikan policy autopilot benar-benar dihormati

## 7. Verifikasi trade-result enrichment
- [ ] Backend sudah pakai versi terbaru
- [ ] EA sudah pakai versi terbaru jika patch MT5 ingin aktif
- [ ] Setelah ada trade close, cek `close_reason`, `tp_hit`, `sl_hit` mulai masuk
- [ ] Cek Trade Summary / review untuk distribusi `by_close_reason`

## 8. Verifikasi demo safety
- [ ] `ALLOW_LIVE_TRADING=false` bila masih fase demo
- [ ] EA tetap `DemoMode=true`, `LiveMode=false`
- [ ] `EMERGENCY_STOP` sesuai tujuan pengujian
- [ ] Tidak ada live enable yang aktif tanpa sengaja

## 9. Scheduler host
- [ ] Task Scheduler Windows benar-benar aktif jika ingin cadence otomatis
- [ ] Cadence sesuai target (mis. 6 jam)
- [ ] Learning run benar-benar bertambah seiring waktu

## 10. Final sanity check
- [ ] `/ops` tidak error
- [ ] `/ops/summary` tidak error
- [ ] Decision logging masih jalan
- [ ] Trade dataset / readiness tidak regress
- [ ] Tidak ada perilaku yang bertentangan dengan mode autopilot aktif
