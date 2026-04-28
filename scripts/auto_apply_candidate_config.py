from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
RECOMMENDED_ENV = ROOT / "data" / "exports" / "recommended_config.env"
CANDIDATE_ENV = ROOT / "data" / "exports" / "candidate_config.env"


def main() -> None:
    if not RECOMMENDED_ENV.exists():
        print(f"Missing recommended config: {RECOMMENDED_ENV}")
        return
    shutil.copyfile(RECOMMENDED_ENV, CANDIDATE_ENV)
    print(f"Wrote candidate config to {CANDIDATE_ENV}")


if __name__ == "__main__":
    main()
