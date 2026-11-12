from typing import Literal, Optional
from pydantic import BaseModel, Field


class ArticleRequest(BaseModel):
    """What the browser extension sends. Only url is required."""
    url: str
    title: Optional[str] = None
    text: str = ""
    author: Optional[str] = None
    publish_date: Optional[str] = None
    site_name: Optional[str] = None
    claims: list[str] = Field(default_factory=list, description="Optional user-selected claims")

class Indicator(BaseModel):
    id: str
    severity: Literal["info", "warning"]
    message: str

class ModelResult(BaseModel):
    available: bool
    predicted_label: Optional[str] = None
    probabilities: dict[str, float] = Field(default_factory=dict)
    risk_probability: Optional[float] = None
    note: str = ""

class IndicatorResult(BaseModel):
    score: float = Field(ge=0, le=1, description="0 = no warning signs found, 1 = many")
    indicators: list[Indicator]

class EvidenceItem(BaseModel):
    claim: str
    source_name: str
    url: str
    title: Optional[str] = None
    rating: Optional[str] = None
    date: Optional[str] = None

class EvidenceResult(BaseModel):
    status: Literal["found", "insufficient_evidence", "not_configured", "error"]
    claims_checked: list[str] = Field(default_factory=list)
    items: list[EvidenceItem] = Field(default_factory=list)
    note: str = ""

class AnalysisResponse(BaseModel):
    assessment: Literal["lower_concern", "some_concern", "higher_concern", "unable_to_assess"]
    summary: str
    combined_score: Optional[float] = None
    model: ModelResult
    metadata: IndicatorResult
    nlp: IndicatorResult
    language: IndicatorResult
    evidence: EvidenceResult
    limitations: list[str]
    disclaimer: str

    
