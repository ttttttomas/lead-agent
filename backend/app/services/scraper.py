import ipaddress
import socket
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/151.0.0.0 Safari/537.36"
)
MAX_TEXT_CHARS = 18000

BROWSER_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}


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


async def _fetch(client: httpx.AsyncClient, url: str) -> httpx.Response:
    response = await client.get(url)

    # Some sites reject the first request unless it looks like a normal
    # navigation that already has a same-origin Referer.
    if response.status_code in {403, 406, 429}:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}/"
        retry_headers = {
            "Referer": origin,
            "Origin": f"{parsed.scheme}://{parsed.netloc}",
        }
        response = await client.get(url, headers=retry_headers)

    return response


async def scrape_website(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ScrapeError("Invalid website URL")

    if not _is_public_host(parsed.hostname):
        raise ScrapeError("Website host is not publicly reachable")

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0),
            follow_redirects=True,
            headers=BROWSER_HEADERS,
            http2=True,
        ) as client:
            response = await _fetch(client, url)

            if response.status_code == 403:
                raise ScrapeError(
                    "Website blocked the automated request (403). "
                    "This site likely uses anti-bot protection and may require a browser-based scraper."
                )

            response.raise_for_status()
    except ScrapeError:
        raise
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
