"""Tests for the extractability analyzer."""

import pytest

from openseo_lens.analyzers.extractability import ExtractabilityAnalyzer
from openseo_lens.models import Category


@pytest.fixture
def analyzer() -> ExtractabilityAnalyzer:
    return ExtractabilityAnalyzer()


SAMPLE_WELL_STRUCTURED = """
<!DOCTYPE html>
<html lang="en">
<head><title>Guide: How to Optimize for AI Search</title></head>
<body>
    <main>
        <article>
            <h1>How to Optimize for AI Search</h1>
            <section>
                <h2>Understanding AI Crawlers</h2>
                <p>AI search engines process content differently than traditional crawlers.</p>
            </section>
            <section>
                <h2>Best Practices</h2>
                <ul>
                    <li>Use semantic HTML</li>
                    <li>Add structured data</li>
                    <li>Write clear, factual content</li>
                </ul>
            </section>
        </article>
    </main>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_analyzer_returns_score(analyzer: ExtractabilityAnalyzer) -> None:
    """Analyzer should return a score with the correct category."""
    score = await analyzer.analyze(
        url="https://example.com",
        html=SAMPLE_WELL_STRUCTURED,
        headers={},
    )
    assert score.category == Category.EXTRACTABILITY
    assert 0 <= score.value <= 100


@pytest.mark.asyncio
async def test_analyzer_handles_empty_html(analyzer: ExtractabilityAnalyzer) -> None:
    """Analyzer should handle empty HTML without crashing."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="",
        headers={},
    )
    assert score.category == Category.EXTRACTABILITY
