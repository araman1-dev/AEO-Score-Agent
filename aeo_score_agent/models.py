from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageData:
    url: str
    status_code: int
    load_time_seconds: float
    html: str
    title: str
    meta_description: str
    canonical: str | None
    headings: list[str]
    paragraphs: list[str]
    list_items: list[str]
    image_alt_texts: list[str]
    links: list[str]
    schema_types: set[str] = field(default_factory=set)
    schema_payloads: list[dict[str, Any]] = field(default_factory=list)
    has_author_bio_hint: bool = False
    has_pub_date: bool = False
    has_last_updated: bool = False
    has_faq_section_hint: bool = False
    has_about_hint: bool = False
    has_trust_signals_hint: bool = False


@dataclass
class MetricResult:
    name: str
    category: str
    weight: int
    score: int
    detail: str


@dataclass
class AnalysisResult:
    pages: list[PageData]
    metrics: list[MetricResult]
    total_score: int
    score_10: float
    grade_band: str
    llm_notes: str | None = None
