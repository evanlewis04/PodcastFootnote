from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


Category = Literal[
    "ml_research",
    "biology",
    "neuroscience",
    "physics",
    "economics",
    "medicine",
    "cs_systems",
    "math_stats",
    "named_entity",
    "other",
]


class TranscriptSegment(BaseModel):
    start: float = Field(ge=0)
    duration: float = Field(ge=0)
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be blank")
        return value


class ExtractRequest(BaseModel):
    video_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    video_url: str = Field(min_length=1)
    title: Optional[str] = None
    listener_profile: str = ""
    known_terms: list[str] = Field(default_factory=list)
    transcript: list[TranscriptSegment] = Field(min_length=1)

    @field_validator("video_id", "video_url")
    @classmethod
    def strip_required_string(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("known_terms")
    @classmethod
    def normalize_known_terms(cls, values: list[str]) -> list[str]:
        return [value.strip() for value in values if value.strip()]


class TermCard(BaseModel):
    id: str = Field(min_length=1)
    term: str = Field(min_length=1)
    expansion: Optional[str] = None
    one_liner: str = Field(min_length=1)
    deeper: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    category: str = Field(min_length=1)
    timestamp: Optional[float] = Field(default=None, ge=0)
    confidence: float = Field(default=0, ge=0, le=1)

    @field_validator("id", "term", "one_liner", "deeper", "quote", "category")
    @classmethod
    def strip_term_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("expansion")
    @classmethod
    def strip_optional_expansion(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


CacheStatus = Literal["hit", "miss", "fixture"]


class ExtractionMetadata(BaseModel):
    prompt_version: str = "glossary-v1"
    model: Optional[str] = None
    cache_status: CacheStatus = "miss"
    transcript_segments: int = Field(default=0, ge=0)
    transcript_duration_seconds: Optional[float] = Field(default=None, ge=0)
    term_count: int = Field(default=0, ge=0)
    timestamped_term_count: int = Field(default=0, ge=0)
    low_confidence_term_count: int = Field(default=0, ge=0)
    timestamp_coverage: float = Field(default=0, ge=0, le=1)
    low_confidence_rate: float = Field(default=0, ge=0, le=1)
    extraction_latency_ms: Optional[int] = Field(default=None, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ExtractResponse(BaseModel):
    video_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_-]+$")
    terms: list[TermCard] = Field(default_factory=list)
    cached: bool = False
    metadata: Optional[ExtractionMetadata] = None

    model_config = ConfigDict(validate_assignment=True)


class RawExtractedTerm(BaseModel):
    term: str = Field(min_length=1)
    expansion: Optional[str] = None
    one_liner: str = Field(min_length=1)
    deeper: str = Field(min_length=1)
    quote: str = Field(min_length=1)
    category: Category

    model_config = ConfigDict(extra="forbid")

    @field_validator("term", "one_liner", "deeper", "quote")
    @classmethod
    def strip_required_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("expansion")
    @classmethod
    def strip_expansion(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        value = value.strip()
        return value or None


class KnownTerm(BaseModel):
    term: str = Field(min_length=1)
    normalized: str = Field(min_length=1)
    dismissed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_video_id: Optional[str] = None

    @field_validator("term", "normalized")
    @classmethod
    def strip_known_term_fields(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value
