import httpx
from fastapi import APIRouter, HTTPException

from app.schemas.lead import LeadAnalyzeRequest, LeadAnalyzeResponse
from app.services.kimi import analyze_lead_with_kimi
from app.services.scraper import ScrapeError, scrape_website

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.post("/analyze", response_model=LeadAnalyzeResponse)
async def analyze_lead(payload: LeadAnalyzeRequest):
    website = str(payload.website)

    try:
        scraped = await scrape_website(website)
    except ScrapeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    try:
        analysis = await analyze_lead_with_kimi(
            company=payload.company,
            website=scraped["final_url"],
            page_title=scraped["title"],
            website_text=scraped["text"],
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"AI analysis failed: {exc}") from exc

    return LeadAnalyzeResponse(
        company=payload.company,
        website=scraped["final_url"],
        page_title=scraped["title"],
        analysis=analysis,
    )
