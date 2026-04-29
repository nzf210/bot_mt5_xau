from __future__ import annotations

import asyncio
import json
from shutil import which

from app.config import get_settings

REVIEW_SCHEMA = {
    "summary": "string",
    "key_findings": ["string"],
    "risks": ["string"],
    "recommended_actions": ["string"],
    "pair_session_notes": ["string"],
}


def _resolve_codex_command() -> str:
    for candidate in ["codex", "codex.cmd", "codex.exe"]:
        path = which(candidate)
        if path:
            return path
    return "codex"


def _extract_json_text(output: str) -> str:
    text = output.strip()
    if not text:
        return text
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1].strip()
    return text


async def run_periodic_llm_review(review_payload: dict) -> dict:
    settings = get_settings()
    prompt = (
        "You are reviewing an MT5 trading bot's recent performance and settings. "
        "Return ONLY valid JSON. Do not return markdown. "
        f"Use exactly this schema: {json.dumps(REVIEW_SCHEMA, ensure_ascii=False)}\n\n"
        "Review payload below:\n"
        f"{json.dumps(review_payload, ensure_ascii=False)}"
    )

    codex_cmd = _resolve_codex_command()
    args = [codex_cmd, "exec", "--skip-git-repo-check", "--output-last-message", prompt]
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=settings.openai_cli_timeout_seconds)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError("llm_review_timeout")

    stdout_text = stdout.decode("utf-8", errors="ignore").strip()
    stderr_text = stderr.decode("utf-8", errors="ignore").strip()
    if process.returncode != 0:
        raise RuntimeError(f"llm_review_failed: exit={process.returncode} stderr={stderr_text} stdout={stdout_text[:500]}")
    if not stdout_text:
        raise RuntimeError(f"llm_review_empty_output stderr={stderr_text}")

    text = _extract_json_text(stdout_text)
    return json.loads(text)
