from shutil import which
import subprocess
import json


def resolve_codex_path() -> str | None:
    for candidate in ["codex", "codex.cmd", "codex.exe"]:
        path = which(candidate)
        if path:
            return path
    return None


def main() -> None:
    codex_path = resolve_codex_path()
    payload = {
        "which_codex": codex_path,
        "available": bool(codex_path),
        "version_ok": False,
        "version_output": None,
    }

    if codex_path:
        try:
            proc = subprocess.run([codex_path, "--version"], capture_output=True, text=True, timeout=15)
            payload["version_output"] = (proc.stdout or proc.stderr).strip()
            payload["version_ok"] = proc.returncode == 0
        except Exception as exc:
            payload["version_output"] = str(exc)

    print(json.dumps(payload, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
