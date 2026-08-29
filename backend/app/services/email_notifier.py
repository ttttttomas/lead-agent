import asyncio
import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.schemas.lead import LeadAnalysis


def _build_body(company: str, website: str, analysis: LeadAnalysis) -> str:
    problems = "\n".join(f"- {item}" for item in analysis.problems) or "- Sin problemas detectados"
    opportunities = "\n".join(f"- {item}" for item in analysis.opportunities) or "- Sin oportunidades detectadas"

    return f"""Nuevo lead analizado: {company}

Web: {website}
Score: {analysis.score}/100

Resumen
{analysis.summary}

Problemas detectados
{problems}

Oportunidades
{opportunities}

Servicio recomendado
{analysis.recommended_service}

Mensaje sugerido
{analysis.outreach_message}
"""


def _send_email_sync(company: str, website: str, analysis: LeadAnalysis) -> None:
    if not settings.smtp_username or not settings.smtp_password or not settings.notification_email:
        raise RuntimeError("Email notifications are not fully configured")

    message = EmailMessage()
    message["From"] = settings.smtp_username
    message["To"] = settings.notification_email
    message["Subject"] = f"Lead Agent: {company} - score {analysis.score}/100"
    message.set_content(_build_body(company, website, analysis))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


async def send_lead_notification(company: str, website: str, analysis: LeadAnalysis) -> None:
    await asyncio.to_thread(_send_email_sync, company, website, analysis)
