from pathlib import Path
from app.utils.time_utils import utc_now_iso


KILL_SWITCH_PATH = Path("data/kill_switch.json")


def set_kill_switch(active: bool, reason: str = "") -> dict:
    KILL_SWITCH_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "active": active,
        "reason": reason,
        "updated_at": utc_now_iso(),
    }
    KILL_SWITCH_PATH.write_text(__import__("json").dumps(payload), encoding="utf-8")
    return payload


def get_kill_switch() -> dict:
    if not KILL_SWITCH_PATH.exists():
        return {"active": False, "reason": "", "updated_at": None}
    import json
    return json.loads(KILL_SWITCH_PATH.read_text(encoding="utf-8"))
