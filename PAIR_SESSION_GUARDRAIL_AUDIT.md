# Pair x Session Guardrail Audit

## Ringkasan
Codebase `mt5_ai_bot` cukup siap untuk ditingkatkan ke policy `pair x session`, karena beberapa fondasi kunci sudah ada:
- request market sudah membawa `symbol` dan `session`
- symbol normalization utility sudah ada
- session filtering sudah ada, walau masih global
- analytics sudah bisa membaca performa per session
- dataset/training sudah menyimpan `session`

Jadi upgrade ini **feasible** tanpa perlu ganti arsitektur total.

## Temuan audit

### 1. Session awareness sudah ada, tapi global
Di `risk_filter.py`, bot hanya mengenal:
- `settings.allowed_sessions`
- filter global `session_not_allowed`

Artinya semua pair diperlakukan sama terhadap session allowlist. Ini terlalu kasar untuk market yang sangat berbeda antar pair.

### 2. Profile system cocok untuk diwarisi, tapi belum bertingkat
`profile_service.py` saat ini menghasilkan threshold global per mode:
- `min_confidence`
- `min_risk_reward`
- `max_spread_points`
- `cooldown_minutes`
- `max_open_positions_per_symbol`

Ini bagus sebagai baseline, tapi belum ada override per symbol atau per session.

### 3. Symbol normalization sudah tersedia
`symbol_service.py` sudah punya `normalize_symbol()`.
Ini sangat membantu untuk menghindari mismatch seperti suffix broker (`XAUUSD.a`, dll) saat menerapkan policy pair-specific.

### 4. Adaptive config masih global
Script recommendation saat ini baru menghasilkan nilai seperti:
- `recommended_min_confidence`
- `recommended_min_risk_reward`
- `recommended_allowed_sessions`
- `recommended_disabled_symbols`

Belum ada rekomendasi matriks `symbol x session`.

### 5. Dataset sudah menyimpan session
Decision/trade dataset sudah membawa `session`, jadi secara teori analisa `pair x session` bisa dibangun dari data yang sama. Tidak perlu ubah filosofi pipeline, hanya perlu enrich analisa.

## Kesimpulan audit
Upgrade pair-session-aware guardrail paling cocok dilakukan bertahap:
1. tambah policy statis `symbol -> allowed_sessions`
2. tambah override threshold opsional `symbol + session`
3. baru belakangan tambahkan adaptive recommendation `pair x session`

Kalau langsung lompat ke adaptive pair-session policy penuh, scope akan membesar dan sulit diverifikasi.

## Rekomendasi implementasi
### Tahap 1 - Static pair-session allowlist
Tambahkan config seperti:
- `SYMBOL_SESSION_POLICY_JSON`

Contoh:
```json
{
  "XAUUSD": {
    "allowed_sessions": ["London", "Overlap", "NewYork"]
  },
  "USDJPY": {
    "allowed_sessions": ["Asia", "London"]
  }
}
```

Behavior:
- normalisasi symbol dulu
- kalau pair punya policy sendiri, pakai itu
- kalau tidak, fallback ke `DEFAULT_SESSION_ALLOWLIST`

### Tahap 2 - Pair-session threshold override
Tambah override opsional seperti:
```json
{
  "XAUUSD": {
    "sessions": {
      "Asia": {
        "min_confidence": 80,
        "min_risk_reward": 2.0,
        "max_spread_points": 25
      },
      "London": {
        "min_confidence": 72,
        "min_risk_reward": 1.7,
        "max_spread_points": 30
      }
    }
  }
}
```

Behavior:
- mulai dari profile global
- override jika ada rule exact match `symbol + session`
- fallback jika tidak ada

### Tahap 3 - Analytics support
Tambahkan analisa baru:
- pnl per `symbol + session`
- win rate per `symbol + session`
- top weak combinations
- recommended allowed sessions per symbol

### Tahap 4 - UI visibility
Panel `/ops` nantinya bisa menampilkan:
- pair-session policy aktif
- fallback/default path
- kombinasi pair-session terbaik/terburuk dari analytics

## Risiko
- JSON config policy bisa cepat jadi berantakan jika tidak divalidasi
- terlalu banyak override bisa membuat behavior bot sulit dipahami
- sample kecil per pair-session bisa menghasilkan rekomendasi palsu

## Rekomendasi akhir
Mulai dari **Tahap 1 + Tahap 2 ringan** dulu. Itu memberi value terbesar dengan resiko paling kecil, dan masih mudah diverifikasi di codebase sekarang.
