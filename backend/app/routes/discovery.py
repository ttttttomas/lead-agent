import asyncio
import smtplib

import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.discovery import (
    AgentRunRequest,
    AgentRunResponse,
    DiscoveredLead,
    DiscoverySearchRequest,
    DiscoverySearchResponse,
)
from app.services.discovery import DiscoveryError, discover_businesses
from app.services.email_notifier import send_lead_notification
from app.services.kimi import analyze_lead_with_kimi, analyze_listing_with_kimi
from app.services.lead_store import LeadStoreError, lead_exists, save_lead
from app.services.scraper import ScrapeError, scrape_website

router = APIRouter(tags=["discovery"])


async def _listing_analysis(business: dict):
    return await analyze_listing_with_kimi(
        company=business["company"],
        industry=business["industry"],
        city=business["city"],
        country=business["country"],
        website=business.get("website"),
        email=business.get("email"),
        phone=business.get("phone"),
        source=business["source"],
    )


def _candidate_limit(requested_leads: int) -> int:
    """Fetch enough candidates so duplicates do not consume the requested limit."""
    return min(max(requested_leads * 8, requested_leads + 20), 200)


async def _process_search(payload: DiscoverySearchRequest) -> DiscoverySearchResponse:
    candidate_limit = _candidate_limit(payload.limit)

    try:
        businesses = await discover_businesses(
            industry=payload.industry,
            city=payload.city,
            country=payload.country,
            limit=candidate_limit,
        )
    except (DiscoveryError, httpx.HTTPError) as exc:
        raise HTTPException(status_code=502, detail=f"Discovery failed: {exc}") from exc

    results: list[DiscoveredLead] = []
    analyzed = 0
    qualified = 0
    skipped_duplicates = 0

    for business in businesses:
        # payload.limit now means NEW analyzed leads, not merely raw candidates.
        if analyzed >= payload.limit:
            break

        result = DiscoveredLead(**business)

        try:
            duplicate = await asyncio.to_thread(
                lead_exists,
                business["company"],
                business["city"],
                business.get("website"),
                business.get("email"),
            )
        except LeadStoreError as exc:
            duplicate = False
            result.error = str(exc)

        if duplicate:
            skipped_duplicates += 1
            continue

        try:
            website_for_analysis = business.get("website")
            if website_for_analysis:
                try:
                    scraped = await scrape_website(website_for_analysis)
                    analysis = await analyze_lead_with_kimi(
                        company=business["company"],
                        website=scraped["final_url"],
                        page_title=scraped["title"],
                        website_text=scraped["text"],
                    )
                    result.website = scraped["final_url"]
                except ScrapeError:
                    analysis = await _listing_analysis(business)
            else:
                analysis = await _listing_analysis(business)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            result.error = f"{result.error + ' | ' if result.error else ''}Analysis: {exc}"
            results.append(result)
            continue

        result.analysis = analysis
        analyzed += 1
        if analysis.score >= payload.minimum_score:
            qualified += 1

        try:
            await asyncio.to_thread(
                save_lead,
                company=business["company"],
                website=result.website,
                industry=business["industry"],
                city=business["city"],
                country=business["country"],
                email=business.get("email"),
                source=business["source"],
                source_url=business.get("source_url"),
                phone=business.get("phone"),
                analysis=analysis,
            )
            result.stored = True
        except LeadStoreError as exc:
            result.error = f"{result.error + ' | ' if result.error else ''}{exc}"

        if payload.notify_each:
            try:
                await send_lead_notification(
                    company=business["company"],
                    website=result.website or business.get("source_url") or "No website found",
                    analysis=analysis,
                )
                result.notification_sent = True
            except (RuntimeError, OSError, smtplib.SMTPException) as exc:
                result.error = f"{result.error + ' | ' if result.error else ''}Email: {exc}"

        results.append(result)

    return DiscoverySearchResponse(
        query=f"{payload.industry} in {payload.city}, {payload.country}",
        discovered=len(businesses),
        analyzed=analyzed,
        qualified=qualified,
        skipped_duplicates=skipped_duplicates,
        leads=results,
    )


@router.post("/api/discovery/search", response_model=DiscoverySearchResponse)
async def search_leads(payload: DiscoverySearchRequest):
    return await _process_search(payload)


@router.post("/api/agent/run", response_model=AgentRunResponse)
async def run_agent(payload: AgentRunRequest):
    results: list[DiscoverySearchResponse] = []

    for city in payload.cities:
        for industry in payload.industries:
            search_payload = DiscoverySearchRequest(
                industry=industry,
                city=city,
                country=payload.country,
                limit=payload.leads_per_search,
                minimum_score=payload.minimum_score,
                notify_each=payload.notify_each,
            )
            results.append(await _process_search(search_payload))

    return AgentRunResponse(
        searches=len(results),
        discovered=sum(item.discovered for item in results),
        analyzed=sum(item.analyzed for item in results),
        qualified=sum(item.qualified for item in results),
        skipped_duplicates=sum(item.skipped_duplicates for item in results),
        results=results,
    )
