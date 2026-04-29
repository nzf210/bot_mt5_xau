# Pair x Session Guardrail Design

## Goal
Menambahkan guardrail yang bisa membedakan policy antar pair dan antar session market, sehingga bot tidak hanya session-aware secara global, tapi juga bisa memakai aturan yang lebih cocok untuk karakter pair tertentu.

## Design Summary
Guardrail baru dibangun sebagai layer di atas profile global yang sudah ada.

Urutan evaluasi target:
1. baseline global profile dari mode (`dry_run/demo/live`)
2. symbol normalization
3. apply symbol-level allowed session policy
4. apply symbol+session threshold override jika ada
5. jalankan risk filter dengan threshold hasil merge

## Config shape
Tambahkan setting JSON string baru, misalnya:
- `SYMBOL_SESSION_POLICY_JSON={...}`

Contoh bentuk awal:
```json
{
  "XAUUSD": {
    "allowed_sessions": ["London", "Overlap", "NewYork"],
    "sessions": {
      "Asia": {
        "min_confidence": 80,
        "min_risk_reward": 2.0,
        "max_spread_points": 25,
        "cooldown_minutes": 45
      },
      "London": {
        "min_confidence": 72,
        "min_risk_reward": 1.7,
        "max_spread_points": 30
      }
    }
  },
  "USDJPY": {
    "allowed_sessions": ["Asia", "London"],
    "sessions": {
      "Asia": {
        "min_confidence": 70,
        "max_spread_points": 20
      }
    }
  }
}
```

## New service responsibilities
### 1. policy parser / resolver
Buat service baru, misalnya `pair_session_policy_service.py`, untuk:
- parse JSON config dengan aman
- normalize symbol
- resolve effective policy untuk `symbol + session`
- merge override ke profile global

### 2. risk filter integration
`risk_filter.py` akan berhenti memakai `settings.allowed_sessions` langsung sebagai satu-satunya rule global. Sebagai gantinya:
- resolve effective policy dulu
- gunakan `effective_allowed_sessions`
- gunakan threshold hasil merge:
  - `min_confidence`
  - `min_risk_reward`
  - `max_spread_points`
  - `cooldown_minutes`
  - lainnya bila diaktifkan

## Effective policy behavior
Untuk request tertentu:
- normalize symbol, contoh `XAUUSD.a -> XAUUSD`
- cari rule symbol
- jika ada `allowed_sessions`, itu override allowlist global
- jika ada `sessions[market.session]`, merge ke profile
- jika tidak ada rule, fallback penuh ke global profile

## Suggested API/UI exposure
Ops summary bisa menampilkan:
- apakah pair-session policy aktif
- rule yang match untuk symbol terakhir
- fallback/global path jika tidak ada exact rule

Control panel fase lanjut bisa menampilkan:
- raw JSON policy
- resolved policy untuk symbol tertentu

## Verification strategy
### Unit-ish behavior checks
- symbol tanpa policy -> fallback global
- symbol dengan policy -> allowlist pair dipakai
- symbol+session override -> threshold override dipakai
- symbol dengan session tak diizinkan -> `session_not_allowed`

### Operational checks
- `/ops/summary` tetap hidup
- panel tetap hidup
- filter reason tetap jelas
- tidak ada pair policy -> behavior lama tetap aman

## Rollout recommendation
### Iteration 1
- parser + resolver
- allowed session per symbol
- threshold override dasar per symbol+session
- no auto-generated config yet

### Iteration 2
- analytics pair-session report
- recommendation generator untuk pair-session combos

### Iteration 3
- UI editor atau viewer yang lebih nyaman
- approval gate untuk adaptive pair-session config

## Why this design
Desain ini menyelesaikan masalah utama tanpa langsung membuat sistem terlalu kompleks:
- XAUUSD tidak perlu diperlakukan sama dengan USDJPY
- Asia session tidak perlu memakai threshold sama dengan Overlap
- global profile tetap ada sebagai safety baseline
- adaptive path masih bisa ditambahkan nanti di atas fondasi yang stabil
