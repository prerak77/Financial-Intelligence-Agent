from datetime import datetime
from enum import Enum
from typing import List, Optional

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


class PickStatus(str, Enum):
    WATCHING = "watching"
    OWNED = "owned"
    SOLD = "sold"


class StockPickCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    status: PickStatus = PickStatus.WATCHING
    entry_price: Optional[float] = Field(default=None, ge=0)
    target_price: Optional[float] = Field(default=None, ge=0)
    stop_loss: Optional[float] = Field(default=None, ge=0)
    notes: str = ""


class StockPickUpdate(BaseModel):
    status: Optional[PickStatus] = None
    entry_price: Optional[float] = Field(default=None, ge=0)
    target_price: Optional[float] = Field(default=None, ge=0)
    stop_loss: Optional[float] = Field(default=None, ge=0)
    notes: Optional[str] = None
    archived: Optional[bool] = None


class StockPickRecord(BaseModel):
    id: int
    ticker: str
    status: PickStatus
    entry_price: Optional[float]
    target_price: Optional[float]
    stop_loss: Optional[float]
    notes: str
    archived: bool = False
    created_at: datetime
    updated_at: datetime


class TransactionAction(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TransactionCreate(BaseModel):
    ticker: str = Field(min_length=1, max_length=10)
    action: TransactionAction
    price: float = Field(ge=0)
    quantity: Optional[float] = Field(default=None, gt=0)
    date: datetime
    note: str = ""


class TransactionRecord(BaseModel):
    id: int
    ticker: str
    action: TransactionAction
    price: float
    quantity: Optional[float]
    date: datetime
    note: str
    created_at: datetime


class AnalysisSnapshotRecord(BaseModel):
    ticker: str
    run_id: str
    signal: Signal
    confidence: float
    summary: str
    reliability: Reliability
    claims: List[Claim] = Field(default_factory=list)
    generated_at: datetime
    updated_at: datetime


class PriceCacheRecord(BaseModel):
    ticker: str
    price: float
    change_percent: float
    as_of: datetime
    source_name: str
    source_url: str
    updated_at: datetime
