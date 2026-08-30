import logging

from fastapi import HTTPException

from app.core.config import settings
from app.routes.discovery import _process_search
from app.schemas.discovery import DiscoverySearchRequest
from app.services.email_notifier import send_daily_lead_report

logger = logging.getLogger(__name__)


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


async def run_daily_agent() -> dict:
    industries = _csv(settings.agent_industries)
    cities = _csv(settings.agent_cities)

    if not industries or not cities:
        raise RuntimeError("AGENT_INDUSTRIES and AGENT_CITIES must contain at least one value")

    all_leads: list[dict] = []
    errors: list[str] = []
    searches = 0
    discovered = 0
    analyzed = 0
    qualified = 0
    skipped_duplicates = 0

    for city in cities:
        for industry in industries:
            searches += 1
            payload = DiscoverySearchRequest(
                industry=industry,
                city=city,
                country=settings.agent_country,
                limit=settings.agent_leads_per_search,
                minimum_score=settings.agent_minimum_score,
                notify_each=False,
            )

            try:
                result = await _process_search(payload)
            except HTTPException as exc:
                errors.append(f"{industry} / {city}: {exc.detail}")
                logger.warning("Scheduled lead search failed: %s / %s: %s", industry, city, exc.detail)
                continue
            except Exception as exc:
                errors.append(f"{industry} / {city}: {exc}")
                logger.exception("Unexpected scheduled lead search failure")
                continue

            discovered += result.discovered
            analyzed += result.analyzed
            qualified += result.qualified
            skipped_duplicates += result.skipped_duplicates

            for lead in result.leads:
                if lead.analysis is None:
                    continue
                all_leads.append(
                    {
                        "company": lead.company,
                        "industry": lead.industry,
                        "city": lead.city,
                        "country": lead.country,
                        "website": lead.website,
                        "email": lead.email,
                        "phone": lead.phone,
                        "source": lead.source,
                        "source_url": lead.source_url,
                        "analysis": lead.analysis,
                    }
                )

    await send_daily_lead_report(
        all_leads,
        high_priority_score=settings.agent_high_priority_score,
        searches=searches,
        skipped_duplicates=skipped_duplicates,
    )

    return {
        "status": "completed",
        "searches": searches,
        "discovered": discovered,
        "analyzed": analyzed,
        "qualified": qualified,
        "skipped_duplicates": skipped_duplicates,
        "report_leads": len(all_leads),
        "email_sent": True,
        "errors": errors,
    }
