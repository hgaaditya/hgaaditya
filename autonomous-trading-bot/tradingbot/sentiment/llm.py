"""Claude-API sentiment adapter (optional).

Implements the same SentimentProvider interface as the rule-based scorer, so the
engine treats them interchangeably — swap via config (`sentiment.provider: llm`).
Requires `pip install '.[llm]'` and an ANTHROPIC_API_KEY. Falls back to a clear
error rather than silently returning neutral, so misconfiguration is visible.

Design note: the LLM is asked for a JSON verdict (score + rationale) over the
morning's headlines and macro calendar. Keep the prompt auditable and the output
constrained; never let free-form model text drive orders directly — it only
produces a bounded bias score that the risk engine still governs.
"""

from __future__ import annotations

import json
import os
from datetime import date

from tradingbot.sentiment.base import SentimentProvider, SentimentSignal

_MODEL = "claude-opus-4-8"

_PROMPT = """You are a markets analyst. Given today's headlines for the Indian
market, return ONLY a JSON object: {{"score": <float -1..1>, "rationale": "<short>"}}.
Score -1 = very bearish, +1 = very bullish, 0 = neutral. Headlines:
{headlines}
"""


class ClaudeSentiment(SentimentProvider):
    def __init__(self, headlines: list[str] | None = None, model: str = _MODEL):
        self.headlines = headlines or []
        self.model = model

    def daily_bias(self, day: date, symbols: list[str]) -> SentimentSignal:  # noqa: ARG002
        if not self.headlines:
            return SentimentSignal.from_score(0.0, "no headlines available (neutral)")
        try:
            import anthropic
        except ImportError as e:  # pragma: no cover - optional dep
            raise RuntimeError("ClaudeSentiment requires: pip install '.[llm]'") from e

        if not os.getenv("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY not set for ClaudeSentiment")

        client = anthropic.Anthropic()
        text = "\n".join(f"- {h}" for h in self.headlines)
        resp = client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": _PROMPT.format(headlines=text)}],
        )
        payload = json.loads(resp.content[0].text)
        return SentimentSignal.from_score(
            float(payload["score"]), rationale=payload.get("rationale", "")
        )
