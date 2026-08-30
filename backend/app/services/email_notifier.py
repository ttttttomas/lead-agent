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
    return f'<a href="{_safe(url)}" style="color:#2563eb;text-decoration:none">{_safe(label)}</a>'


def _list_html(items: list[str]) -> str:
    if not items:
        return '<p style="color:#64748b">Sin datos detectados.</p>'
    return "<ul style=\"margin:8px 0 0 20px;padding:0;color:#475569;line-height:1.55\">" + "".join(
        f"<li style=\"margin-bottom:6px\">{_safe(item)}</li>" for item in items
    ) + "</ul>"


def _contact_html(lead: dict) -> str:
    contacts = []
    if lead.get("email"):
        contacts.append(_link(f'mailto:{lead["email"]}', lead["email"]))
    if lead.get("phone"):
        contacts.append(_link(f'tel:{lead["phone"]}', lead["phone"]))
    if lead.get("whatsapp"):
        contacts.append(_link(lead["whatsapp"], "WhatsApp"))
    if lead.get("instagram"):
        contacts.append(_link(lead["instagram"], "Instagram"))
    if lead.get("facebook"):
        contacts.append(_link(lead["facebook"], "Facebook"))
    if lead.get("linkedin"):
        contacts.append(_link(lead["linkedin"], "LinkedIn"))
    return " | ".join(contacts) if contacts else '<span style="color:#94a3b8">Sin contacto encontrado</span>'


def _errors_html(errors: list[str]) -> str:
    if not errors:
        return ""
    items = "".join(f'<li style="margin-bottom:6px">{_safe(item)}</li>' for item in errors)
    return f"""
    <div style="margin-top:24px;padding:16px 18px;border:1px solid #fed7aa;background:#fff7ed;border-radius:8px">
      <strong style="color:#9a3412">⚠️ Búsquedas no completadas ({len(errors)})</strong>
      <p style="margin:8px 0;color:#9a3412;font-size:13px">El reporte se envió igualmente con todos los leads obtenidos correctamente.</p>
      <ul style="margin:8px 0 0 18px;padding:0;color:#9a3412;font-size:12px;line-height:1.45">{items}</ul>
    </div>
    """


def _score_badge(value: int, high_priority_score: int) -> str:
    color = "#16a34a" if value >= high_priority_score else "#d97706" if value >= 50 else "#64748b"
    return f'<span style="font-weight:800;color:{color}">{value}</span>'


def _lead_rows(leads: list[dict], high_priority_score: int) -> str:
    rows = []
    for lead in leads:
        opportunity = int(lead.get("opportunity_score") or lead["analysis"].score)
        contact = int(lead.get("contact_score") or 0)
        final = int(lead.get("final_score") or opportunity)
        rows.append(f"""
        <tr>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;font-weight:700;color:#1e293b">{_safe(lead.get('company'))}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;color:#64748b">{_safe(lead.get('industry'))}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0">{_contact_html(lead)}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:center">{_score_badge(opportunity, high_priority_score)}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:center">{_score_badge(contact, 70)}</td>
          <td style="padding:12px;border-bottom:1px solid #e2e8f0;text-align:center">{_score_badge(final, high_priority_score)}</td>
        </tr>
        """)
    return "".join(rows)


