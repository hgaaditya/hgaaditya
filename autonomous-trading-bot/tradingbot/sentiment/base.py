"""Sentiment interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class SentimentSignal:
    score: float          # -1 (very bearish) .. +1 (very bullish)
    label: str            # "bullish" | "bearish" | "neutral"
    rationale: str = ""

    @staticmethod
    def from_score(score: float, rationale: str = "") -> SentimentSignal:
        score = max(-1.0, min(1.0, score))
        label = "bullish" if score > 0.15 else "bearish" if score < -0.15 else "neutral"
        return SentimentSignal(score=score, label=label, rationale=rationale)


class SentimentProvider(ABC):
    @abstractmethod
    def daily_bias(self, day: date, symbols: list[str]) -> SentimentSignal:
        """A single market-wide (or symbol-aware) bias for the session."""
