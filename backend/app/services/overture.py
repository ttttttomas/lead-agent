import asyncio
import json
import re

import duckdb
import httpx

USER_AGENT = "LeadAgent/0.7 (business discovery; contact: local-development)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERTURE_STAC_URL = "https://stac.overturemaps.org/catalog.json"
OVERTURE_S3_ROOT = "s3://overturemaps-us-west-2/release"

# Overture keeps the legacy categories field during the current migration to
# basic_category/taxonomy. We search all three so the provider survives schema
# changes and still works with the current 2026 releases.
OVERTURE_CATEGORY_TERMS = {
    "agencias de viajes": ["travel_agency", "travel_services", "travel"],
    "agencia de viajes": ["travel_agency", "travel_services", "travel"],
    "hoteles": ["hotel", "lodging", "accommodation"],
    "hotel": ["hotel", "lodging", "accommodation"],
    "hostels": ["hostel", "lodging", "accommodation"],
    "apart hoteles": ["hotel", "apartment_hotel", "lodging"],
    "campings": ["campground", "camp_site"],
    "inmobiliarias": ["real_estate", "real_estate_agent", "estate_agent"],
    "inmobiliaria": ["real_estate", "real_estate_agent", "estate_agent"],
    "constructoras": ["contractor", "construction", "builder"],
    "constructora": ["contractor", "construction", "builder"],
    "arquitectos": ["architect", "architecture"],
    "arquitectura": ["architect", "architecture"],
    "ingenierias": ["engineer", "engineering"],
    "ingenierías": ["engineer", "engineering"],
    "restaurantes": ["restaurant", "casual_eatery"],
    "restaurante": ["restaurant", "casual_eatery"],
    "cafeterias": ["cafe", "coffee_shop"],
    "cafeterías": ["cafe", "coffee_shop"],
    "bares": ["bar", "pub"],
    "pizzerias": ["pizza_restaurant", "pizzeria"],
    "panaderias": ["bakery"],
    "panaderías": ["bakery"],
    "heladerias": ["ice_cream_shop", "ice_cream"],
    "heladerías": ["ice_cream_shop", "ice_cream"],
    "gimnasios": ["gym", "fitness_center", "fitness_centre"],
    "gimnasio": ["gym", "fitness_center", "fitness_centre"],
    "clubes deportivos": ["sports_club", "sports_center", "sports_centre"],
    "clinicas": ["clinic", "medical_clinic"],
    "clínicas": ["clinic", "medical_clinic"],
    "clinica": ["clinic", "medical_clinic"],
    "dentistas": ["dentist", "dental_clinic"],
    "odontologos": ["dentist", "dental_clinic"],
    "odontólogos": ["dentist", "dental_clinic"],
    "veterinarias": ["veterinarian", "veterinary_clinic"],
    "farmacias": ["pharmacy"],
    "opticas": ["optician", "eyewear"],
    "ópticas": ["optician", "eyewear"],
    "peluquerias": ["hair_salon", "hairdresser"],
    "peluquería": ["hair_salon", "hairdresser"],
    "barberias": ["barber", "barber_shop", "hair_salon"],
    "barberías": ["barber", "barber_shop", "hair_salon"],
    "centros de estetica": ["beauty_salon", "beauty_spa"],
    "centros de estética": ["beauty_salon", "beauty_spa"],
    "spa": ["spa", "day_spa"],
    "concesionarias": ["car_dealer", "auto_dealer"],
    "concesionaria": ["car_dealer", "auto_dealer"],
    "talleres mecanicos": ["auto_repair", "car_repair", "automotive_repair"],
    "talleres mecánicos": ["auto_repair", "car_repair", "automotive_repair"],
    "gomerias": ["tire_shop", "tyre_shop"],
    "gomerías": ["tire_shop", "tyre_shop"],
    "supermercados": ["supermarket", "grocery_store"],
    "tiendas de ropa": ["clothing_store", "clothes"],
    "mueblerias": ["furniture_store", "furniture"],
    "mueblerías": ["furniture_store", "furniture"],
    "ferreterias": ["hardware_store", "hardware"],
    "ferreterías": ["hardware_store", "hardware"],
    "colegios": ["school"],
    "escuelas": ["school"],
    "universidades": ["university"],
    "institutos": ["college", "educational_institution"],
    "estudios contables": ["accountant", "accounting"],
    "contadores": ["accountant", "accounting"],
    "abogados": ["lawyer", "law_firm", "legal_services"],
    "estudios juridicos": ["lawyer", "law_firm", "legal_services"],
    "estudios jurídicos": ["lawyer", "law_firm", "legal_services"],
    "consultoras": ["consulting", "business_consulting"],
    "agencias de marketing": ["advertising_agency", "marketing_agency", "advertising"],
    "marketing": ["advertising_agency", "marketing_agency", "advertising"],
    "seguros": ["insurance", "insurance_agency"],
    "informatica": ["computer_store", "computer_services"],
    "informática": ["computer_store", "computer_services"],
    "imprentas": ["printing", "print_shop", "copy_shop"],
    "fotografos": ["photographer", "photography"],
    "fotógrafos": ["photographer", "photography"],
    "logistica": ["logistics", "shipping_service"],
    "logística": ["logistics", "shipping_service"],
    "salones de eventos": ["event_venue", "events_venue"],
}


class OvertureError(RuntimeError):
    pass


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