def _detail_cards(leads: list[dict], high_priority_score: int) -> str:
    cards = []
    for index, lead in enumerate(leads, start=1):
        analysis = lead["analysis"]
        opportunity = int(lead.get("opportunity_score") or analysis.score)
        contact = int(lead.get("contact_score") or 0)
        final = int(lead.get("final_score") or opportunity)
        cards.append(f"""
        <div style="margin:0 0 22px 0;padding:18px;border-left:4px solid #3b82f6;background:#f8fafc;border-radius:0 8px 8px 0">
          <h3 style="margin:0 0 8px;color:#1e293b">{index}. {_safe(lead.get('company'))}</h3>
          <p style="margin:0 0 10px;color:#475569"><strong>Scores:</strong> Oportunidad {opportunity}/100 · Contacto {contact}/100 · Final {_score_badge(final, high_priority_score)}/100</p>
          <p style="margin:0 0 12px;color:#475569"><strong>Contacto:</strong> {_contact_html(lead)}</p>
          <p style="margin:0 0 6px;color:#334155"><strong>Resumen:</strong> {_safe(analysis.summary)}</p>
          <p style="margin:14px 0 4px;color:#334155"><strong>Problemas Operativos:</strong></p>{_list_html(analysis.problems)}
          <p style="margin:14px 0 4px;color:#334155"><strong>Oportunidades de Mejora:</strong></p>{_list_html(analysis.opportunities)}
          <p style="margin:14px 0 4px;color:#1e3a8a"><strong>Software Sugerido (iWEB):</strong></p>
          <p style="margin:6px 0;color:#1e40af;font-weight:700;line-height:1.55">{_safe(analysis.recommended_service)}</p>
          <p style="margin:14px 0 4px;color:#334155"><strong>Mensaje sugerido:</strong></p>
          <p style="margin:6px 0;color:#475569;line-height:1.55">{_safe(analysis.outreach_message)}</p>
        </div>
        """)
    return "".join(cards)


def _build_daily_report_html(
    leads: list[dict],
    *,
    high_priority_score: int,
    searches: int,
    skipped_duplicates: int,
    skipped_chains: int,
    errors: list[str],
) -> str:
    now = datetime.now(ZoneInfo(settings.agent_timezone))
    scored = [lead for lead in leads if lead.get("analysis")]
    contactable = sorted(
        [lead for lead in scored if lead.get("contactable")],
        key=lambda x: (x.get("final_score") or 0, x.get("contact_score") or 0),
        reverse=True,
    )
    unreachable = sorted(
        [lead for lead in scored if not lead.get("contactable")],
        key=lambda x: x.get("final_score") or 0,
        reverse=True,
    )
    final_scores = [int(lead.get("final_score") or lead["analysis"].score) for lead in scored]
    avg_final = round(sum(final_scores) / len(final_scores)) if final_scores else 0
    high_priority = sum(1 for lead in contactable if int(lead.get("final_score") or 0) >= high_priority_score)
    successful_searches = max(0, searches - len(errors))

    contactable_table = _lead_rows(contactable, high_priority_score) or '<tr><td colspan="6" style="padding:20px;text-align:center;color:#64748b">No se encontraron leads contactables nuevos.</td></tr>'
    unreachable_section = ""
    if unreachable:
        unreachable_section = f"""
        <h2 style="margin-top:30px;font-size:17px;color:#64748b;border-bottom:2px solid #e2e8f0;padding-bottom:10px">🔎 Leads sin canal de contacto ({len(unreachable)})</h2>
        <p style="color:#64748b;font-size:13px">Se conservan para investigación, pero no cuentan como leads calificados para outreach.</p>
        <table style="width:100%;border-collapse:collapse;font-size:14px"><tbody>{_lead_rows(unreachable, high_priority_score)}</tbody></table>
        """

    return f"""
    <!doctype html><html><body style="margin:0;padding:0;background:#eef2f7;font-family:Arial,Helvetica,sans-serif">
    <div style="max-width:860px;margin:24px auto;background:#ffffff;border:1px solid #dbe3ee;border-radius:8px;overflow:hidden">
      <div style="padding:30px 26px;background:linear-gradient(135deg,#26489d,#3b82f6);text-align:center;color:white">
        <h1 style="margin:0;font-size:26px">iWEB Marketing Agent</h1><p style="margin:8px 0 0">Reporte de Generación de Leads del {now.strftime('%Y-%m-%d')}</p>
      </div>
      <div style="padding:30px">
        <div style="display:flex;border:1px solid #dbe3ee;border-radius:7px;background:#f8fafc;margin-bottom:28px">
          <div style="flex:1;padding:18px;text-align:center"><div style="font-size:12px;color:#64748b">CONTACTABLES</div><div style="font-size:24px;font-weight:800;color:#1e3a8a">{len(contactable)}</div></div>
          <div style="flex:1;padding:18px;text-align:center;border-left:1px solid #cbd5e1"><div style="font-size:12px;color:#64748b">SCORE FINAL PROMEDIO</div><div style="font-size:24px;font-weight:800;color:#1e3a8a">{avg_final}/100</div></div>
          <div style="flex:1;padding:18px;text-align:center;border-left:1px solid #cbd5e1"><div style="font-size:12px;color:#64748b">ALTA PRIORIDAD</div><div style="font-size:24px;font-weight:800;color:#ef4444">{high_priority}</div></div>
        </div>

        <h2 style="font-size:17px;color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:10px">📋 Leads listos para contactar</h2>
        <div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr style="background:#f8fafc;color:#475569"><th style="padding:10px;text-align:left">Empresa</th><th style="padding:10px;text-align:left">Categoría</th><th style="padding:10px;text-align:left">Contacto</th><th style="padding:10px;text-align:center">Oportunidad</th><th style="padding:10px;text-align:center">Contacto</th><th style="padding:10px;text-align:center">Final</th></tr></thead><tbody>{contactable_table}</tbody></table></div>

        <h2 style="margin-top:30px;font-size:17px;color:#1e293b;border-bottom:2px solid #e2e8f0;padding-bottom:10px">💡 Análisis de oportunidades</h2>
        {_detail_cards(contactable, high_priority_score) if contactable else '<p style="color:#64748b">No hubo leads contactables nuevos.</p>'}
        {unreachable_section}
        {_errors_html(errors)}
        <p style="margin-top:26px;padding-top:16px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:12px">Búsquedas: {successful_searches}/{searches} completadas · Duplicados: {skipped_duplicates} · Cadenas omitidas antes de IA: {skipped_chains} · Sin contacto: {len(unreachable)} · Generado automáticamente por iWEB Marketing Agent.</p>
      </div>
    </div></body></html>
    """


