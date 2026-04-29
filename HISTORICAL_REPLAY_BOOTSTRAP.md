# Historical Replay Bootstrap

Dokumen ini menjelaskan cara mengisi dataset bootstrap dari historical bars tanpa menunggu data live berjalan lama.

## Tujuan
Membuat dataset replay yang:
- membaca bars historis dari CSV
- membangun market snapshot ala runtime bot
- menjalankan local decision engine
- menerapkan risk filter
- menghitung forward outcome beberapa bar ke depan
- menulis dataset bootstrap untuk analytics/training awal

## Script
```bash
python scripts/build_historical_replay_dataset.py --csv <path_csv>
```

## CSV minimal
Butuh kolom:
- `time`
- `open`
- `high`
- `low`
- `close`

Opsional:
- `spread`
- `tick_volume`

Contoh header:
```csv
time,open,high,low,close,spread
2025-01-01T00:00:00Z,2620.1,2621.5,2619.8,2621.2,0.3
```

## Contoh run
```bash
python scripts/build_historical_replay_dataset.py \
  --csv data/imports/xauusd_m5.csv \
  --symbol XAUUSD \
  --timeframe M5 \
  --higher-timeframe H1 \
  --mode dry_run \
  --lookback-bars 10 \
  --outcome-horizon-bars 12 \
  --output-prefix xauusd_m5_replay
```

## Output
Script menulis:
- `data/exports/<prefix>_dataset.csv`
- `data/exports/<prefix>_summary.json`

## Isi dataset
Beberapa field penting:
- `decision`
- `confidence`
- `entry`
- `stop_loss`
- `take_profit`
- `risk_reward`
- `passed_filter`
- `filter_reason`
- `session`
- `ema20`
- `ema50`
- `rsi14`
- `macd_main`
- `macd_signal`
- `atr14`
- `outcome_label`
- `outcome_pnl`
- `bars_held`
- `mfe`
- `mae`

## Catatan penting
- Ini bootstrap dataset, bukan pengganti penuh live outcomes.
- Spread akan memakai kolom CSV jika ada. Kalau tidak ada, script memakai pendekatan fallback sederhana.
- Higher timeframe replay sekarang dibangun dari resample seri terpisah lalu di-merge kembali sebagai context mundur, jadi lebih realistis daripada proxy satu seri.
- Ini masih belum identik dengan feed HTF broker-native multi-stream, jadi tetap perlakukan sebagai bootstrap yang kuat, bukan ground truth final.
- Gunakan ini untuk mempercepat analytics, gating, dan eksperimen model awal, lalu tetap kalibrasikan dengan data live asli.
