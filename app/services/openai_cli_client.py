import asyncio
import json
from shutil import which

from app.config import get_settings
from app.schemas import MarketRequest
from app.services.prompt_builder import build_prompt


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


def _resolve_codex_command() -> str:
    for candidate in ["codex", "codex.cmd", "codex.exe"]:
        path = which(candidate)
        if path:
            return path
    return "codex"


async def _run_codex(args: list[str], timeout_seconds: int) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError(f"openai_cli_timeout args={' '.join(args[:6])}")

    stdout_text = stdout.decode("utf-8", errors="ignore").strip()
    stderr_text = stderr.decode("utf-8", errors="ignore").strip()
    return process.returncode, stdout_text, stderr_text


async def analyze_with_openai_cli(market: MarketRequest) -> str:
    settings = get_settings()
    prompt = build_prompt(market, enable_vision=settings.enable_vision)
    market_json = json.dumps(market.model_dump(exclude={"chart_image_base64", "chart_image_mime"}), ensure_ascii=False)
    full_prompt = (
        f"{prompt}\n\n"
        "Structured market payload below. Return ONLY valid JSON matching the expected decision schema. "
        "Do not wrap the answer in markdown fences.\n\n"
        f"{market_json}"
    )

    codex_cmd = _resolve_codex_command()
    attempts = [
        [codex_cmd, "exec", "--skip-git-repo-check", "--output-last-message", full_prompt],
        [codex_cmd, "exec", "--skip-git-repo-check", full_prompt],
    ]

    failure_notes: list[str] = []
    for args in attempts:
        returncode, stdout_text, stderr_text = await _run_codex(args, settings.openai_cli_timeout_seconds)
        if returncode == 0 and stdout_text:
            return _extract_json_text(stdout_text)
        failure_notes.append(
            f"rc={returncode} stdout={stdout_text[:400]} stderr={stderr_text[:400]} args={' '.join(args[:6])}"
        )

    raise RuntimeError("openai_cli_failed: " + " || ".join(failure_notes))
