from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CURRENT_MODEL = ROOT / "models" / "current" / "model.json"
BACKUP_DIR = ROOT / "models" / "reports" / "model_backups"


def main() -> None:
    if not CURRENT_MODEL.exists():
        print(f"Current model not found: {CURRENT_MODEL}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"model_{ts}.json.bak"
    shutil.copyfile(CURRENT_MODEL, backup_path)
    print(f"Backed up current model to {backup_path}")


if __name__ == "__main__":
    main()
