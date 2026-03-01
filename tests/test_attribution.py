"""Tests for the attribution analyzer."""

import pytest

from openseo_lens.analyzers.attribution import AttributionAnalyzer
from openseo_lens.models import Category


@pytest.fixture
def analyzer() -> AttributionAnalyzer:
    return AttributionAnalyzer()


SAMPLE_HTML_WITH_AUTHOR = """
<!DOCTYPE html>
<html>
<head>
    <meta name="author" content="Dr. Jane Smith">
    <meta property="article:published_time" content="2026-01-15">
</head>
<body>
    <article>
        <h1>Expert Analysis of AI Search Trends</h1>
        <p>By <span itemprop="author">Dr. Jane Smith, PhD in Computer Science</span></p>
        <p>Published: January 15, 2026</p>
    </article>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_analyzer_returns_score(analyzer: AttributionAnalyzer) -> None:
    """Analyzer should return a score with the correct category."""
    score = await analyzer.analyze(
        url="https://example.com",
        html=SAMPLE_HTML_WITH_AUTHOR,
        headers={},
    )
    assert score.category == Category.ATTRIBUTION
    assert 0 <= score.value <= 100


@pytest.mark.asyncio
async def test_analyzer_handles_empty_html(analyzer: AttributionAnalyzer) -> None:
    """Analyzer should handle empty HTML without crashing."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="",
        headers={},
    )
    assert score.category == Category.ATTRIBUTION
