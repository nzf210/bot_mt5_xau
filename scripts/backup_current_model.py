from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CURRENT_MODEL = ROOT / "models" / "current" / "model.pkl"
CURRENT_META = ROOT / "models" / "current" / "model_meta.json"
BACKUP_DIR = ROOT / "models" / "reports" / "model_backups"


def main() -> None:
    if not CURRENT_MODEL.exists():
        print(f"Current model not found: {CURRENT_MODEL}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    model_backup = BACKUP_DIR / f"model_{ts}.pkl.bak"
    shutil.copyfile(CURRENT_MODEL, model_backup)
    print(f"Backed up current model to {model_backup}")
    if CURRENT_META.exists():
        meta_backup = BACKUP_DIR / f"model_meta_{ts}.json.bak"
        shutil.copyfile(CURRENT_META, meta_backup)
        print(f"Backed up current model meta to {meta_backup}")


if __name__ == "__main__":
    main()
