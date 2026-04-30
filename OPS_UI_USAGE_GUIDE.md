# Ops UI Usage Guide

Panduan ini menjelaskan cara memakai panel `/ops` pada mt5_ai_bot.

## 1. Readiness
Menunjukkan status umum sistem.

- `ready`: sistem tidak menemukan blocker besar
- `caution`: ada kondisi yang perlu perhatian
- `danger`: ada blocker penting, misalnya kill switch aktif

## 2. Guardrails
Menunjukkan mode dan batasan runtime.

### Active Profile
Bisa dipakai untuk memilih:
- `dry_run`
- `demo`
- `live`

Catatan:
- mengganti profile tidak otomatis menghapus emergency stop atau kill switch
- `live` tetap bisa diblok oleh guardrail lain

## 3. Kill Switch
### Set Kill Switch
- pilih `true` untuk mengunci runtime
- pilih `false` untuk melepas lock
- isi `reason` agar perubahan mudah diaudit

## 4. Approval Summary
Bagian ini dipakai untuk config/model workflow.

### Prepare Candidate Config
Menjalankan rangkaian:
- generate config recommendation
- prepare candidate config
- compare current vs recommendation
- rebuild approval summary

Gunakan ini sebelum review perubahan config.

### Backup Current Model
Membuat backup model aktif sebelum promotion/eksperimen.

### Rebuild Approval Summary
Refresh ringkasan approval tanpa menyiapkan candidate config baru.

### Apply Candidate Config
**Butuh konfirmasi manual.**
Isi field konfirmasi dengan:
```text
apply
```
Baru submit.

Catatan:
- action ini diblok jika rollback signal aktif
- action ini diblok jika candidate config belum ada

## 5. Learning Cycle
Bagian ini menunjukkan pipeline belajar lokal/non-LLM.

### Run Learning Cycle Now
**Butuh konfirmasi manual.**
Isi field konfirmasi dengan:
```text
run
```
Baru submit.

Action ini menjalankan learning cycle on-demand, misalnya:
- build dataset
- readiness check
- adaptive analytics
- rollback trigger check
- train/evaluate candidate jika gate mengizinkan

## 6. Local Engine Settings
Bagian ini mengontrol rule inti untuk `/analyze` hot path.

### Spread/ATR Max Ratio
Nilai ini menentukan seberapa besar spread masih ditoleransi dibanding ATR sebelum local engine memutuskan `WAIT`.

Contoh interpretasi:
- `0.08` = sangat ketat
- `0.12` = lebih realistis untuk GOLD CFD dengan spread agak tebal
- `0.15` = lebih longgar untuk testing broker tertentu

### Update Local Engine Settings
Simpan nilai baru tanpa mengedit `.env` manual.

Catatan:
- nilai lebih tinggi bisa membuat bot lebih sering memberi setup
- nilai terlalu tinggi bisa meloloskan kondisi spread buruk

## 7. LLM Periodic Review
Bagian ini mengontrol slow-path external LLM review.

### Enabled
- `true`: periodic review boleh jalan sesuai cadence
- `false`: periodic review nonaktif

### Cadence options
- `manual_only`
- `1h`
- `3h`
- `6h`
- `12h`
- `24h`

Default:
- `3h`

### Update LLM Review Settings
Simpan perubahan enabled/cadence.

### Run LLM Review Now
Menjalankan periodic review secara paksa (force-run), tanpa menunggu cadence berikutnya.

Gunakan ini kalau:
- baru mengubah setting
- ingin tes provider external sekarang
- ingin refresh review output manual

## 8. Pair-Session Policy
Menampilkan policy pair x session yang aktif.

## 9. Adaptive Pair-Session Insight
Menampilkan hasil analytics pair-session jika report tersedia.

## 10. Trade Summary / Decision Summary
Dipakai untuk memantau hasil runtime dan filter reasons.

## Recommended Safe Workflow
1. buka `/ops`
2. cek `Readiness`
3. cek `Kill Switch` dan `Emergency Stop`
4. untuk config workflow:
   - `Prepare Candidate Config`
   - review `Approval Summary`
   - jika yakin, `Apply Candidate Config` dengan confirm `apply`
5. untuk learning workflow:
   - `Run Learning Cycle Now` dengan confirm `run`
6. untuk local engine tuning:
   - cek log `/analyze`
   - sesuaikan `Spread/ATR Max Ratio` bila bot terlalu sering WAIT karena spread
7. untuk external review:
   - atur cadence di `LLM Periodic Review`
   - gunakan `Run LLM Review Now` bila perlu

## Important Notes
- hot path `/analyze` sekarang local-first
- external LLM review bukan keputusan per candle
- beberapa action sengaja memakai confirm text agar tidak kepencet tanpa sengaja
