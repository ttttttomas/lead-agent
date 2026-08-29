import json

import httpx

from app.core.config import settings
from app.schemas.lead import LeadAnalysis

SYSTEM_PROMPT = """You are a B2B sales analyst for a software development agency.
Analyze only the public facts supplied about a potential client and identify realistic software opportunities.
Do not invent facts, technologies, missing features, or business problems that are not supported by the supplied data.
If the company has no known website, you may treat the absence of a website in the supplied discovery data as a digital-presence opportunity, but do not claim the company definitively has no website outside that data source.
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
The outreach message must be short, personalized, professional, and avoid exaggerated or unverified claims.
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


async def _analyze_prompt(user_prompt: str) -> LeadAnalysis:
    raw = await chat_with_kimi(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=1800,
    )
    return LeadAnalysis.model_validate(_extract_json(raw))


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
    return await _analyze_prompt(user_prompt)


async def analyze_listing_with_kimi(
    *,
    company: str,
    industry: str,
    city: str,
    country: str,
    website: str | None,
    email: str | None,
    phone: str | None,
    source: str,
) -> LeadAnalysis:
    user_prompt = f"""Potential client discovered from a public business listing.
Company: {company}
Industry/search category: {industry}
City: {city}
Country: {country}
Website found in listing: {website or 'Not provided by source'}
Public email found: {email or 'Not provided'}
Public phone found: {phone or 'Not provided'}
Discovery source: {source}

No readable website content is available for this analysis. Base the assessment only on these listing facts. If no website was provided by the source, frame website development as a possible opportunity rather than a certainty.
"""
    return await _analyze_prompt(user_prompt)
