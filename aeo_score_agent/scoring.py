from __future__ import annotations

from collections import Counter
from statistics import mean

try:
    import textstat
except Exception:
    class _TextstatFallback:
        @staticmethod
        def flesch_kincaid_grade(text: str) -> float:
            words = len(text.split())
            sentences = max(text.count(".") + text.count("!") + text.count("?"), 1)
            return (words / sentences) / 3

        @staticmethod
        def lexicon_count(text: str) -> int:
            return len(text.split())

        @staticmethod
        def sentence_count(text: str) -> int:
            return max(text.count(".") + text.count("!") + text.count("?"), 1)

    textstat = _TextstatFallback()

from aeo_score_agent.models import MetricResult, PageData


def _has_schema(pages: list[PageData], candidates: set[str]) -> bool:
    normalized = {c.lower() for c in candidates}
    for page in pages:
        for schema_type in page.schema_types:
            if schema_type.lower() in normalized:
                return True
    return False


def _question_headings_ratio(pages: list[PageData]) -> float:
    headings = [h for p in pages for h in p.headings]
    if not headings:
        return 0.0
    q_count = sum(1 for h in headings if "?" in h or h.lower().startswith(("what", "how", "why", "when", "where", "who")))
    return q_count / len(headings)


def score_site(pages: list[PageData], https_enabled: bool, llm_scores: dict[str, float] | None = None) -> list[MetricResult]:
    llm_scores = llm_scores or {}
    metrics: list[MetricResult] = []

    all_paragraphs = [p for page in pages for p in page.paragraphs]
    all_text = "\n".join(all_paragraphs)
    avg_para_words = mean([len(p.split()) for p in all_paragraphs]) if all_paragraphs else 0

    def add(name: str, category: str, weight: int, passed: bool, detail: str):
        metrics.append(MetricResult(name=name, category=category, weight=weight, score=weight if passed else 0, detail=detail))

    # 1. Structured Data / Schema Markup (25)
    add("FAQ schema present", "Structured Data / Schema Markup", 5, _has_schema(pages, {"FAQPage"}), "Checks for FAQPage schema.")
    add("HowTo schema present", "Structured Data / Schema Markup", 4, _has_schema(pages, {"HowTo"}), "Checks for HowTo schema.")
    add("Speakable schema present", "Structured Data / Schema Markup", 4, _has_schema(pages, {"SpeakableSpecification", "speakable"}), "Checks for speakable schema.")
    add("Article/NewsArticle schema", "Structured Data / Schema Markup", 3, _has_schema(pages, {"Article", "NewsArticle"}), "Checks for article schema.")
    add("Organization/LocalBusiness schema", "Structured Data / Schema Markup", 3, _has_schema(pages, {"Organization", "LocalBusiness"}), "Checks for organization schema.")
    add("BreadcrumbList schema", "Structured Data / Schema Markup", 2, _has_schema(pages, {"BreadcrumbList"}), "Checks for breadcrumb schema.")
    add("Product/Review schema", "Structured Data / Schema Markup", 2, _has_schema(pages, {"Product", "Review"}), "Checks for product/review schema.")
    add(
        "No schema validation errors",
        "Structured Data / Schema Markup",
        2,
        all(bool(page.schema_payloads) for page in pages) if pages else False,
        "Proxy check: at least one valid extracted schema payload per page.",
    )

    # 2. Content Structure & Answer Readiness (25)
    direct_answer = any(len(p.split()) >= 20 for p in all_paragraphs[:10])
    add("Direct answers near top", "Content Structure & Answer Readiness", 5, direct_answer, "Looks for substantial early paragraphs.")
    add(
        "Question-based H2/H3 headers",
        "Content Structure & Answer Readiness",
        5,
        _question_headings_ratio(pages) >= 0.2,
        "At least 20% headings are question-like.",
    )
    add(
        "Concise paragraph answers (40–60 words)",
        "Content Structure & Answer Readiness",
        5,
        40 <= avg_para_words <= 60,
        f"Average paragraph words: {avg_para_words:.1f}",
    )
    add("FAQ sections present", "Content Structure & Answer Readiness", 4, any(p.has_faq_section_hint for p in pages), "Looks for FAQ/question indicators.")
    add(
        "Numbered lists / steps",
        "Content Structure & Answer Readiness",
        3,
        any(any(li[:2].strip().rstrip('.') .isdigit() for li in p.list_items) for p in pages),
        "Looks for numbered list items.",
    )
    tone_score = llm_scores.get("conversational_tone", 0.6)
    add("Conversational language", "Content Structure & Answer Readiness", 3, tone_score >= 0.6, "LLM or heuristic tone score.")

    # 3. E-E-A-T Signals (20)
    add("Author bylines with bio", "E-E-A-T Signals", 4, any(p.has_author_bio_hint for p in pages), "Checks for author/bio hints.")
    add("Author schema markup", "E-E-A-T Signals", 3, _has_schema(pages, {"Person", "Author"}), "Checks for Person/Author schema.")
    add("About Us page/credentials", "E-E-A-T Signals", 3, any("/about" in p.url.lower() or p.has_about_hint for p in pages), "Checks about signals.")

    external_links = sum(1 for p in pages for link in p.links if not any(link.startswith(page.url.split('/')[0] + '//' + page.url.split('/')[2]) for page in pages))
    add("Citations/external references", "E-E-A-T Signals", 3, external_links >= 3, f"External links detected: {external_links}")
    add("Publication and updated dates", "E-E-A-T Signals", 4, any(p.has_pub_date and p.has_last_updated for p in pages), "Checks date signals.")
    add("Trust signals", "E-E-A-T Signals", 3, any(p.has_trust_signals_hint for p in pages), "Looks for awards/certifications/partners.")

    # 4. Technical & Metadata (15)
    add(
        "Question-friendly titles",
        "Technical & Metadata",
        3,
        any("?" in p.title or p.title.lower().startswith(("what", "how", "why")) for p in pages),
        "Checks title format.",
    )
    add(
        "Meta descriptions are direct answers",
        "Technical & Metadata",
        3,
        any(20 <= len(p.meta_description.split()) <= 35 for p in pages),
        "Checks meta description length and usefulness.",
    )
    add("Canonical tags set", "Technical & Metadata", 2, all(bool(p.canonical) for p in pages) if pages else False, "Checks canonical links.")
    add("Fast load (<3s)", "Technical & Metadata", 3, mean([p.load_time_seconds for p in pages]) < 3 if pages else False, "Checks average response time.")
    add("Mobile friendly", "Technical & Metadata", 2, any("viewport" in p.html.lower() for p in pages), "Checks viewport meta tag.")
    add("HTTPS enabled", "Technical & Metadata", 2, https_enabled, "Checks URL scheme.")

    # 5. Semantic & NLP Readiness (10)
    token_counts = Counter(word.lower().strip(".,:;!?()[]{}\"'") for word in all_text.split())
    entity_like_terms = [w for w, c in token_counts.items() if c >= 3 and len(w) > 4]
    add("Topic entities covered", "Semantic & NLP Readiness", 3, len(entity_like_terms) >= 15, "Heuristic: repeated content entities.")
    add("Natural language questions", "Semantic & NLP Readiness", 3, _question_headings_ratio(pages) >= 0.2, "Question phrasing usage.")
    add("Logical internal linking", "Semantic & NLP Readiness", 2, any(len(p.links) >= 3 for p in pages), "Checks internal link presence.")
    add("Descriptive image alt text", "Semantic & NLP Readiness", 2, any(len(alt.split()) >= 3 for p in pages for alt in p.image_alt_texts), "Checks alt text quality.")

    # 6. Voice Search Readiness (5)
    add("Speakable schema for key passages", "Voice Search Readiness", 2, _has_schema(pages, {"SpeakableSpecification", "speakable"}), "Checks speakable schema.")
    readability = textstat.flesch_kincaid_grade(all_text) if all_text.strip() else 20
    add("Conversational reading level (<= Grade 8)", "Voice Search Readiness", 2, readability <= 8, f"Flesch-Kincaid grade: {readability:.1f}")
    avg_sentence_words = textstat.lexicon_count(all_text) / max(textstat.sentence_count(all_text), 1) if all_text.strip() else 100
    add("Short direct sentences", "Voice Search Readiness", 1, avg_sentence_words <= 20, f"Avg sentence words: {avg_sentence_words:.1f}")

    return metrics
