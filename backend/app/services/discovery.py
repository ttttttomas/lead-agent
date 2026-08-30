import re

import httpx

USER_AGENT = "LeadAgent/0.6 (business discovery; contact: local-development)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

CATEGORY_FILTERS = {
    # Turismo y alojamiento
    "hoteles": [('tourism', 'hotel'), ('tourism', 'hostel'), ('tourism', 'guest_house')],
    "hotel": [('tourism', 'hotel')],
    "hostels": [('tourism', 'hostel')],
    "apart hoteles": [('tourism', 'apartment')],
    "agencias de viajes": [('shop', 'travel_agency')],
    "agencia de viajes": [('shop', 'travel_agency')],
    "campings": [('tourism', 'camp_site')],

    # Gastronomía
    "restaurantes": [('amenity', 'restaurant'), ('amenity', 'fast_food')],
    "restaurante": [('amenity', 'restaurant')],
    "cafeterias": [('amenity', 'cafe')],
    "cafeterías": [('amenity', 'cafe')],
    "bares": [('amenity', 'bar'), ('amenity', 'pub')],
    "pizzerias": [('cuisine', 'pizza')],
    "panaderias": [('shop', 'bakery')],
    "panaderías": [('shop', 'bakery')],
    "heladerias": [('amenity', 'ice_cream')],
    "heladerías": [('amenity', 'ice_cream')],

    # Inmobiliario / construcción / hogar
    "inmobiliarias": [('office', 'estate_agent')],
    "inmobiliaria": [('office', 'estate_agent')],
    "constructoras": [('craft', 'builder'), ('office', 'company')],
    "constructora": [('craft', 'builder')],
    "arquitectos": [('office', 'architect')],
    "arquitectura": [('office', 'architect')],
    "ingenierias": [('office', 'engineer')],
    "ingenierías": [('office', 'engineer')],
    "electricistas": [('craft', 'electrician')],
    "plomeros": [('craft', 'plumber')],
    "pintores": [('craft', 'painter')],
    "carpinterias": [('craft', 'carpenter')],
    "carpinterías": [('craft', 'carpenter')],
    "mueblerias": [('shop', 'furniture')],
    "mueblerías": [('shop', 'furniture')],
    "ferreterias": [('shop', 'hardware')],
    "ferreterías": [('shop', 'hardware')],
    "corralones": [('shop', 'building_materials')],

    # Salud
    "clinicas": [('amenity', 'clinic')],
    "clínicas": [('amenity', 'clinic')],
    "clinica": [('amenity', 'clinic')],
    "dentistas": [('amenity', 'dentist')],
    "odontologos": [('amenity', 'dentist')],
    "odontólogos": [('amenity', 'dentist')],
    "farmacias": [('amenity', 'pharmacy')],
    "veterinarias": [('amenity', 'veterinary')],
    "opticas": [('shop', 'optician')],
    "ópticas": [('shop', 'optician')],
    "fisioterapia": [('healthcare', 'physiotherapist')],
    "kinesiologia": [('healthcare', 'physiotherapist')],
    "kinesiología": [('healthcare', 'physiotherapist')],
    "psicologos": [('healthcare', 'psychotherapist')],
    "psicólogos": [('healthcare', 'psychotherapist')],
    "laboratorios": [('healthcare', 'laboratory')],

    # Belleza / bienestar
    "peluquerias": [('shop', 'hairdresser')],
    "peluquería": [('shop', 'hairdresser')],
    "barberias": [('shop', 'hairdresser')],
    "barberías": [('shop', 'hairdresser')],
    "centros de estetica": [('shop', 'beauty')],
    "centros de estética": [('shop', 'beauty')],
    "spa": [('leisure', 'spa')],
    "masajes": [('shop', 'massage')],
    "tatuajes": [('shop', 'tattoo')],

    # Deporte
    "gimnasios": [('leisure', 'fitness_centre')],
    "gimnasio": [('leisure', 'fitness_centre')],
    "clubes deportivos": [('leisure', 'sports_centre')],
    "canchas": [('leisure', 'pitch')],
    "piletas": [('leisure', 'swimming_pool')],

    # Automotor
    "concesionarias": [('shop', 'car')],
    "concesionaria": [('shop', 'car')],
    "talleres mecanicos": [('shop', 'car_repair')],
    "talleres mecánicos": [('shop', 'car_repair')],
    "gomerias": [('shop', 'tyres')],
    "gomerías": [('shop', 'tyres')],
    "lavaderos de autos": [('amenity', 'car_wash')],
    "alquiler de autos": [('amenity', 'car_rental')],
    "estaciones de servicio": [('amenity', 'fuel')],

    # Retail / comercios
    "supermercados": [('shop', 'supermarket')],
    "almacenes": [('shop', 'convenience')],
    "tiendas de ropa": [('shop', 'clothes')],
    "zapaterias": [('shop', 'shoes')],
    "zapaterías": [('shop', 'shoes')],
    "joyerias": [('shop', 'jewelry')],
    "joyerías": [('shop', 'jewelry')],
    "librerias": [('shop', 'books')],
    "librerías": [('shop', 'books')],
    "florerias": [('shop', 'florist')],
    "florerías": [('shop', 'florist')],
    "jugueterias": [('shop', 'toys')],
    "jugueterías": [('shop', 'toys')],
    "electronica": [('shop', 'electronics')],
    "electrónica": [('shop', 'electronics')],
    "celulares": [('shop', 'mobile_phone')],
    "pet shops": [('shop', 'pet')],

    # Educación
    "colegios": [('amenity', 'school')],
    "escuelas": [('amenity', 'school')],
    "jardines": [('amenity', 'kindergarten')],
    "universidades": [('amenity', 'university')],
    "institutos": [('amenity', 'college')],
    "academias de idiomas": [('amenity', 'language_school')],
    "autoescuelas": [('amenity', 'driving_school')],

    # Servicios profesionales
    "estudios contables": [('office', 'accountant')],
    "contadores": [('office', 'accountant')],
    "abogados": [('office', 'lawyer')],
    "estudios juridicos": [('office', 'lawyer')],
    "estudios jurídicos": [('office', 'lawyer')],
    "consultoras": [('office', 'consulting')],
    "agencias de marketing": [('office', 'advertising_agency')],
    "marketing": [('office', 'advertising_agency')],
    "seguros": [('office', 'insurance')],
    "financieras": [('office', 'financial')],
    "coworkings": [('office', 'coworking')],
    "notarias": [('office', 'notary')],
    "notarías": [('office', 'notary')],

    # Tecnología / impresión / servicios digitales
    "informatica": [('shop', 'computer')],
    "informática": [('shop', 'computer')],
    "servicio tecnico pc": [('shop', 'computer')],
    "imprentas": [('shop', 'copyshop')],
    "fotografos": [('craft', 'photographer')],
    "fotógrafos": [('craft', 'photographer')],

    # Logística / eventos
    "couriers": [('office', 'logistics')],
    "logistica": [('office', 'logistics')],
    "logística": [('office', 'logistics')],
    "salones de eventos": [('amenity', 'events_venue')],
    "organizadores de eventos": [('office', 'event_management')],
    "funerarias": [('shop', 'funeral_directors')],
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

    timeout = httpx.Timeout(12.0, connect=6.0)
    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
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

    return "[out:json][timeout:15];(" + "".join(parts) + ");out center tags;"


async def _query_overpass(query: str) -> dict:
    """Try each public provider once and fail over quickly."""
    headers = {"User-Agent": USER_AGENT}
    errors: list[str] = []
    timeout = httpx.Timeout(20.0, connect=6.0, read=20.0, write=8.0, pool=6.0)

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        for url in OVERPASS_URLS:
            try:
                response = await client.post(url, data={"data": query})
                if response.status_code in {429, 502, 503, 504}:
                    errors.append(f"{url}: HTTP {response.status_code}")
                    continue
                response.raise_for_status()
                return response.json()
            except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError, ValueError) as exc:
                errors.append(f"{url}: {exc.__class__.__name__}: {exc}")

    raise DiscoveryError(
        "All Overpass providers failed temporarily. " + " | ".join(errors)
    )


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
    payload = await _query_overpass(query)

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
