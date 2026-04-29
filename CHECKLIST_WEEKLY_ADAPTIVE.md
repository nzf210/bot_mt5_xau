# Weekly Adaptive Tuning Checklist

- [ ] Run `python scripts/check_dataset_readiness.py`
- [ ] Confirm dataset level is at least `analytics_ready` before trusting adaptive insights
- [ ] Confirm dataset level is at least `training_ready` before training candidate model
- [ ] Confirm dataset level is at least `promotion_ready` before promoting model/config
- [ ] Minimum trade sample is sufficient
- [ ] Run `python scripts/run_adaptive_tuning.py`
- [ ] Review `adaptive_report.json`
- [ ] Review `config_comparison.json`
- [ ] Review `candidate_config.env`
- [ ] Review `performance_checkpoint.json`
- [ ] Review `rollback_trigger_check.json`
- [ ] Review `model_evaluation.json`
- [ ] Review `model_threshold_tuning.json`
- [ ] Review model history summary
- [ ] Candidate config only approved if clearly justified
- [ ] Candidate model only promoted if clearly justified
- [ ] Backup/rollback path verified before any approval
- [ ] If unclear, do nothing and keep current config/model
