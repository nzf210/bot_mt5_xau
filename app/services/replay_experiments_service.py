from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEARNING_DIR = ROOT / "data" / "learning"
EXPERIMENTS_JSONL = LEARNING_DIR / "replay_experiments.jsonl"
BASELINE_PATH = LEARNING_DIR / "replay_baseline.json"


def append_replay_experiment(summary: dict) -> None:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    with EXPERIMENTS_JSONL.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, ensure_ascii=False) + "\n")


def load_recent_replay_experiments(limit: int = 5) -> list[dict]:
    if not EXPERIMENTS_JSONL.exists():
        return []
    rows: list[dict] = []
    with EXPERIMENTS_JSONL.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows[-limit:][::-1]


def save_replay_baseline(summary: dict) -> None:
    LEARNING_DIR.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_replay_baseline() -> dict:
    if not BASELINE_PATH.exists():
        return {"available": False}
    try:
        payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"available": False}
    payload["available"] = True
    return payload
