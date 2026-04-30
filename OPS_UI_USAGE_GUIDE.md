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

### RSI Bullish Threshold
Threshold RSI minimum untuk menganggap momentum bullish cukup kuat.

Contoh:
- `55` = lebih ketat
- `52` = lebih longgar untuk replay diagnosis

### RSI Bearish Threshold
Threshold RSI maksimum untuk menganggap momentum bearish cukup kuat.

Contoh:
- `45` = lebih ketat
- `48` = lebih longgar untuk replay diagnosis

### Min RR Threshold
Minimum reward/risk agar setup tidak langsung ditolak.

Contoh:
- `1.2` = lebih ketat
- `1.0` = lebih longgar untuk diagnosis replay awal

### Trend Strictness
Menentukan seberapa keras syarat alignment trend.

Mode:
- `strict`: close harus benar-benar di atas/bawah EMA alignment penuh
- `moderate`: lebih longgar, cukup dekat dengan EMA20 sambil tetap searah HTF
- `loose`: paling longgar, cukup arah EMA + HTF

### Update Local Engine Settings
Simpan nilai baru tanpa mengedit `.env` manual.

Catatan:
- nilai lebih tinggi bisa membuat bot lebih sering memberi setup
- nilai terlalu tinggi bisa meloloskan kondisi spread buruk
- replay lama tidak perlu dihapus, biarkan sebagai pembanding historis setelah tuning baru dijalankan
- RR dan S/R construction sekarang juga bisa berubah lewat patch engine, jadi bandingkan hasil replay sebelum dan sesudah perubahan logika, bukan hanya angka threshold

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

## 8. Historical Replay Lab
Bagian ini dipakai untuk diagnosis historis berbasis CSV.

### Field utama
- `CSV Path`: lokasi file historical export
- `Symbol`: label simbol untuk replay
- `Timeframe`: timeframe dasar replay
- `Higher Timeframe`: context HTF untuk replay
- `Mode`: biasanya `dry_run`
- `Lookback Bars`: jumlah candle yang dipakai untuk snapshot lokal
- `Outcome Horizon Bars`: jumlah candle ke depan untuk evaluasi outcome
- `Output Prefix`: nama prefix file hasil export replay
- `Point Size`: konversi spread MT5 dari points menjadi price distance replay, misalnya `0.01` untuk banyak broker GOLD

### Save Replay Lab Settings
Menyimpan setting replay historis saat ini.

### Run Historical Replay
Menjalankan replay historis menggunakan setting saat ini, lalu menyimpan summary hasil terakhir ke dashboard `/ops`.

Gunakan ini untuk:
- audit kenapa engine sering `WAIT`
- melihat raw buy/sell/wait vs filtered buy/sell/wait
- mengecek `top raw reasons` yang sekarang lebih granular
- mengecek `top raw warnings`
- mengecek top filter reasons sebelum masuk tahap training

## 9. Pair-Session Policy
Menampilkan policy pair x session yang aktif.

## 10. Adaptive Pair-Session Insight
Menampilkan hasil analytics pair-session jika report tersedia.

## 11. Trade Summary / Decision Summary
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
7. untuk replay historis:
   - isi field di `Historical Replay Lab`
   - simpan setting
   - jalankan `Run Historical Replay`
   - audit raw buy/sell/wait dan top filter reasons
8. untuk external review:
   - atur cadence di `LLM Periodic Review`
   - gunakan `Run LLM Review Now` bila perlu

## Important Notes
- hot path `/analyze` sekarang local-first
- external LLM review bukan keputusan per candle
- beberapa action sengaja memakai confirm text agar tidak kepencet tanpa sengaja