def _build_daily_report_text(leads: list[dict], errors: list[str], skipped_chains: int) -> str:
    contactable = [lead for lead in leads if lead.get("analysis") and lead.get("contactable")]
    unreachable = [lead for lead in leads if lead.get("analysis") and not lead.get("contactable")]
    lines = [
        "iWEB Marketing Agent - Reporte diario",
        "",
        f"Leads contactables: {len(contactable)}",
        f"Sin contacto: {len(unreachable)}",
        f"Cadenas omitidas antes de IA: {skipped_chains}",
        "",
    ]
    for lead in sorted(contactable, key=lambda item: item.get("final_score") or 0, reverse=True):
        analysis = lead["analysis"]
        lines.extend([
            f"{lead.get('company')} - Final {lead.get('final_score')}/100",
            f"Oportunidad: {lead.get('opportunity_score')}/100 | Contacto: {lead.get('contact_score')}/100",
            f"Rubro: {lead.get('industry')}",
            f"Web: {lead.get('website') or 'No disponible'}",
            f"Email: {lead.get('email') or 'No disponible'}",
            f"Teléfono: {lead.get('phone') or 'No disponible'}",
            f"Servicio sugerido: {analysis.recommended_service}",
            "",
        ])
    if errors:
        lines.extend(["Búsquedas no completadas:", *[f"- {item}" for item in errors]])
    return "\n".join(lines)


def _send_daily_report_sync(
    leads: list[dict],
    high_priority_score: int,
    searches: int,
    skipped_duplicates: int,
    skipped_chains: int,
    errors: list[str],
) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_username
    message["To"] = settings.notification_email
    contactable = sum(1 for lead in leads if lead.get("contactable"))
    message["Subject"] = f"iWEB Marketing Agent - {contactable} leads contactables"
    message.set_content(_build_daily_report_text(leads, errors, skipped_chains))
    message.add_alternative(
        _build_daily_report_html(
            leads,
            high_priority_score=high_priority_score,
            searches=searches,
            skipped_duplicates=skipped_duplicates,
            skipped_chains=skipped_chains,
            errors=errors,
        ),
        subtype="html",
    )
    _send_message_sync(message)


async def send_daily_lead_report(
    leads: list[dict],
    *,
    high_priority_score: int,
    searches: int,
    skipped_duplicates: int,
    skipped_chains: int = 0,
    errors: list[str] | None = None,
) -> None:
    await asyncio.to_thread(
        _send_daily_report_sync,
        leads,
        high_priority_score,
        searches,
        skipped_duplicates,
        skipped_chains,
        errors or [],
    )
