# Phase 4 Approval Workflow

Phase 4 fokus pada approval workflow yang lebih rapi untuk candidate config dan candidate model.

## Goal
Membuat sistem bisa:
- menyiapkan candidate config
- membandingkan current vs recommended
- merangkum approval state
- menyiapkan backup sebelum apply/promote
- tetap menjaga approval manual sebagai gate utama

## Config Approval Flow
1. Generate recommendation:
```bash
python scripts/generate_config_recommendation.py
```

2. Prepare candidate config:
```bash
python scripts/auto_apply_candidate_config.py
```

3. Compare current vs candidate recommendation:
```bash
python scripts/compare_config_vs_recommendation.py
```

4. Build unified approval summary:
```bash
python scripts/build_approval_summary.py
```

5. Review outputs:
- `data/exports/recommended_config.env`
- `data/exports/candidate_config.env`
- `data/exports/config_comparison.json`
- `data/exports/approval_summary.json`

6. Apply manually only after review:
```bash
python scripts/approve_candidate_config.py
```

## Model Approval Flow
1. Ensure readiness allows training
2. Run learning cycle or train/evaluate directly
3. Review:
- `models/reports/model_evaluation.json`
- `data/exports/approval_summary.json`
- `data/exports/rollback_trigger_check.json`

4. Backup current model before promotion:
```bash
python scripts/backup_current_model.py
```

5. Promote manually only after review:
```bash
python scripts/promote_candidate_model.py
```

6. Roll back if needed:
```bash
python scripts/rollback_model.py
```

## Approval Principles
- No auto-promote by default
- No blind config apply
- If rollback signal is active, review before any apply/promote
- Pair-session policy changes should be treated as material config changes

## Recommended Next UI Step
Expose `approval_summary.json` in `/ops` so the operator can see:
- readiness level
- promotion recommendation
- rollback recommendation
- config differences
- candidate existence state
