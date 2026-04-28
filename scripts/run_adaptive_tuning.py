import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = [
    "scripts/build_decision_dataset.py",
    "scripts/build_trade_dataset.py",
    "scripts/run_adaptive_analytics.py",
    "scripts/generate_config_recommendation.py",
    "scripts/compare_config_vs_recommendation.py",
    "scripts/auto_apply_candidate_config.py",
    "scripts/check_performance_checkpoint.py",
    "scripts/check_rollback_trigger.py",
    "scripts/log_tuning_history.py",
    "scripts/evaluate_setup_model.py",
    "scripts/tune_model_threshold.py",
    "scripts/log_model_evaluation_history.py",
    "scripts/summarize_model_history.py",
]


def main() -> None:
    for script in SCRIPTS:
        print(f"Running {script}...")
        subprocess.run(["python3", str(ROOT / script)], check=True)
    print("Adaptive tuning pipeline complete.")


if __name__ == "__main__":
    main()
