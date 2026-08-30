import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.scraper import BROWSER_HEADERS, ScrapeError, _is_public_host

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")

CONTACT_PATHS = ["/contacto", "/contact", "/contact-us", "/nosotros", "/about"]


def _clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:80] or None


def _normalize_social(value: str | None, domain: str) -> str | None:
    if not value:
        return None
    value = value.strip()
    if value.startswith("@"):
        return f"https://{domain}/{value[1:]}"
    if value.startswith("www."):
        return f"https://{value}"
    if not value.startswith(("http://", "https://")) and domain in value:
        return f"https://{value}"
    return value


def _extract_from_soup(soup: BeautifulSoup) -> dict:
    emails: list[str] = []
    phones: list[str] = []
    whatsapp = None
    instagram = None
    facebook = None
    linkedin = None

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        lower = href.lower()

        if lower.startswith("mailto:"):
            email = href.split(":", 1)[1].split("?", 1)[0].strip()
            if email and email not in emails:
                emails.append(email)
        elif lower.startswith("tel:"):
            phone = _clean_phone(href.split(":", 1)[1])
            if phone and phone not in phones:
                phones.append(phone)
        elif "wa.me/" in lower or "api.whatsapp.com" in lower or "whatsapp.com/send" in lower:
            whatsapp = whatsapp or href
        elif "instagram.com/" in lower:
            instagram = instagram or href
        elif "facebook.com/" in lower:
            facebook = facebook or href
        elif "linkedin.com/" in lower:
            linkedin = linkedin or href

    text = soup.get_text(" ", strip=True)
    for email in EMAIL_RE.findall(text):
        if email not in emails:
            emails.append(email)
    for phone in PHONE_RE.findall(text):
        cleaned = _clean_phone(phone)
        if cleaned and cleaned not in phones:
            phones.append(cleaned)

    return {
        "email": emails[0] if emails else None,
        "phone": phones[0] if phones else None,
        "whatsapp": whatsapp,
        "instagram": instagram,
        "facebook": facebook,
        "linkedin": linkedin,
    }


def _merge(base: dict, extra: dict) -> dict:
    merged = dict(base)
    for key, value in extra.items():
        if value and not merged.get(key):
            merged[key] = value
    return merged


async def enrich_contact_data(business: dict) -> dict:
    enriched = dict(business)

    # Normalize social/contact fields already present in discovery metadata.
    enriched["instagram"] = _normalize_social(enriched.get("instagram"), "instagram.com")
    enriched["facebook"] = _normalize_social(enriched.get("facebook"), "facebook.com")
    enriched["linkedin"] = _normalize_social(enriched.get("linkedin"), "linkedin.com")

    website = enriched.get("website")
    if not website:
        enriched["contactable"] = any(
            enriched.get(key) for key in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin")
        )
        return enriched

    parsed = urlparse(website)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or not _is_public_host(parsed.hostname):
        enriched["contactable"] = any(
            enriched.get(key) for key in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin")
        )
        return enriched

    urls = [website] + [urljoin(website, path) for path in CONTACT_PATHS]

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(12.0, connect=6.0),
            follow_redirects=True,
            headers=BROWSER_HEADERS,
            http2=True,
        ) as client:
            for url in urls:
                try:
                    response = await client.get(url)
                    if response.status_code >= 400:
                        continue
                    content_type = response.headers.get("content-type", "").lower()
                    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
                        continue
                    soup = BeautifulSoup(response.content, "html.parser")
                    enriched = _merge(enriched, _extract_from_soup(soup))

                    # Stop early once we have at least one direct channel and one social/web channel.
                    if enriched.get("email") or enriched.get("phone") or enriched.get("whatsapp"):
                        if enriched.get("instagram") or enriched.get("facebook") or enriched.get("linkedin"):
                            break
                except httpx.HTTPError:
                    continue
    except (httpx.HTTPError, ScrapeError):
        pass

    enriched["contactable"] = any(
        enriched.get(key) for key in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin")
    )
    return enriched
