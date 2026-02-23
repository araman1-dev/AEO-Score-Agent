from __future__ import annotations

import argparse
from collections import defaultdict

from aeo_score_agent.analyzer import analyze_url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AEO Score Agent")
    parser.add_argument("--url", help="Website URL to analyze")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximum pages to crawl")
    parser.add_argument("--disable-llm", action="store_true", help="Disable optional LLM quality scoring")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    url = args.url or input("Enter the website URL to run AEO readiness scoring: ").strip()
    if not url:
        print("No URL provided. Exiting.")
        return 1

    print(f"\nAnalyzing {url} ...")
    result = analyze_url(url=url, max_pages=args.max_pages, enable_llm=not args.disable_llm)

    if not result.pages:
        print("Could not crawl any HTML pages. Please verify the URL and try again.")
        return 1

    print(f"\nCrawled pages: {len(result.pages)}")
    print(f"Raw score: {result.total_score}/100")
    print(f"AEO score: {result.score_10}/10")
    print(f"Grade: {result.grade_band}")
    if result.llm_notes:
        print(f"LLM notes: {result.llm_notes}")

    by_category = defaultdict(list)
    for metric in result.metrics:
        by_category[metric.category].append(metric)

    print("\nDetailed checklist scoring:")
    for category, metrics in by_category.items():
        category_points = sum(m.score for m in metrics)
        category_total = sum(m.weight for m in metrics)
        print(f"\n{category} ({category_points}/{category_total})")
        for m in metrics:
            state = "✅" if m.score == m.weight else "❌"
            print(f"  {state} {m.name}: {m.score}/{m.weight} — {m.detail}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
