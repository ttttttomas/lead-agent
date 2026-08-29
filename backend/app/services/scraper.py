import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (compatible; LeadAgent/0.1; +https://github.com/ttttttomas/lead-agent)"
MAX_TEXT_CHARS = 18000


class ScrapeError(RuntimeError):
    pass


def _is_public_host(hostname: str) -> bool:
    try:
        addresses = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False
    return True


async def scrape_website(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ScrapeError("Invalid website URL")

    if not _is_public_host(parsed.hostname):
        raise ScrapeError("Website host is not publicly reachable")

    headers = {"User-Agent": USER_AGENT}

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise ScrapeError(f"Could not fetch website: {exc}") from exc

    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        raise ScrapeError("Website did not return HTML content")

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    text = " ".join(soup.stripped_strings)
    text = " ".join(text.split())

    if not text:
        raise ScrapeError("Website returned no readable text")

    return {
        "final_url": str(response.url),
        "title": title,
        "text": text[:MAX_TEXT_CHARS],
    }
