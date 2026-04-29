from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
BACKUP_DIR = ROOT / "models" / "reports" / "model_backups"
CURRENT_MODEL = ROOT / "models" / "current" / "model.pkl"
CURRENT_META = ROOT / "models" / "current" / "model_meta.json"


def main() -> None:
    if not BACKUP_DIR.exists():
        print(f"No backup directory: {BACKUP_DIR}")
        return

    model_backups = sorted(BACKUP_DIR.glob("model_*.pkl.bak"))
    if not model_backups:
        print("No model backups found")
        return

    latest_model = model_backups[-1]
    CURRENT_MODEL.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(latest_model, CURRENT_MODEL)
    print(f"Rolled back {CURRENT_MODEL} from {latest_model}")

    meta_backups = sorted(BACKUP_DIR.glob("model_meta_*.json.bak"))
    if meta_backups:
        latest_meta = meta_backups[-1]
        shutil.copyfile(latest_meta, CURRENT_META)
        print(f"Rolled back {CURRENT_META} from {latest_meta}")


if __name__ == "__main__":
    main()
