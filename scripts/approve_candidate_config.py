from pathlib import Path
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
CANDIDATE_ENV = ROOT / "data" / "exports" / "candidate_config.env"
BACKUP_DIR = ROOT / "data" / "exports" / "env_backups"


def merge_env(current: Path, candidate: Path) -> str:
    current_map = {}
    if current.exists():
        for line in current.read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.strip().startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            current_map[k.strip()] = v.strip()

    for line in candidate.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if v.strip() != "":
            current_map[k.strip()] = v.strip()

    return "\n".join(f"{k}={v}" for k, v in current_map.items()) + "\n"


def main() -> None:
    if not CANDIDATE_ENV.exists():
        print(f"Missing candidate config: {CANDIDATE_ENV}")
        return
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if ENV_FILE.exists():
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        shutil.copyfile(ENV_FILE, BACKUP_DIR / f".env.{ts}.bak")
    merged = merge_env(ENV_FILE, CANDIDATE_ENV)
    ENV_FILE.write_text(merged, encoding="utf-8")
    print(f"Applied candidate config to {ENV_FILE}")


if __name__ == "__main__":
    main()
