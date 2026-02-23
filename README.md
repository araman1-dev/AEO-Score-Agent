# AEO-Score-Agent

A CLI agent that asks for a website URL, crawls the site, and computes an **AEO Readiness Score** from 1–10 using your checklist.

## What it does

- Prompts for a URL when invoked (or accepts `--url`)
- Crawls a starting URL and subpages on the same domain
- Parses HTML with BeautifulSoup
- Extracts schema/structured data via extruct
- Evaluates technical + content heuristics across:
  - Structured Data / Schema Markup (25)
  - Content Structure & Answer Readiness (25)
  - E-E-A-T Signals (20)
  - Technical & Metadata (15)
  - Semantic & NLP Readiness (10)
  - Voice Search Readiness (5)
- Outputs raw score `/100`, converted score `/10`, and grade band
- Optionally calls an LLM (OpenAI) for conversational tone scoring

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python -m aeo_score_agent.cli
```

Example with flags:

```bash
python -m aeo_score_agent.cli --url https://example.com --max-pages 12
```

Disable LLM scoring:

```bash
python -m aeo_score_agent.cli --url https://example.com --disable-llm
```

## Optional LLM setup

If you want LLM-assisted content quality checks:

```bash
export OPENAI_API_KEY=your_key_here
export OPENAI_MODEL=gpt-4o-mini
```

If no key is set, the agent runs fully in heuristic mode.

## Notes

- Crawling is intentionally capped with `--max-pages` to keep runs fast.
- Some checks are heuristic proxies (e.g., schema validation) and should be paired with manual verification tools for production audits.
