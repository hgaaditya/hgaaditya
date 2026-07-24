"""Rule-based sentiment (default): lexicon scoring over supplied headlines.

Free, fully local, deterministic. In production, feed it the morning's headlines
from an RSS/news source; with no headlines it returns neutral (no tilt). This is
intentionally simple and auditable — every point of the score is explainable.
"""

from __future__ import annotations

import re
from datetime import date

from tradingbot.sentiment.base import SentimentProvider, SentimentSignal

_POSITIVE = {
    "surge", "rally", "gain", "gains", "record", "beat", "beats", "upgrade",
    "growth", "profit", "bullish", "rebound", "optimism", "boost", "strong",
    "recovery", "inflows", "rate cut", "stimulus",
}
_NEGATIVE = {
    "plunge", "crash", "fall", "falls", "loss", "losses", "miss", "downgrade",
    "slump", "bearish", "recession", "fear", "selloff", "weak", "default",
    "outflows", "rate hike", "inflation", "war", "sanction", "sanctions",
}


class RuleBasedSentiment(SentimentProvider):
    def __init__(self, headlines: list[str] | None = None):
        # `None` means "no feed wired yet" -> neutral. `[]` also neutral.
        self.headlines = headlines if headlines is not None else []

    def daily_bias(self, day: date, symbols: list[str]) -> SentimentSignal:  # noqa: ARG002
        if not self.headlines:
            return SentimentSignal.from_score(0.0, "no headlines available (neutral)")

        pos = neg = 0
        for line in self.headlines:
            tokens = set(re.findall(r"[a-z]+(?: [a-z]+)?", line.lower()))
            pos += len(tokens & _POSITIVE)
            neg += len(tokens & _NEGATIVE)

        total = pos + neg
        raw = 0.0 if total == 0 else (pos - neg) / total
        return SentimentSignal.from_score(
            raw, rationale=f"{pos} positive vs {neg} negative cues in {len(self.headlines)} headlines"
        )
