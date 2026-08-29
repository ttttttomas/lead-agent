import re

import httpx

USER_AGENT = "LeadAgent/0.3 (business discovery; contact: local-development)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

CATEGORY_FILTERS = {
    "hoteles": [('tourism', 'hotel'), ('tourism', 'hostel'), ('tourism', 'guest_house')],
    "hotel": [('tourism', 'hotel')],
    "restaurantes": [('amenity', 'restaurant'), ('amenity', 'fast_food')],
    "restaurante": [('amenity', 'restaurant')],
    "agencias de viajes": [('shop', 'travel_agency')],
    "agencia de viajes": [('shop', 'travel_agency')],
    "inmobiliarias": [('office', 'estate_agent')],
    "inmobiliaria": [('office', 'estate_agent')],
    "constructoras": [('craft', 'builder'), ('office', 'company')],
    "constructora": [('craft', 'builder')],
    "peluquerias": [('shop', 'hairdresser')],
    "peluquería": [('shop', 'hairdresser')],
    "gimnasios": [('leisure', 'fitness_centre')],
    "gimnasio": [('leisure', 'fitness_centre')],
    "clinicas": [('amenity', 'clinic')],
    "clínicas": [('amenity', 'clinic')],
    "clinica": [('amenity', 'clinic')],
    "dentistas": [('amenity', 'dentist')],
    "veterinarias": [('amenity', 'veterinary')],
    "farmacias": [('amenity', 'pharmacy')],
    "cafeterias": [('amenity', 'cafe')],
    "cafeterías": [('amenity', 'cafe')],
}


class DiscoveryError(RuntimeError):
    pass


def _normalize_category(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _website(tags: dict) -> str | None:
    value = tags.get("website") or tags.get("contact:website")
    if not value:
        return None
    value = value.strip()
    if value.startswith("www."):
        value = f"https://{value}"
    elif not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    return value


def _first(tags: dict, *keys: str) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value:
            return str(value).strip()
    return None


def _source_url(element: dict) -> str:
    element_type = element.get("type", "node")
    element_id = element.get("id")
    return f"https://www.openstreetmap.org/{element_type}/{element_id}"


async def _geocode_bbox(city: str, country: str) -> tuple[float, float, float, float]:
    params = {
        "q": f"{city}, {country}",
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"}

    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        response = await client.get(NOMINATIM_URL, params=params)
        response.raise_for_status()
        data = response.json()

    if not data:
        raise DiscoveryError(f"Could not locate city: {city}, {country}")

    south, north, west, east = map(float, data[0]["boundingbox"])
    return south, west, north, east


def _build_overpass_query(filters: list[tuple[str, str]], bbox: tuple[float, float, float, float]) -> str:
    south, west, north, east = bbox
    parts: list[str] = []
    for key, value in filters:
        for element_type in ("node", "way", "relation"):
            parts.append(
                f'{element_type}["{key}"="{value}"]["name"]({south},{west},{north},{east});'
            )

    return "[out:json][timeout:35];(" + "".join(parts) + ");out center tags;"


async def discover_businesses(industry: str, city: str, country: str, limit: int) -> list[dict]:
    category = _normalize_category(industry)
    filters = CATEGORY_FILTERS.get(category)
    if not filters:
        supported = ", ".join(sorted(set(CATEGORY_FILTERS.keys())))
        raise DiscoveryError(
            f"Unsupported industry '{industry}' for the free discovery provider. Supported examples: {supported}"
        )

    bbox = await _geocode_bbox(city, country)
    query = _build_overpass_query(filters, bbox)

    headers = {"User-Agent": USER_AGENT}
    async with httpx.AsyncClient(timeout=45.0, headers=headers) as client:
        response = await client.post(OVERPASS_URL, data={"data": query})
        response.raise_for_status()
        payload = response.json()

    leads: list[dict] = []
    seen: set[str] = set()

    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        name = (tags.get("name") or "").strip()
        if not name:
            continue

        phone = _first(tags, "contact:phone", "phone", "contact:mobile", "mobile")
        email = _first(tags, "contact:email", "email")
        website = _website(tags)
        dedupe_key = (website or phone or f"{name}|{city}").lower()
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        leads.append(
            {
                "company": name,
                "industry": industry,
                "city": city,
                "country": country,
                "website": website,
                "email": email,
                "phone": phone,
                "source": "openstreetmap",
                "source_url": _source_url(element),
            }
        )

        if len(leads) >= limit:
            break

    return leads
