# SOP - MT5 AI Bot Operations

## Prinsip utama
- Trade engine boleh jalan otomatis.
- Adaptive tuning boleh jalan semi-otomatis.
- Apply config/model baru harus lewat gate.
- Rollback dan kill switch harus selalu siap.
- Kalau ragu, jangan ubah apa pun.

## Rutinitas harian
1. Cek health API
2. Cek review performa harian
3. Cek log error
4. Siapkan kill switch jika ada anomali

## Kapan run adaptive tuning
- Ideal: 1x per hari untuk review ringan
- Lebih serius: 1x per minggu
- Minimum sample: 10+ trade, lebih bagus 20-50+

## Setelah tuning
Review:
- adaptive_report.json
- config_comparison.json
- candidate_config.env
- performance_checkpoint.json
- rollback_trigger_check.json
- model_evaluation.json
- model_threshold_tuning.json

## Approve config jika
- checkpoint layak
- data cukup
- candidate masuk akal
- tidak ada red flag besar

## Jangan approve jika
- sample kecil
- model candidate belum layak
- market abnormal
- perubahan terlalu agresif

## Train model jika
- trade dataset cukup
- label bersih
- feature konsisten

## Promote model jika
- promotion_recommended=true
- candidate tidak kalah dari current
- sample cukup

## Rollback config jika
- performa memburuk jelas
- false signal naik
- drawdown membesar
- behavior filter aneh

## Rollback model jika
- model baru terlalu sering block setup bagus
- win rate turun setelah model aktif
- score model terasa tidak masuk akal

## Kapan diam
- data belum cukup
- performa masih normal
- belum ada bukti kandidat lebih baik
- market sangat abnormal
- baru habis news besar

## Mode aman
- Dry-run: saat perubahan besar
- Demo: saat validasi perubahan
- Live kecil: hanya jika demo stabil dan guard siap

## Escalation
- Warning: cek log, jangan ubah config
- Caution: tahan approval
- Danger: aktifkan kill switch, rollback bila perlu