async def _geocode_bbox(city: str, country: str) -> tuple[float, float, float, float]:
    params = {
        "q": f"{city}, {country}",
        "format": "jsonv2",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": USER_AGENT, "Accept-Language": "es,en;q=0.8"}
    timeout = httpx.Timeout(12.0, connect=6.0)

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        response = await client.get(NOMINATIM_URL, params=params)
        response.raise_for_status()
        data = response.json()

    if not data:
        raise OvertureError(f"Could not locate city: {city}, {country}")

    south, north, west, east = map(float, data[0]["boundingbox"])
    return south, west, north, east


async def _latest_release() -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={"User-Agent": USER_AGENT}) as client:
            response = await client.get(OVERTURE_STAC_URL)
            response.raise_for_status()
            latest = response.json().get("latest")
    except (httpx.HTTPError, ValueError) as exc:
        raise OvertureError(f"Could not resolve latest Overture release: {exc}") from exc

    if not latest or not isinstance(latest, str):
        raise OvertureError("Overture STAC catalog did not provide a latest release")
    return latest.rstrip("/").split("/")[-1]


def _social_fields(raw: object) -> dict:
    socials: list[str] = []
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            socials = parsed if isinstance(parsed, list) else []
        except json.JSONDecodeError:
            socials = []
    elif isinstance(raw, list):
        socials = [str(value) for value in raw if value]

    result = {"instagram": None, "facebook": None, "linkedin": None, "whatsapp": None}
    for value in socials:
        lower = value.lower()
        if "instagram.com/" in lower and not result["instagram"]:
            result["instagram"] = value
        elif "facebook.com/" in lower and not result["facebook"]:
            result["facebook"] = value
        elif "linkedin.com/" in lower and not result["linkedin"]:
            result["linkedin"] = value
        elif ("wa.me/" in lower or "whatsapp.com/" in lower) and not result["whatsapp"]:
            result["whatsapp"] = value
    return result


def _query_sync(
    release: str,
    bbox: tuple[float, float, float, float],
    terms: list[str],
    industry: str,
    city: str,
    country: str,
    limit: int,
) -> list[dict]:
    south, west, north, east = bbox
    path = f"{OVERTURE_S3_ROOT}/{release}/theme=places/type=place/*"

    placeholders = ",".join("?" for _ in terms)
    sql = f"""
        SELECT
            id,
            names.primary AS name,
            confidence,
            operating_status,
            categories.primary AS legacy_category,
            basic_category,
            taxonomy.primary AS taxonomy_category,
            websites[1] AS website,
            emails[1] AS email,
            phones[1] AS phone,
            CAST(socials AS JSON)::VARCHAR AS socials,
            addresses[1].freeform AS address
        FROM read_parquet('{path}', hive_partitioning=1)
        WHERE bbox.xmin BETWEEN ? AND ?
          AND bbox.ymin BETWEEN ? AND ?
          AND names.primary IS NOT NULL
          AND COALESCE(operating_status, 'open') != 'permanently_closed'
          AND (
            LOWER(COALESCE(categories.primary, '')) IN ({placeholders})
            OR LOWER(COALESCE(basic_category, '')) IN ({placeholders})
            OR LOWER(COALESCE(taxonomy.primary, '')) IN ({placeholders})
          )
        ORDER BY
            CASE WHEN emails IS NOT NULL OR phones IS NOT NULL OR websites IS NOT NULL OR socials IS NOT NULL THEN 0 ELSE 1 END,
            confidence DESC NULLS LAST
        LIMIT ?
    """

    params: list[object] = [west, east, south, north]
    params.extend(terms)
    params.extend(terms)
    params.extend(terms)
    params.append(limit)

    try:
        connection = duckdb.connect(database=":memory:")
        connection.execute("INSTALL httpfs; LOAD httpfs;")
        connection.execute("SET s3_region='us-west-2';")
        rows = connection.execute(sql, params).fetchall()
        columns = [description[0] for description in connection.description]
        connection.close()
    except Exception as exc:
        raise OvertureError(f"Overture query failed: {exc}") from exc

    leads: list[dict] = []
    for row in rows:
        item = dict(zip(columns, row))
        name = str(item.get("name") or "").strip()
        if not name:
            continue

        social_fields = _social_fields(item.get("socials"))
        website = item.get("website")
        email = item.get("email")
        phone = item.get("phone")
        contactable = bool(website or email or phone or any(social_fields.values()))

        leads.append(
            {
                "company": name,
                "industry": industry,
                "city": city,
                "country": country,
                "website": str(website).strip() if website else None,
                "email": str(email).strip() if email else None,
                "phone": str(phone).strip() if phone else None,
                "source": "overture",
                "source_url": None,
                "address": str(item.get("address") or "").strip() or None,
                "contactable": contactable,
                **social_fields,
            }
        )

    return leads


async def discover_overture_businesses(
    industry: str,
    city: str,
    country: str,
    limit: int,
) -> list[dict]:
    terms = OVERTURE_CATEGORY_TERMS.get(_normalize(industry))
    if not terms:
        return []

    release, bbox = await asyncio.gather(_latest_release(), _geocode_bbox(city, country))
    normalized_terms = sorted({_normalize(term).replace(" ", "_") for term in terms})
    return await asyncio.to_thread(
        _query_sync,
        release,
        bbox,
        normalized_terms,
        industry,
        city,
        country,
        limit,
    )
