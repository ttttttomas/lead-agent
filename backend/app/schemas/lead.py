from pydantic import BaseModel, Field, HttpUrl


class LeadAnalyzeRequest(BaseModel):
    company: str = Field(min_length=2, max_length=200)
    website: HttpUrl


class LeadAnalysis(BaseModel):
    score: int = Field(ge=0, le=100)
    summary: str
    problems: list[str]
    opportunities: list[str]
    recommended_service: str
    outreach_message: str


class LeadAnalyzeResponse(BaseModel):
    company: str
    website: str
    page_title: str | None = None
    analysis: LeadAnalysis
    notification_sent: bool = False
    notification_error: str | None = None
