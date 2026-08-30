import asyncio
import logging

from fastapi import HTTPException

from app.core.config import settings
from app.routes.discovery import _process_search
from app.schemas.discovery import DiscoverySearchRequest
from app.services.email_notifier import send_daily_lead_report

logger = logging.getLogger(__name__)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


async def _run_one_search(industry: str, city: str, semaphore: asyncio.Semaphore) -> dict:
    payload = DiscoverySearchRequest(
        industry=industry,
        city=city,
        country=settings.agent_country,
        limit=settings.agent_leads_per_search,
        minimum_score=settings.agent_minimum_score,
        notify_each=False,
    )

    async with semaphore:
        try:
            result = await _process_search(payload)
            return {"industry": industry, "city": city, "result": result, "error": None}
        except HTTPException as exc:
            error = str(exc.detail)
            logger.warning("Scheduled lead search failed: %s / %s: %s", industry, city, error)
            return {"industry": industry, "city": city, "result": None, "error": error}
        except Exception as exc:
            logger.exception("Unexpected scheduled lead search failure: %s / %s", industry, city)
            return {"industry": industry, "city": city, "result": None, "error": str(exc)}


async def run_daily_agent() -> dict:
    industries = _csv(settings.agent_industries)
    cities = _csv(settings.agent_cities)
    if not industries or not cities:
        raise RuntimeError("AGENT_INDUSTRIES and AGENT_CITIES must contain at least one value")

    combinations = [(industry, city) for city in cities for industry in industries]
    semaphore = asyncio.Semaphore(max(1, settings.agent_max_concurrency))
    outcomes = await asyncio.gather(*(_run_one_search(industry, city, semaphore) for industry, city in combinations))

    all_leads: list[dict] = []
    errors: list[str] = []
    discovered = analyzed = qualified = skipped_duplicates = 0

    for outcome in outcomes:
        if outcome["error"]:
            errors.append(f'{outcome["industry"]} / {outcome["city"]}: {outcome["error"]}')
            continue
        result = outcome["result"]
        if result is None:
            continue

        discovered += result.discovered
        analyzed += result.analyzed
        qualified += result.qualified
        skipped_duplicates += result.skipped_duplicates

        for lead in result.leads:
            if lead.analysis is None:
                continue
            all_leads.append({
                "company": lead.company,
                "industry": lead.industry,
                "city": lead.city,
                "country": lead.country,
                "website": lead.website,
                "email": lead.email,
                "phone": lead.phone,
                "whatsapp": lead.whatsapp,
                "instagram": lead.instagram,
                "facebook": lead.facebook,
                "linkedin": lead.linkedin,
                "contactable": lead.contactable,
                "source": lead.source,
                "source_url": lead.source_url,
                "analysis": lead.analysis,
            })

    # Contactable leads first; unreachable leads remain visible in a secondary section.
    all_leads.sort(key=lambda item: (bool(item.get("contactable")), item["analysis"].score), reverse=True)

    await send_daily_lead_report(
        all_leads,
        high_priority_score=settings.agent_high_priority_score,
        searches=len(combinations),
        skipped_duplicates=skipped_duplicates,
        errors=errors,
    )

    return {
        "status": "completed",
        "searches": len(combinations),
        "successful_searches": len(combinations) - len(errors),
        "failed_searches": len(errors),
        "discovered": discovered,
        "analyzed": analyzed,
        "qualified": qualified,
        "contactable": sum(1 for lead in all_leads if lead.get("contactable")),
        "without_contact": sum(1 for lead in all_leads if not lead.get("contactable")),
        "skipped_duplicates": skipped_duplicates,
        "report_leads": len(all_leads),
        "email_sent": True,
        "errors": errors,
    }
