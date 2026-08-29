import asyncio
import smtplib

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.schemas.lead import LeadAnalyzeRequest, LeadAnalyzeResponse
from app.services.email_notifier import send_lead_notification
from app.services.kimi import analyze_lead_with_kimi
from app.services.lead_store import LeadStoreError, get_lead, get_lead_stats, list_leads
from app.services.scraper import ScrapeError, scrape_website

router = APIRouter(prefix="/api/leads", tags=["leads"])


def _safe_notification_error(exc: Exception) -> str:
    message = str(exc).strip()
    if isinstance(exc, smtplib.SMTPAuthenticationError):
        return "Gmail authentication failed. Check SMTP_USERNAME and the Google App Password in SMTP_PASSWORD."
    if isinstance(exc, smtplib.SMTPRecipientsRefused):
        return "Gmail rejected the notification recipient. Check NOTIFICATION_EMAIL."
    if isinstance(exc, smtplib.SMTPSenderRefused):
        return "Gmail rejected the sender address. Check SMTP_USERNAME."
    if isinstance(exc, RuntimeError):
        return message or "Email notifications are not fully configured."
    return f"Email delivery failed: {message or exc.__class__.__name__}"


@router.get("")
async def read_leads(
    limit: int = Query(default=100, ge=1, le=500),
    min_score: int | None = Query(default=None, ge=0, le=100),
    industry: str | None = None,
    city: str | None = None,
):
    try:
        leads = await asyncio.to_thread(list_leads, limit, min_score, industry, city)
        return {"count": len(leads), "leads": leads}
    except LeadStoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stats")
async def read_lead_stats():
    try:
        return await asyncio.to_thread(get_lead_stats)
    except LeadStoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/{lead_id}")
async def read_lead(lead_id: int):
    try:
        lead = await asyncio.to_thread(get_lead, lead_id)
    except LeadStoreError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


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

    notification_sent = False
    notification_error = None
    try:
        await send_lead_notification(
            company=payload.company,
            website=scraped["final_url"],
            analysis=analysis,
        )
        notification_sent = True
    except (RuntimeError, OSError, smtplib.SMTPException) as exc:
        notification_error = _safe_notification_error(exc)

    return LeadAnalyzeResponse(
        company=payload.company,
        website=scraped["final_url"],
        page_title=scraped["title"],
        analysis=analysis,
        notification_sent=notification_sent,
        notification_error=notification_error,
    )
