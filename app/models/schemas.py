from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Signal(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    MIXED_SIGNAL = "MIXED_SIGNAL"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class ClaimSentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class SourceType(str, Enum):
    PRICE = "price"
    NEWS = "news"
    SEC_FILING = "sec_filing"


class Citation(BaseModel):
    source_type: SourceType
    title: str
    url: str
    published_at: datetime
    retrieved_at: datetime


class Claim(BaseModel):
    claim: str
    sentiment: ClaimSentiment
    citations: List[Citation] = Field(default_factory=list)


class Reliability(BaseModel):
    citation_coverage: float = 0.0
    source_conflict: bool = False
    freshness_hours_max: float = 0.0
    warnings: List[str] = Field(default_factory=list)


class StockAnalysis(BaseModel):
    run_id: str
    generated_at: datetime
    ticker: str
    signal: Signal
    confidence: float = 0.0
    summary: str
    claims: List[Claim] = Field(default_factory=list)
    reliability: Reliability


class AnalyzeRequest(BaseModel):
    watchlist: List[str] = Field(min_length=1, max_length=5)


class AnalyzeResponse(BaseModel):
    run_id: str
    generated_at: datetime
    analyses: List[StockAnalysis]
    citation_coverage_avg: float
    low_confidence_rate: float
    avg_runtime_per_ticker: float
    failure_recovery_rate: float
