import json
from collections.abc import AsyncIterator
import httpx
from app.core.config import settings
from app.services.ai.base import AIProvider

class OpenAICompatibleProvider(AIProvider):
    async def stream_chat(self, messages: list[dict], model: str | None = None) -> AsyncIterator[str]:
        if not settings.ai_api_key:
            raise RuntimeError("AI_API_KEY is missing. Add it to backend/.env and restart the API.")

        url = settings.ai_base_url.rstrip("/") + "/chat/completions"
        payload = {
            "model": model or settings.ai_model,
            "messages": messages,
            "temperature": settings.ai_temperature,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {settings.ai_api_key}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=15.0)) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    raise RuntimeError(f"AI provider returned {response.status_code}: {body.decode('utf-8', 'replace')[:500]}")
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                        if content:
                            yield content
                    except (json.JSONDecodeError, IndexError, AttributeError):
                        continue
