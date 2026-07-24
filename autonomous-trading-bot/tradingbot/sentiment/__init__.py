"""Sentiment providers: turn news/events into a daily directional bias.

Pluggable behind one interface. Default is a transparent rule-based scorer; an
optional Claude-API adapter implements the same interface for richer analysis.
"""

from __future__ import annotations

from tradingbot.sentiment.base import SentimentProvider, SentimentSignal
from tradingbot.sentiment.rules import RuleBasedSentiment


def build_sentiment(provider: str) -> SentimentProvider:
    if provider == "none":
        return RuleBasedSentiment(headlines=[])  # neutral
    if provider == "rules":
        return RuleBasedSentiment()
    if provider == "llm":
        from tradingbot.sentiment.llm import ClaudeSentiment

        return ClaudeSentiment()
    raise KeyError(f"Unknown sentiment provider '{provider}'")


__all__ = ["SentimentProvider", "SentimentSignal", "RuleBasedSentiment", "build_sentiment"]
