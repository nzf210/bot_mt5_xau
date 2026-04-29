# MT5 AI Bot Autonomy Roadmap

Roadmap ini fokus pada peningkatan otonomi bot secara aman dan bertahap, terutama di area learning loop. Tujuannya bukan membuat bot self-modifying tanpa kendali, tapi membangun sistem yang bisa:
- mengumpulkan data sendiri
- mengevaluasi kesiapan data sendiri
- melatih candidate sendiri
- menilai candidate sendiri
- memberi sinyal apply/promote/rollback dengan gate yang jelas

## Current State Summary

### Sudah ada
- Market analyze pipeline dari MT5 ke Python ke AI ke filter ke execution
- Logging keputusan AI dan hasil trade
- Ops panel `/ops` dan `/ops/summary`
- Kill switch, profile modes, readiness summary
- CLI-first provider registry
- Dataset builders
- Candidate model training/evaluation scaffolding
- Dataset threshold gate
- `decision_id` linkage untuk join keputusan dan hasil trade
- Pair-session static guardrail
- Pair-session analytics foundation

### Belum ada
- Scheduler/orchestrator learning loop yang stabil
- Dataset collection policy yang enforced otomatis
- Auto-run analytics/training/evaluation secara periodik
- Learning cycle state tracking yang terlihat di ops panel
- Promotion/apply loop yang lebih otomatis namun tetap bounded
- Rollback trigger terhubung ke loop orchestration

## Guiding Principles
- Safety > autonomy
- No auto-promotion without strong gate
- No config/model mutation when dataset readiness is insufficient
- Human review remains required for material changes until the system has long enough evidence
- Rollback path must exist before any higher autonomy layer is enabled

## Phase 0 - Data Reality First
Goal: pastikan bot benar-benar mengumpulkan data yang layak dipakai.

### Deliverables
- Stable decision logging in production path
- Stable trade result ingest in production path
- Verify `decision_id` survives MT5 -> backend -> closed trade report
- Confirm datasets are non-empty and growing
- Add basic daily sanity check for row growth

### Success criteria
- Decision dataset grows continuously
- Trade dataset receives closed trades
- No major mismatch between trade rows and originating decision rows

## Phase 1 - Autonomous Data Readiness
Goal: bot bisa menilai sendiri apakah datanya layak untuk analytics/training/promotion.

### Deliverables
- `check_dataset_readiness.py` integrated into routine operations
- Readiness status surfaced in ops panel
- Clear states:
  - `insufficient_data`
  - `analytics_ready`
  - `training_ready`
  - `promotion_ready`
- Daily/weekly recommended operator actions based on state

### Success criteria
- Operator can see learning readiness instantly
- No analytics/training run is trusted when readiness is below threshold

## Phase 2 - Scheduled Learning Pipeline
Goal: analytics/training/evaluation can run automatically on a schedule.

### Deliverables
- Scheduled job runner on target machine (Windows Task Scheduler or equivalent)
- Batch script / PowerShell runner for:
  - build decision dataset
  - build trade dataset
  - check dataset readiness
  - run adaptive analytics
  - train candidate model when allowed
  - evaluate candidate model when allowed
- Persistent run logs for each learning cycle

### Success criteria
- The learning pipeline can run unattended
- Failures are visible in logs and ops panel
- Runs do not mutate active config/model by default

## Phase 3 - Learning Cycle Visibility
Goal: ops panel shows learning status, not just trading status.

### Deliverables
- New ops summary block for learning cycle
- Show latest run time, latest status, readiness level, and latest outputs
- Show whether candidate model exists
- Show whether promotion is recommended
- Show whether rollback trigger is active

### Success criteria
- Operator can inspect learning lifecycle from `/ops`
- No need to manually inspect files for common status questions

## Phase 4 - Bounded Candidate Promotion Workflow
Goal: candidate config/model can move closer to autonomy, but still bounded.

### Deliverables
- Unified approval gate summary
- Candidate config/model prepared automatically
- Promotion eligibility checked automatically
- Optional one-click operator approval from panel later
- Config/model remain unchanged until gate passes and approval is granted

### Success criteria
- Recommendation generation becomes routine
- Promotion remains explainable and reviewable
- No accidental self-mutation

## Phase 5 - Automatic Rollback Signals
Goal: if performance deteriorates, bot can strongly signal or prepare rollback automatically.

### Deliverables
- Rollback trigger integrated into scheduled learning loop
- Warning states surfaced in ops panel
- Candidate/current comparison retained historically
- Optional rollback package prepared automatically, but not blindly applied at first

### Success criteria
- System detects degradation earlier
- Rollback path is operational before more autonomy is granted

## Phase 6 - Pair-Session Adaptive Policy
Goal: pair-session insights move from analytics into bounded recommendations.

### Deliverables
- Stable `recommended_symbol_session_policy`
- Threshold recommendations per pair-session when sample is sufficient
- Visibility in ops panel
- Review-first application path to `SYMBOL_SESSION_POLICY_JSON`

### Success criteria
- Pair-session policy evolves from evidence, not guesswork
- Narrow data does not create overconfident recommendations

## Phase 7 - Higher Autonomy Mode (Optional, Late)
Goal: only after enough history and stable behavior, consider semi-automatic apply flows.

### Deliverables
- Strict prerequisites:
  - sustained dataset growth
  - multiple evaluation cycles
  - rollback path verified
  - promotion history tracked
- Semi-automatic config apply under conservative scope
- Semi-automatic model promotion only with very strong evidence

### Success criteria
- Higher autonomy is earned, not assumed
- Behavior remains bounded and reversible

## Recommended Implementation Order
1. Phase 0
2. Phase 1
3. Phase 2
4. Phase 3
5. Phase 4
6. Phase 5
7. Phase 6
8. Phase 7 only if prior phases prove stable

## Honest Assessment
Right now the bot is strongest in:
- execution automation
- operational visibility
- guardrail structure

It is weakest in:
- real dataset accumulation
- scheduled learning orchestration
- integrated autonomous learning lifecycle

## Recommendation Right Now
The most valuable next build is:
1. scheduled learning runner
2. learning-cycle visibility in ops panel
3. bounded promotion workflow

That path gives the bot more real autonomy without pretending it is ready for unsafe self-modification.
