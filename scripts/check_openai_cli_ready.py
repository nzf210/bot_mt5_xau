from shutil import which
import subprocess
import json


def main() -> None:
    codex_path = which("codex")
    payload = {
        "which_codex": codex_path,
        "available": bool(codex_path),
        "version_ok": False,
        "version_output": None,
    }

    if codex_path:
        try:
            proc = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=15)
            payload["version_output"] = (proc.stdout or proc.stderr).strip()
            payload["version_ok"] = proc.returncode == 0
        except Exception as exc:
            payload["version_output"] = str(exc)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
