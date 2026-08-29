import httpx

from app.core.config import settings


async def chat_with_kimi(messages: list[dict], max_tokens: int = 2048) -> str:
    if not settings.nvidia_api_key:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    payload = {
        "model": settings.kimi_model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
        "stream": False,
    }

    headers = {
        "Authorization": f"Bearer {settings.nvidia_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.nvidia_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"]
