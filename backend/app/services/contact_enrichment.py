import re
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from app.services.scraper import BROWSER_HEADERS, _is_public_host

EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{7,}\d)")
CONTACT_PATHS = ["/contacto", "/contact", "/contact-us", "/nosotros", "/about"]
SOCIAL_DOMAINS = ("instagram.com", "facebook.com", "linkedin.com")
SEARCH_URL = "https://html.duckduckgo.com/html/"


def _clean_phone(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:80] or None


def _extract_from_soup(soup: BeautifulSoup) -> dict:
    emails, phones = [], []
    whatsapp = instagram = facebook = linkedin = None
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()
        lower = href.lower()
        if lower.startswith("mailto:"):
            value = href.split(":", 1)[1].split("?", 1)[0].strip()
            if value and value not in emails:
                emails.append(value)
        elif lower.startswith("tel:"):
            value = _clean_phone(href.split(":", 1)[1])
            if value and value not in phones:
                phones.append(value)
        elif "wa.me/" in lower or "api.whatsapp.com" in lower or "whatsapp.com/send" in lower:
            whatsapp = whatsapp or href
        elif "instagram.com/" in lower:
            instagram = instagram or href
        elif "facebook.com/" in lower:
            facebook = facebook or href
        elif "linkedin.com/" in lower:
            linkedin = linkedin or href

    text = soup.get_text(" ", strip=True)
    for value in EMAIL_RE.findall(text):
        if value not in emails:
            emails.append(value)
    for value in PHONE_RE.findall(text):
        value = _clean_phone(value)
        if value and value not in phones:
            phones.append(value)

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


def _unwrap_ddg_url(href: str) -> str:
    if href.startswith("//"):
        href = "https:" + href
    parsed = urlparse(href)
    if "duckduckgo.com" in parsed.netloc:
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return unquote(target[0])
    return href


async def _search_public_presence(company: str, city: str) -> dict:
    query = f'"{company}" {city} contacto sitio oficial instagram facebook'
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), headers=BROWSER_HEADERS, follow_redirects=True) as client:
            response = await client.get(SEARCH_URL, params={"q": query})
            if response.status_code >= 400:
                return {}
            soup = BeautifulSoup(response.content, "html.parser")
    except httpx.HTTPError:
        return {}

    found = {"website": None, "instagram": None, "facebook": None, "linkedin": None}
    blocked_domains = ("google.", "tripadvisor.", "booking.com", "wikipedia.org", "youtube.com")
    for anchor in soup.select("a.result__a[href]")[:8]:
        href = _unwrap_ddg_url(anchor.get("href", ""))
        host = (urlparse(href).hostname or "").lower()
        if not host:
            continue
        if "instagram.com" in host:
            found["instagram"] = found["instagram"] or href
        elif "facebook.com" in host:
            found["facebook"] = found["facebook"] or href
        elif "linkedin.com" in host:
            found["linkedin"] = found["linkedin"] or href
        elif not any(domain in host for domain in blocked_domains) and not found["website"]:
            found["website"] = href
    return found


async def enrich_contact_data(business: dict) -> dict:
    enriched = dict(business)

    if not enriched.get("website") and not any(enriched.get(k) for k in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin")):
        enriched = _merge(enriched, await _search_public_presence(enriched.get("company", ""), enriched.get("city", "")))

    website = enriched.get("website")
    if website:
        parsed = urlparse(website)
        if parsed.scheme in {"http", "https"} and parsed.hostname and _is_public_host(parsed.hostname):
            urls = [website] + [urljoin(website, path) for path in CONTACT_PATHS]
            try:
                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0), follow_redirects=True, headers=BROWSER_HEADERS, http2=True) as client:
                    for url in urls:
                        try:
                            response = await client.get(url)
                            if response.status_code >= 400:
                                continue
                            if "html" not in response.headers.get("content-type", "").lower():
                                continue
                            enriched = _merge(enriched, _extract_from_soup(BeautifulSoup(response.content, "html.parser")))
                            if enriched.get("email") or enriched.get("phone") or enriched.get("whatsapp"):
                                break
                        except httpx.HTTPError:
                            continue
            except httpx.HTTPError:
                pass

    enriched["contactable"] = any(enriched.get(key) for key in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin"))
    return enriched
