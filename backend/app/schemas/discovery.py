from pydantic import BaseModel, Field

from app.schemas.lead import LeadAnalysis


class DiscoverySearchRequest(BaseModel):
    industry: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=120)
    country: str = Field(default="Argentina", min_length=2, max_length=120)
    limit: int = Field(default=10, ge=1, le=50)
    minimum_score: int = Field(default=50, ge=0, le=100)
    notify_each: bool = True


class DiscoveredLead(BaseModel):
    company: str
    industry: str
    city: str
    country: str
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    source: str
    source_url: str | None = None
    analysis: LeadAnalysis | None = None
    stored: bool = False
    notification_sent: bool = False
    error: str | None = None


class DiscoverySearchResponse(BaseModel):
    query: str
    discovered: int
    analyzed: int
    qualified: int
    skipped_duplicates: int
    leads: list[DiscoveredLead]
