from __future__ import annotations

import json
import os
from typing import Any


def evaluate_content_with_llm(text: str) -> tuple[dict[str, float], str | None]:
    """Optional LLM scoring hook.

    Enabled when OPENAI_API_KEY is set. Returns (scores, notes).
    Expected keys in scores: conversational_tone (0..1).
    """

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {}, None

    try:
        from openai import OpenAI
    except Exception:
        return {}, "OPENAI_API_KEY detected, but openai package is not installed."

    client = OpenAI(api_key=api_key)
    prompt = (
        "You are evaluating page content for answer engine optimization. "
        "Return compact JSON with: conversational_tone (0-1), "
        "answer_directness (0-1), eeat_confidence (0-1), notes (string)."
    )

    sample = text[:12000]
    try:
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            input=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": sample},
            ],
            temperature=0.1,
        )
        content = response.output_text
        data: dict[str, Any] = json.loads(content)
        scores = {
            "conversational_tone": float(data.get("conversational_tone", 0.6)),
            "answer_directness": float(data.get("answer_directness", 0.6)),
            "eeat_confidence": float(data.get("eeat_confidence", 0.6)),
        }
        notes = data.get("notes")
        return scores, str(notes) if notes is not None else None
    except Exception as exc:
        return {}, f"LLM evaluation unavailable: {exc}"
