from pydantic import BaseModel, Field

from app.schemas.lead import LeadAnalysis


class DiscoverySearchRequest(BaseModel):
    industry: str = Field(min_length=2, max_length=100)
    city: str = Field(min_length=2, max_length=120)
    country: str = Field(default="Argentina", min_length=2, max_length=120)
    limit: int = Field(default=10, ge=1, le=50)
    minimum_score: int = Field(default=50, ge=0, le=100)
    notify_each: bool = True


class AgentRunRequest(BaseModel):
    industries: list[str] = Field(min_length=1, max_length=20)
    cities: list[str] = Field(min_length=1, max_length=20)
    country: str = Field(default="Argentina", min_length=2, max_length=120)
    leads_per_search: int = Field(default=10, ge=1, le=30)
    minimum_score: int = Field(default=50, ge=0, le=100)
    notify_each: bool = True


class DiscoveredLead(BaseModel):
    company: str
    industry: str
    city: str
    country: str
    address: str | None = None
    website: str | None = None
    email: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    instagram: str | None = None
    facebook: str | None = None
    linkedin: str | None = None
    contactable: bool = False
    contact_score: int = Field(default=0, ge=0, le=100)
    opportunity_score: int | None = Field(default=None, ge=0, le=100)
    final_score: int | None = Field(default=None, ge=0, le=100)
    chain_detected: bool = False
    chain_reason: str | None = None
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
    skipped_chains: int = 0
    leads: list[DiscoveredLead]


class AgentRunResponse(BaseModel):
    searches: int
    discovered: int
    analyzed: int
    qualified: int
    skipped_duplicates: int
    skipped_chains: int = 0
    results: list[DiscoverySearchResponse]
