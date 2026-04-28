import json
import re
from typing import Any


JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_first_json_block(text: str) -> str:
    if not text:
        return ""
    match = JSON_BLOCK_RE.search(text)
    return match.group(0) if match else ""


def safe_json_loads(text: str) -> dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}
