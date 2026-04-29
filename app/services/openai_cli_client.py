import asyncio
import json
from app.config import get_settings
from app.schemas import MarketRequest
from app.services.prompt_builder import build_prompt


async def analyze_with_openai_cli(market: MarketRequest) -> str:
    settings = get_settings()
    prompt = build_prompt(market, enable_vision=settings.enable_vision)
    market_json = json.dumps(market.model_dump(exclude={"chart_image_base64", "chart_image_mime"}), ensure_ascii=False)
    full_prompt = (
        f"{prompt}\n\n"
        "Structured market payload below. Return ONLY valid JSON matching the expected decision schema.\n\n"
        f"{market_json}"
    )

    process = await asyncio.create_subprocess_exec(
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--output-last-message",
        full_prompt,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=settings.openai_cli_timeout_seconds
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.communicate()
        raise RuntimeError("openai_cli_timeout")

    if process.returncode != 0:
        raise RuntimeError(
            f"openai_cli_failed: exit={process.returncode} stderr={stderr.decode('utf-8', errors='ignore').strip()}"
        )

    output = stdout.decode("utf-8", errors="ignore").strip()
    if not output:
        raise RuntimeError("openai_cli_empty_output")

    return output
