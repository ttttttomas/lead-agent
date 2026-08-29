import json

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.schemas.lead import LeadAnalysis

_engine = None


class LeadStoreError(RuntimeError):
    pass


def _get_engine():
    global _engine
    if _engine is None:
        engine_kwargs = {"pool_pre_ping": True}

        if settings.database_url.startswith("sqlite"):
            engine_kwargs["connect_args"] = {"check_same_thread": False}
        else:
            engine_kwargs["pool_recycle"] = 1800

        _engine = create_engine(settings.database_url, **engine_kwargs)
    return _engine


def init_database() -> None:
    schema = text(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name VARCHAR(255) NOT NULL,
            website VARCHAR(500),
            industry VARCHAR(150),
            city VARCHAR(150),
            country VARCHAR(150),
            contact_email VARCHAR(255),
            source VARCHAR(100),
            score INTEGER,
            opportunity VARCHAR(255),
            analysis TEXT,
            outreach_draft TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'new',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    try:
        with _get_engine().begin() as connection:
            connection.execute(schema)
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score)"))
            connection.execute(text("CREATE INDEX IF NOT EXISTS idx_leads_industry ON leads(industry)"))
    except SQLAlchemyError as exc:
        raise LeadStoreError(f"Database initialization failed: {exc}") from exc


def lead_exists(company: str, city: str, website: str | None, email: str | None) -> bool:
    clauses = ["(LOWER(company_name) = LOWER(:company) AND LOWER(COALESCE(city, '')) = LOWER(:city))"]
    params = {"company": company, "city": city}

    if website:
        clauses.append("LOWER(COALESCE(website, '')) = LOWER(:website)")
        params["website"] = website
    if email:
        clauses.append("LOWER(COALESCE(contact_email, '')) = LOWER(:email)")
        params["email"] = email

    query = text(f"SELECT id FROM leads WHERE {' OR '.join(clauses)} LIMIT 1")

    try:
        with _get_engine().connect() as connection:
            return connection.execute(query, params).first() is not None
    except SQLAlchemyError as exc:
        raise LeadStoreError(f"Database duplicate check failed: {exc}") from exc


def save_lead(
    *,
    company: str,
    website: str | None,
    industry: str,
    city: str,
    country: str,
    email: str | None,
    source: str,
    source_url: str | None,
    phone: str | None,
    analysis: LeadAnalysis,
) -> int:
    analysis_payload = analysis.model_dump()
    analysis_payload["discovery_metadata"] = {
        "source_url": source_url,
        "phone": phone,
    }

    statement = text(
        """
        INSERT INTO leads (
            company_name, website, industry, city, country, contact_email,
            source, score, opportunity, analysis, outreach_draft, status
        ) VALUES (
            :company, :website, :industry, :city, :country, :email,
            :source, :score, :opportunity, :analysis, :outreach, 'analyzed'
        )
        """
    )

    params = {
        "company": company,
        "website": website,
        "industry": industry,
        "city": city,
        "country": country,
        "email": email,
        "source": source,
        "score": analysis.score,
        "opportunity": analysis.recommended_service[:255],
        "analysis": json.dumps(analysis_payload, ensure_ascii=False),
        "outreach": analysis.outreach_message,
    }

    try:
        with _get_engine().begin() as connection:
            result = connection.execute(statement, params)
            return int(result.lastrowid)
    except SQLAlchemyError as exc:
        raise LeadStoreError(f"Database insert failed: {exc}") from exc
