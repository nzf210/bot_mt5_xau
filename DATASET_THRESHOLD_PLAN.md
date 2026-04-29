# Dataset Threshold Plan - MT5 AI Bot

Tujuan dokumen ini adalah menetapkan ambang minimum sebelum bot boleh:
- dianalisis secara statistik dengan percaya diri lebih tinggi
- melatih candidate model
- mempromosikan model/config hasil adaptive tuning

## Prinsip
- Data sedikit boleh dikumpulkan, tapi tidak boleh dianggap cukup untuk training serius
- Analytics readiness, training readiness, dan promotion readiness adalah level berbeda
- Jika threshold tidak lolos, default action adalah **jangan ubah config/model**

## Level 1 - Insufficient Data
Kondisi ini berarti bot baru mengumpulkan jejak, belum layak dipakai untuk learning serius.

Trigger umum:
- decision rows < 30
- closed trades < 10
- hanya satu kelas hasil (`win` saja atau `loss` saja)

Action:
- lanjut kumpulkan data
- boleh review manual, tapi jangan ubah model/config karena data

## Level 2 - Analytics Ready
Level ini cukup untuk statistik dasar dan adaptive report awal.

Minimum:
- decision rows >= 30
- closed trades >= 10
- ada minimal 1 `win` dan 1 `loss`
- minimal 1 symbol aktif
- minimal 1 timeframe aktif
- minimal 1 session aktif

Action:
- boleh jalankan `run_adaptive_analytics.py`
- boleh baca rekomendasi confidence/RR/session/symbol
- belum otomatis layak train/promote

## Level 3 - Training Ready
Level ini cukup untuk mulai melatih candidate model baseline.

Minimum:
- closed trades >= 30
- decision rows >= 60
- win count >= 10
- loss count >= 10
- minimal 2 session aktif
- minimal 2 timeframe aktif
- minimal 2 symbol aktif atau 1 symbol dengan sample besar yang disengaja

Action:
- boleh jalankan training candidate model
- boleh evaluasi candidate vs current
- hasil evaluasi tetap belum otomatis boleh dipromote

## Level 4 - Promotion Ready
Level ini cukup untuk mempertimbangkan apply config/model hasil learning.

Minimum:
- closed trades >= 50
- decision rows >= 100
- win count >= 15
- loss count >= 15
- minimal 2 session aktif
- minimal 2 timeframe aktif
- candidate evaluation tersedia
- candidate lebih baik dari current atau belum ada current model
- tidak seluruh performa hanya ditopang satu cluster data yang terlalu sempit

Action:
- boleh pertimbangkan approve candidate config
- boleh pertimbangkan promote candidate model
- tetap review manual sebelum apply

## Caution flags
Walau threshold lolos, tetap tahan promotion jika:
- semua data hanya dari 1 session
- semua data hanya dari 1 timeframe kecil
- market regime tampak abnormal
- sample baru saja terkumpul dari periode news/volatilitas ekstrem
- candidate unggul tipis sekali dan belum stabil

## Default recommendation
- <10 trades: kumpulkan data saja
- 10-29 trades: analytics awal boleh, training jangan
- 30-49 trades: training candidate boleh
- 50+ trades: promotion boleh dipertimbangkan jika evaluasi mendukung
