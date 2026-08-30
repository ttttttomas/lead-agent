import asyncio
import html
import smtplib
from datetime import datetime
from email.message import EmailMessage
from zoneinfo import ZoneInfo

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


def _send_message_sync(message: EmailMessage) -> None:
    if not settings.smtp_username or not settings.smtp_password or not settings.notification_email:
        raise RuntimeError("Email notifications are not fully configured")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(message)


def _send_email_sync(company: str, website: str, analysis: LeadAnalysis) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_username
    message["To"] = settings.notification_email
    message["Subject"] = f"Lead Agent: {company} - score {analysis.score}/100"
    message.set_content(_build_body(company, website, analysis))
    _send_message_sync(message)


async def send_lead_notification(company: str, website: str, analysis: LeadAnalysis) -> None:
    await asyncio.to_thread(_send_email_sync, company, website, analysis)


def _safe(value: object | None) -> str:
    return html.escape(str(value or ""), quote=True)


def _link(url: str | None, label: str) -> str:
    if not url:
        return '<span style="color:#94a3b8;font-style:italic">No disponible</span>'
    safe_url = _safe(url)
    return f'<a href="{safe_url}" style="color:#2563eb;text-decoration:none">{_safe(label)}</a>'


def _list_html(items: list[str]) -> str:
    if not items:
        return '<p style="color:#64748b">Sin datos detectados.</p>'
    return "<ul style=\"margin:8px 0 0 20px;padding:0;color:#475569;line-height:1.55\">" + "".join(
        f"<li style=\"margin-bottom:6px\">{_safe(item)}</li>" for item in items
    ) + "</ul>"


def _build_daily_report_html(leads: list[dict], *, high_priority_score: int, searches: int, skipped_duplicates: int) -> str:
    now = datetime.now(ZoneInfo(settings.agent_timezone))
    scored = [lead for lead in leads if lead.get("analysis")]
    scores = [lead["analysis"].score for lead in scored]
    avg_score = round(sum(scores) / len(scores)) if scores else 0
    high_priority = sum(1 for score in scores if score >= high_priority_score)

    rows = []
    details = []
    for index, lead in enumerate(sorted(scored, key=lambda item: item["analysis"].score, reverse=True), start=1):
        analysis = lead["analysis"]
        score = analysis.score
        score_color = "#ef4444" if score >= high_priority_score else "#d97706" if score >= 50 else "#64748b"
        priority = "Alta" if score >= high_priority_score else "Media" if score >= 50 else "Baja"
        website = lead.get("website")
        email = lead.get("email")
        phone = lead.get("phone")

        rows.append(
            f"""
            <tr>
              <td style="padding:14px;border-bottom:1px solid #e2e8f0;font-weight:700;color:#1e293b">{_safe(lead.get('company'))}</td>
              <td style="padding:14px;border-bottom:1px solid #e2e8f0;color:#64748b">{_safe(lead.get('industry'))}</td>
              <td style="padding:14px;border-bottom:1px solid #e2e8f0">{_link(website, 'Visitar sitio')}</td>
              <td style="padding:14px;border-bottom:1px solid #e2e8f0">{_link(f'mailto:{email}' if email else None, email or 'No disponible')}</td>
              <td style="padding:14px;border-bottom:1px solid #e2e8f0;text-align:center">
                <span style="display:inline-block;padding:5px 8px;border-radius:6px;background:#fff1f2;color:{score_color};font-weight:800">{score}<br><span style="font-size:11px">({priority})</span></span>
              </td>
            </tr>
            """
        )

        contacts = []
        if email:
            contacts.append(_link(f"mailto:{email}", email))
        if phone:
            contacts.append(_link(f"tel:{phone}", phone))
        contact_html = " | ".join(contacts) if contacts else '<span style="color:#94a3b8">Sin contacto directo</span>'

        details.append(
            f"""
            <div style="margin:0 0 22px 0;padding:18px;border-left:4px solid #3b82f6;background:#f8fafc;border-radius:0 8px 8px 0">
              <h3 style="margin:0 0 10px;color:#1e293b">{index}. {_safe(lead.get('company'))} <span style="color:{score_color};font-size:14px">(Score: {score})</span></h3>
              <p style="margin:0 0 12px;color:#475569"><strong>Contacto:</strong> {contact_html}</p>
              <p style="margin:0 0 6px;color:#334155"><strong>Resumen:</strong> {_safe(analysis.summary)}</p>
              <p style="margin:14px 0 4px;color:#334155"><strong>Problemas Operativos:</strong></p>
              {_list_html(analysis.problems)}
              <p style="margin:14px 0 4px;color:#334155"><strong>Oportunidades de Mejora:</strong></p>
              {_list_html(analysis.opportunities)}
              <p style="margin:14px 0 4px;color:#1e3a8a"><strong>Software Sugerido (iWEB):</strong></p>
              <p style="margin:6px 0;color:#1e40af;font-weight:700;line-height:1.55">{_safe(analysis.recommended_service)}</p>
              <p style="margin:14px 0 4px;color:#334155"><strong>Mensaje sugerido:</strong></p>
              <p style="margin:6px 0;color:#475569;line-height:1.55">{_safe(analysis.outreach_message)}</p>
            </div>
            """
        )

    return f"""
    <!doctype html>
    <html>
    <body style="margin:0;padding:0;background:#eef2f7;font-family:Arial,Helvetica,sans-serif">
      <div style="max-width:760px;margin:24px auto;background:#ffffff;border:1px solid #dbe3ee;border-radius:8px;overflow:hidden">
        <div style="padding:30px 26px;background:linear-gradient(135deg,#26489d,#3b82f6);text-align:center;color:white">
          <h1 style="margin:0;font-size:26px">iWEB Marketing Agent</h1>
          <p style="margin:8px 0 0">Reporte de Generación de Leads del {now.strftime('%Y-%m-%d')}</p>
        </div>

        <div style="padding:30px">
          <div style="display:flex;border:1px solid #dbe3ee;border-radius:7px;background:#f8fafc;margin-bottom:28px">
            <div style="flex:1;padding:18px;text-align:center"><div style="font-size:12px;color:#64748b">LEADS PROCESADOS</div><div style="font-size:24px;font-weight:800;color:#1e3a8a">{len(scored)}</div></div>
            <div style="flex:1;padding:18px;text-align:center;border-left:1px solid #cbd5e1"><div style="font-size:12px;color:#64748b">SCORE PROMEDIO</div><div style="font-size:24px;font-weight:800;color:#1e3a8a">{avg_score}/100</div></div>
            <div style="flex:1;padding:18px;text-align:center;border-left:1px solid #cbd5e1"><div style="font-size:12px;color:#64748b">ALTA PRIORIDAD (≥ {high_priority_score})</div><div style="font-size:24px;font-weight:800;color:#ef4444">{high_priority}</div></div>
          </div>

          <h2 style="font-size:17px;color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:10px">📋 Listado General</h2>
          <div style="overflow-x:auto">
            <table style="width:100%;border-collapse:collapse;font-size:14px">
              <thead><tr style="background:#f8fafc;color:#475569"><th style="padding:12px;text-align:left">Empresa</th><th style="padding:12px;text-align:left">Categoría</th><th style="padding:12px;text-align:left">Web</th><th style="padding:12px;text-align:left">Email</th><th style="padding:12px;text-align:center">Score</th></tr></thead>
              <tbody>{''.join(rows) if rows else '<tr><td colspan="5" style="padding:20px;text-align:center;color:#64748b">No se encontraron leads nuevos en esta ejecución.</td></tr>'}</tbody>
            </table>
          </div>

          <h2 style="margin-top:30px;font-size:17px;color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:10px">💡 Análisis de Oportunidades Clave</h2>
          {''.join(details) if details else '<p style="color:#64748b">No hubo nuevos leads para analizar.</p>'}

          <p style="margin-top:26px;padding-top:16px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:12px">Búsquedas ejecutadas: {searches} · Duplicados omitidos: {skipped_duplicates} · Generado automáticamente por iWEB Marketing Agent.</p>
        </div>
      </div>
    </body>
    </html>
    """


