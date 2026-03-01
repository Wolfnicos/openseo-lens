"""Tests for the structured data analyzer."""

import pytest

from openseo_lens.analyzers.structured_data import StructuredDataAnalyzer
from openseo_lens.models import Category


@pytest.fixture
def analyzer() -> StructuredDataAnalyzer:
    return StructuredDataAnalyzer()


SAMPLE_HTML_WITH_JSONLD = """
<!DOCTYPE html>
<html>
<head>
    <script type="application/ld+json">
    {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Example Corp",
        "url": "https://example.com"
    }
    </script>
</head>
<body><h1>Example</h1></body>
</html>
"""

SAMPLE_HTML_NO_STRUCTURED_DATA = """
<!DOCTYPE html>
<html>
<head><title>Example</title></head>
<body><h1>Example</h1><p>No structured data here.</p></body>
</html>
"""


@pytest.mark.asyncio
async def test_analyzer_returns_score(analyzer: StructuredDataAnalyzer) -> None:
    """Analyzer should return a score with the correct category."""
    score = await analyzer.analyze(
        url="https://example.com",
        html=SAMPLE_HTML_WITH_JSONLD,
        headers={},
    )
    assert score.category == Category.STRUCTURED_DATA
    assert 0 <= score.value <= 100


@pytest.mark.asyncio
async def test_analyzer_handles_empty_html(analyzer: StructuredDataAnalyzer) -> None:
    """Analyzer should handle empty HTML without crashing."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="",
        headers={},
    )
    assert score.category == Category.STRUCTURED_DATA
