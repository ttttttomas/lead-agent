import re

import httpx

from app.services.discovery import DiscoveryError, discover_businesses as discover_osm_businesses
from app.services.overture import OvertureError, discover_overture_businesses


def _normalize_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _dedupe_key(lead: dict) -> str:
    website = (lead.get("website") or "").lower().rstrip("/")
    if website:
        return f"web:{website}"
    phone = re.sub(r"\D", "", lead.get("phone") or "")
    if phone:
        return f"phone:{phone}"
    return f"name:{_normalize_name(lead.get('company'))}|{_normalize_name(lead.get('city'))}"


def _merge_leads(primary: dict, extra: dict) -> dict:
    merged = dict(primary)
    for key, value in extra.items():
        if value and not merged.get(key):
            merged[key] = value

    # Keep Overture as the source when it contributed the primary record, but
    # preserve where fallback enrichment came from.
    sources = []
    for source in (primary.get("source"), extra.get("source")):
        if source and source not in sources:
            sources.append(source)
    merged["source"] = "+".join(sources) if sources else "unknown"

    merged["contactable"] = any(
        merged.get(field)
        for field in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin", "website")
    )
    return merged


async def discover_businesses(industry: str, city: str, country: str, limit: int) -> list[dict]:
    """Discover businesses using Overture first and OpenStreetMap as fallback.

    Overture is preferred because its Places schema can include websites,
    emails, phones and social profiles. OSM remains useful for local coverage
    and as a resilience fallback when Overture is unavailable.
    """
    overture_leads: list[dict] = []
    overture_error: Exception | None = None

    try:
        overture_leads = await discover_overture_businesses(
            industry=industry,
            city=city,
            country=country,
            limit=limit,
        )
    except (OvertureError, httpx.HTTPError) as exc:
        overture_error = exc

    # Fetch OSM when Overture cannot satisfy the requested candidate pool.
    osm_leads: list[dict] = []
    if len(overture_leads) < limit:
        try:
            osm_leads = await discover_osm_businesses(
                industry=industry,
                city=city,
                country=country,
                limit=limit,
            )
        except (DiscoveryError, httpx.HTTPError) as exc:
            if not overture_leads:
                if overture_error:
                    raise DiscoveryError(
                        f"Overture failed ({overture_error}); OSM fallback failed ({exc})"
                    ) from exc
                raise

    merged_by_key: dict[str, dict] = {}
    name_index: dict[str, str] = {}

    for lead in [*overture_leads, *osm_leads]:
        key = _dedupe_key(lead)
        name_key = f"{_normalize_name(lead.get('company'))}|{_normalize_name(lead.get('city'))}"

        existing_key = key if key in merged_by_key else name_index.get(name_key)
        if existing_key and existing_key in merged_by_key:
            merged_by_key[existing_key] = _merge_leads(merged_by_key[existing_key], lead)
            continue

        clean = dict(lead)
        clean["contactable"] = any(
            clean.get(field)
            for field in ("email", "phone", "whatsapp", "instagram", "facebook", "linkedin", "website")
        )
        merged_by_key[key] = clean
        name_index[name_key] = key

    leads = list(merged_by_key.values())

    # Contactable records are substantially more useful for sales. Within each
    # group keep Overture records first because they generally have richer POI data.
    leads.sort(
        key=lambda lead: (
            0 if lead.get("contactable") else 1,
            0 if str(lead.get("source", "")).startswith("overture") else 1,
            str(lead.get("company", "")).lower(),
        )
    )
    return leads[:limit]