def _build_daily_report_text(leads: list[dict], high_priority_score: int) -> str:
    scored = [lead for lead in leads if lead.get("analysis")]
    lines = ["iWEB Marketing Agent - Reporte diario", "", f"Leads procesados: {len(scored)}", ""]
    for lead in sorted(scored, key=lambda item: item["analysis"].score, reverse=True):
        analysis = lead["analysis"]
        priority = "ALTA" if analysis.score >= high_priority_score else "MEDIA"
        lines.extend([
            f"{lead.get('company')} - {analysis.score}/100 ({priority})",
            f"Rubro: {lead.get('industry')}",
            f"Web: {lead.get('website') or 'No disponible'}",
            f"Email: {lead.get('email') or 'No disponible'}",
            f"Servicio sugerido: {analysis.recommended_service}",
            "",
        ])
    return "\n".join(lines)


def _send_daily_report_sync(leads: list[dict], high_priority_score: int, searches: int, skipped_duplicates: int) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_username
    message["To"] = settings.notification_email
    message["Subject"] = f"iWEB Marketing Agent - Reporte diario ({len(leads)} leads)"
    message.set_content(_build_daily_report_text(leads, high_priority_score))
    message.add_alternative(
        _build_daily_report_html(
            leads,
            high_priority_score=high_priority_score,
            searches=searches,
            skipped_duplicates=skipped_duplicates,
        ),
        subtype="html",
    )
    _send_message_sync(message)


async def send_daily_lead_report(leads: list[dict], *, high_priority_score: int, searches: int, skipped_duplicates: int) -> None:
    await asyncio.to_thread(
        _send_daily_report_sync,
        leads,
        high_priority_score,
        searches,
        skipped_duplicates,
    )
