"""Tests for the crawlability analyzer."""

import pytest

from openseo_lens.analyzers.crawlability import AI_BOTS, CrawlabilityAnalyzer
from openseo_lens.models import Category


@pytest.fixture
def analyzer() -> CrawlabilityAnalyzer:
    return CrawlabilityAnalyzer()


@pytest.mark.asyncio
async def test_analyzer_returns_score(analyzer: CrawlabilityAnalyzer) -> None:
    """Analyzer should return a score with the correct category."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="<html><body></body></html>",
        headers={},
    )
    assert score.category == Category.CRAWLABILITY
    assert 0 <= score.value <= 100


@pytest.mark.asyncio
async def test_analyzer_handles_tdm_header(analyzer: CrawlabilityAnalyzer) -> None:
    """Analyzer should process TDM-Reservation header."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="<html><body></body></html>",
        headers={"TDM-Reservation": "1"},
    )
    assert score.category == Category.CRAWLABILITY


def test_ai_bots_registry() -> None:
    """AI bots registry should contain known crawlers."""
    assert "GPTBot" in AI_BOTS
    assert "ChatGPT-User" in AI_BOTS
    assert "Google-Extended" in AI_BOTS
    assert "GoogleOther" in AI_BOTS
    assert "anthropic-ai" in AI_BOTS
    assert "ClaudeBot" in AI_BOTS
    assert "PerplexityBot" in AI_BOTS
    assert "meta-externalagent" in AI_BOTS
    assert len(AI_BOTS) == 12
