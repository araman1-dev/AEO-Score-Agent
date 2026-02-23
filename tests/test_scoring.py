from aeo_score_agent.models import PageData
from aeo_score_agent.scoring import score_site


def _sample_page() -> PageData:
    return PageData(
        url="https://example.com",
        status_code=200,
        load_time_seconds=0.4,
        html='<html><head><meta name="viewport" content="width=device-width, initial-scale=1"></head><body></body></html>',
        title="What is Example?",
        meta_description="This is a concise answer about example readiness and optimization for answer engines.",
        canonical="https://example.com",
        headings=["What is Example?", "How to use Example"],
        paragraphs=["This paragraph contains enough words to serve as a direct answer for users and search agents."],
        list_items=["1. First step", "2. Second step"],
        image_alt_texts=["team standing in front of office"],
        links=["https://example.com/about", "https://wikipedia.org/wiki/Example"],
        schema_types={"FAQPage", "Organization", "SpeakableSpecification"},
        schema_payloads=[{"@type": "FAQPage"}],
        has_author_bio_hint=True,
        has_pub_date=True,
        has_last_updated=True,
        has_faq_section_hint=True,
        has_about_hint=True,
        has_trust_signals_hint=True,
    )


def test_score_site_returns_metrics_sum_to_100_weight():
    page = _sample_page()
    metrics = score_site([page], https_enabled=True)
    assert sum(m.weight for m in metrics) == 100
    assert len(metrics) > 0
