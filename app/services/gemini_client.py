import json
import httpx
from app.config import get_settings
from app.schemas import MarketRequest
from app.services.prompt_builder import build_prompt


async def analyze_with_gemini(market: MarketRequest) -> str:
    settings = get_settings()
    prompt = build_prompt(market, enable_vision=settings.enable_vision)

    parts = [{"text": prompt}, {"text": json.dumps(market.model_dump(exclude={"chart_image_base64", "chart_image_mime"}))}]
    if settings.enable_vision and market.chart_image_base64:
        parts.append({
            "inline_data": {
                "mime_type": market.chart_image_mime or "image/png",
                "data": market.chart_image_base64,
            }
        })

    payload = {"contents": [{"parts": parts}]}
    url = f"{settings.gemini_base_url}/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        return ""
    parts = candidates[0].get("content", {}).get("parts", [])
    texts = [p.get("text", "") for p in parts if p.get("text")]
    return "\n".join(texts).strip()
