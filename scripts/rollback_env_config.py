from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
BACKUP_DIR = ROOT / "data" / "exports" / "env_backups"


def main() -> None:
    if not BACKUP_DIR.exists():
        print(f"No backup directory: {BACKUP_DIR}")
        return
    backups = sorted(BACKUP_DIR.glob(".env.*.bak"))
    if not backups:
        print("No backups found")
        return
    latest = backups[-1]
    shutil.copyfile(latest, ENV_FILE)
    print(f"Rolled back {ENV_FILE} from {latest}")


if __name__ == "__main__":
    main()
