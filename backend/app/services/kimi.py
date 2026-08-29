import json

import httpx

from app.core.config import settings
from app.schemas.lead import LeadAnalysis

SYSTEM_PROMPT = """You are a B2B sales analyst for a software development agency.
Analyze the public website content of a potential client and identify realistic software opportunities.
Do not invent facts that are not supported by the supplied website text.
Return ONLY valid JSON matching this exact schema:
{
  "score": 0,
  "summary": "string",
  "problems": ["string"],
  "opportunities": ["string"],
  "recommended_service": "string",
  "outreach_message": "string"
}
The score must be an integer from 0 to 100 and should measure how strong the lead is for custom software, web development, ecommerce, booking systems, dashboards, automation, integrations, or redesign work.
The outreach message must be short, personalized, professional, and avoid exaggerated claims.
"""


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

    async with httpx.AsyncClient(timeout=90.0) as client:
        response = await client.post(
            f"{settings.nvidia_base_url}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    return data["choices"][0]["message"]["content"]


def _extract_json(raw: str) -> dict:
    cleaned = raw.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].lstrip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Kimi did not return valid JSON")
        return json.loads(cleaned[start : end + 1])


async def analyze_lead_with_kimi(
    company: str,
    website: str,
    page_title: str | None,
    website_text: str,
) -> LeadAnalysis:
    user_prompt = f"""Potential client: {company}
Website: {website}
Page title: {page_title or 'Unknown'}

Public website text:
---
{website_text}
---

Analyze this company as a potential lead for a software development agency.
"""

    raw = await chat_with_kimi(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1800,
    )

    parsed = _extract_json(raw)
    return LeadAnalysis.model_validate(parsed)
