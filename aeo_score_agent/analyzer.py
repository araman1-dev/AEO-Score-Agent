from __future__ import annotations

from urllib.parse import urlparse

from aeo_score_agent.crawler import SiteCrawler
from aeo_score_agent.llm import evaluate_content_with_llm
from aeo_score_agent.models import AnalysisResult
from aeo_score_agent.scoring import score_site


def grade_band(score_10: float) -> str:
    if score_10 >= 9:
        return "AEO-optimized"
    if score_10 >= 7:
        return "Good, minor gaps"
    if score_10 >= 5:
        return "Moderate readiness, significant room to improve"
    if score_10 >= 3:
        return "Low readiness"
    return "Not AEO-ready"


def analyze_url(url: str, max_pages: int = 10, enable_llm: bool = True) -> AnalysisResult:
    crawler = SiteCrawler(max_pages=max_pages)
    pages = crawler.crawl(url)
    if not pages:
        return AnalysisResult(pages=[], metrics=[], total_score=0, score_10=0.0, grade_band="Not AEO-ready")

    text_blob = "\n".join(["\n".join(page.paragraphs[:8]) for page in pages])
    llm_scores, llm_notes = evaluate_content_with_llm(text_blob) if enable_llm else ({}, None)

    https_enabled = urlparse(pages[0].url).scheme.lower() == "https"
    metrics = score_site(pages, https_enabled=https_enabled, llm_scores=llm_scores)

    total = sum(m.score for m in metrics)
    score_10 = round(total / 10.0, 2)

    return AnalysisResult(
        pages=pages,
        metrics=metrics,
        total_score=total,
        score_10=score_10,
        grade_band=grade_band(score_10),
        llm_notes=llm_notes,
    )
