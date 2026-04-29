# Local Runtime + Periodic LLM Review Refactor Plan

## Goal
Mengubah bot dari arsitektur `LLM-per-candle` menjadi:
- **local-runtime-first** untuk hot path trading
- **external LLM periodic review** untuk analisa adaptif

## Final Decision
### Runtime hot path
- Tidak memanggil LLM external per candle
- Menggunakan local rules dan optional local model scoring
- Tetap melewati risk filter dan guardrail

### LLM slow path
- Digunakan untuk analisa periodik
- Default cadence: **setiap 3 jam**
- Cadence bisa diubah manual dari UI
- Tidak auto-apply config/model changes
- Output masuk ke report / recommendation / approval summary

---

## Architecture Shift

### Old architecture
`MT5 -> Python -> external LLM -> parse -> risk filter -> trade decision`

### New architecture
`MT5 -> Python -> local decision engine -> risk filter -> trade decision`

And separately:
`recent logs/results -> LLM review job (default 3h) -> recommendation artifacts -> operator review`

---

## Scope

### In scope
- Local decision engine for `/analyze`
- Optional local model scoring in runtime
- Periodic LLM review job with default 3h cadence
- UI visibility and manual cadence control
- Safe persistence of LLM review schedule/config

### Out of scope
- Auto-apply config changes
- Auto-promote models
- Removing LLM tooling entirely
- Live trading autonomy expansion

---

## Runtime Design

### 1. New local decision engine
Create service:
- `app/services/local_decision_engine.py`

Input:
- `MarketRequest`

Output:
- `TradeDecision`

### 2. Local decision logic
Use deterministic checks first:
- trend alignment
- EMA relationship
- RSI condition
- MACD confirmation if available
- ATR / volatility sanity
- support/resistance proximity
- spread sanity
- higher timeframe alignment
- session/news/position context
- RR feasibility

Default posture:
- prefer `WAIT` when setup is weak, conflicting, or incomplete

### 3. Optional local model scoring
If current model exists and is healthy:
- call local model scoring as supporting signal
- never require external LLM for runtime decision

### 4. Risk filter stays
Keep existing risk filter and guardrails after local decision generation.

---

## Periodic LLM Review Design

### Purpose
LLM becomes a slow-path reviewer, not the hot-path decision engine.

### Default cadence
- every **3 hours**

### Manual cadence options
Suggested enum values:
- `manual_only`
- `1h`
- `3h`
- `6h`
- `12h`
- `24h`

Default:
- `3h`

### LLM review inputs
- recent decisions
- recent trade results
- pair/session analytics
- current config snapshot
- approval summary context
- maybe dataset readiness / rollback trigger state

### LLM review outputs
- periodic review report
- config recommendation update
- pair/session recommendation notes
- operator-facing summary

### No direct mutation
LLM review must not directly:
- apply config
- promote model
- change runtime profile

---

## UI / Ops Requirements

### Add LLM review settings block
Expose in `/ops`:
- review mode enabled/disabled
- cadence value
- last review run time
- next scheduled review time
- last review status
- run now action

### Manual controls
Add safe actions:
- update cadence
- set manual-only mode
- trigger review now

### Visibility
Show:
- whether runtime is local-only
- whether external LLM is only used in periodic review
- current review provider status

---

## Persistence

Create durable config/state file, e.g.:
- `data/llm_review_settings.json`

Suggested fields:
```json
{
  "enabled": true,
  "cadence": "3h",
  "last_run_at": null,
  "next_run_at": null,
  "last_status": null
}
```

---

## Scheduler / Execution Model

### Runtime analyze
- direct synchronous local engine
- no external provider dependency

### Periodic review job
New script, e.g.:
- `scripts/run_llm_periodic_review.py`

Responsibilities:
- check cadence eligibility
- gather recent artifacts
- call provider
- store review output
- update settings/status file
- refresh approval/recommendation artifacts if needed

---

## File Changes (planned)

### New files
- `app/services/local_decision_engine.py`
- `app/services/llm_review_settings_service.py`
- `scripts/run_llm_periodic_review.py`
- `data/llm_review_settings.json` (runtime-created)
- `LLM_REVIEW_SCHEDULING.md`

### Likely modified files
- `app/routes/analyze.py`
- `app/routes/ops.py`
- `app/services/ops_summary_service.py`
- `app/templates/ops_dashboard.html`
- `app/services/model_service.py`
- `README.md`
- `WINDOWS_LEARNING_SCHEDULER.md`

---

## Rollout Plan

### Phase 1
- Introduce local decision engine
- Switch `/analyze` hot path away from external LLM
- Keep current risk filter

### Phase 2
- Add periodic LLM review script
- Add settings persistence
- Add basic `/ops` visibility

### Phase 3
- Add cadence control in UI
- Add run-now action
- Integrate outputs into approval summary

### Phase 4
- Tune local rules and optional model score usage
- Reduce dependence on LLM for day-to-day operations

---

## Acceptance Criteria

### Runtime
- `/analyze` no longer depends on external LLM
- bot can operate in demo mode without Codex/Gemini being available
- decision latency is materially lower and more stable

### LLM review
- periodic review defaults to every 3 hours
- cadence can be changed from UI
- review results are visible in `/ops`
- no automatic config/model mutation occurs

### Safety
- risk filter and kill switch remain intact
- emergency stop behavior remains intact
- operator review remains required for material changes

---

## Recommendation
Implement this refactor before adding more LLM hot-path sophistication. The current runtime evidence strongly suggests external LLM should be demoted to the periodic analysis layer rather than kept in the decision hot path.
