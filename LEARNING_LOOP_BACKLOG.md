# Learning Loop Backlog

## Priority 1
- [ ] Verify production logging and trade-result ingest produce real rows consistently
- [ ] Add scheduled runner for dataset build + readiness check
- [ ] Persist learning cycle run logs/status to file or SQLite
- [ ] Surface dataset readiness in `/ops`

## Priority 2
- [ ] Add scheduled runner for adaptive analytics
- [ ] Add scheduled runner for candidate model train/evaluate
- [ ] Surface latest learning run status in `/ops`
- [ ] Surface candidate model presence + promotion recommendation in `/ops`

## Priority 3
- [ ] Unify apply/promote/rollback state into one summary block
- [ ] Add pair-session recommendation visibility in richer form
- [ ] Add operator approval workflow UX for config/model changes

## Priority 4
- [ ] Explore bounded semi-automatic apply flow
- [ ] Explore rollback package generation
- [ ] Explore confidence history / evaluation history visualization
