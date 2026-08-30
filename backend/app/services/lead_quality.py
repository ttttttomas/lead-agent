from urllib.parse import urlparse

# Conservative list: only brands/corporations where local branches usually do
# not control their core website/software purchasing decisions.
CHAIN_MARKERS = {
    "hilton": "Hilton",
    "doubletree": "Hilton / DoubleTree",
    "hampton by hilton": "Hilton / Hampton",
    "marriott": "Marriott",
    "sheraton": "Marriott / Sheraton",
    "westin": "Marriott / Westin",
    "courtyard by marriott": "Marriott / Courtyard",
    "accor": "Accor",
    "ibis": "Accor / ibis",
    "novotel": "Accor / Novotel",
    "mercure": "Accor / Mercure",
    "sofitel": "Accor / Sofitel",
    "nh hotel": "NH Hotels",
    "nh collection": "NH Hotels",
    "eurostars": "Eurostars Hotel Company",
    "exe hotel": "Eurostars / Exe Hotels",
    "holiday inn": "IHG / Holiday Inn",
    "intercontinental": "IHG / InterContinental",
    "crowne plaza": "IHG / Crowne Plaza",
    "wyndham": "Wyndham",
    "ramada": "Wyndham / Ramada",
    "howard johnson": "Wyndham / Howard Johnson",
    "hyatt": "Hyatt",
    "four seasons": "Four Seasons",
    "best western": "Best Western",
}

CHAIN_DOMAINS = {
    "hilton.com": "Hilton",
    "marriott.com": "Marriott",
    "all.accor.com": "Accor",
    "accor.com": "Accor",
    "nh-hotels.com": "NH Hotels",
    "eurostarshotels.com": "Eurostars Hotel Company",
    "ihg.com": "IHG",
    "hyatt.com": "Hyatt",
    "wyndhamhotels.com": "Wyndham",
    "bestwestern.com": "Best Western",
    "fourseasons.com": "Four Seasons",
}


def detect_large_chain(company: str, website: str | None = None) -> tuple[bool, str | None]:
    normalized_name = " ".join((company or "").lower().split())
    for marker, brand in CHAIN_MARKERS.items():
        if marker in normalized_name:
            return True, f"Marca/cadena detectada: {brand}"

    if website:
        try:
            hostname = (urlparse(website).hostname or "").lower()
        except ValueError:
            hostname = ""
        for domain, brand in CHAIN_DOMAINS.items():
            if hostname == domain or hostname.endswith(f".{domain}"):
                return True, f"Dominio corporativo detectado: {brand}"

    return False, None


def calculate_contact_score(business: dict) -> int:
    """Score how actionable the public contact data is, capped at 100.

    Direct channels are worth more than passive profiles. A website helps but
    does not by itself make a lead strongly contactable.
    """
    score = 0
    if business.get("email"):
        score += 30
    if business.get("whatsapp"):
        score += 30
    if business.get("phone"):
        score += 20
    if business.get("instagram"):
        score += 10
    if business.get("linkedin"):
        score += 8
    if business.get("facebook"):
        score += 5
    if business.get("website"):
        score += 10
    return min(score, 100)


def calculate_final_score(opportunity_score: int, contact_score: int) -> int:
    """Commercial ranking: opportunity matters most, contactability breaks ties."""
    opportunity = max(0, min(int(opportunity_score), 100))
    contact = max(0, min(int(contact_score), 100))
    return round(opportunity * 0.7 + contact * 0.3)
