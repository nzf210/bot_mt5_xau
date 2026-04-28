from pathlib import Path
import shutil
import json

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_MODEL = ROOT / "models" / "candidates" / "candidate_model.pkl"
CANDIDATE_META = ROOT / "models" / "candidates" / "candidate_model_meta.json"
CURRENT_MODEL = ROOT / "models" / "current" / "model.pkl"
CURRENT_META = ROOT / "models" / "current" / "model_meta.json"
EVAL_REPORT = ROOT / "models" / "reports" / "model_evaluation.json"


def main() -> None:
    if not CANDIDATE_MODEL.exists() or not CANDIDATE_META.exists() or not EVAL_REPORT.exists():
        print("Missing candidate model/meta or evaluation report")
        return

    evaluation = json.loads(EVAL_REPORT.read_text(encoding="utf-8"))
    if not evaluation.get("promotion_recommended"):
        print("Promotion not recommended, aborting")
        return

    CURRENT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(CANDIDATE_MODEL, CURRENT_MODEL)
    shutil.copyfile(CANDIDATE_META, CURRENT_META)
    print(f"Promoted candidate model to {CURRENT_MODEL}")


if __name__ == "__main__":
    main()
