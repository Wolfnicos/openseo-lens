"""Comprehensive tests for the structured data analyzer."""

import pytest

from openseo_lens.analyzers.structured_data import (
    MicrodataItem,
    StructuredDataAnalyzer,
    StructuredDataSummary,
    analyze_structured_data,
    extract_jsonld_blocks,
    extract_microdata,
    has_rdfa,
)
from openseo_lens.models import Category, Severity

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer() -> StructuredDataAnalyzer:
    return StructuredDataAnalyzer()


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

HTML_ARTICLE_COMPLETE = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "How AI Search is Changing SEO",
  "author": {"@type": "Person", "name": "Jane Smith"},
  "datePublished": "2026-01-15",
  "image": "https://example.com/image.jpg",
  "description": "A deep dive into AI-powered search engines."
}
</script>
</head>
<body><h1>Article</h1></body>
</html>
"""

HTML_ARTICLE_MISSING_PROPS = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "My Post"
}
</script>
</head>
<body><h1>Article</h1></body>
</html>
"""

HTML_FAQPAGE_COMPLETE = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is AI SEO?",
      "acceptedAnswer": {"@type": "Answer", "text": "It is optimizing for AI search."}
    }
  ]
}
</script>
</head>
<body><h1>FAQ</h1></body>
</html>
"""

HTML_NO_STRUCTURED_DATA = """
<!DOCTYPE html>
<html>
<head><title>Example</title></head>
<body><h1>No structured data here.</h1></body>
</html>
"""

HTML_INVALID_JSON = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{ this is not valid json !!!
</script>
</head>
<body><h1>Example</h1></body>
</html>
"""

HTML_WRONG_CONTEXT = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://example.org",
  "@type": "Article",
  "headline": "Test"
}
</script>
</head>
<body></body>
</html>
"""

HTML_MICRODATA = """
<!DOCTYPE html>
<html>
<body>
<div itemscope itemtype="https://schema.org/Product">
  <span itemprop="name">Widget Pro</span>
  <span itemprop="description">A great widget</span>
  <span itemprop="image">https://example.com/img.jpg</span>
</div>
</body>
</html>
"""

HTML_RDFA = """
<!DOCTYPE html>
<html vocab="https://schema.org/" typeof="Article">
<head><title>Test</title></head>
<body>
  <span property="name">My Article</span>
</body>
</html>
"""

HTML_GRAPH_ARRAY = """
<!DOCTYPE html>
<html>
<head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@graph": [
    {"@type": "Organization", "name": "ACME Corp", "url": "https://acme.com", "description": "A corp"},
    {"@type": "WebPage", "name": "Home", "description": "Welcome"}
  ]
}
</script>
</head>
<body></body>
</html>
"""


# ---------------------------------------------------------------------------
# extract_jsonld_blocks
# ---------------------------------------------------------------------------

class TestExtractJsonLdBlocks:
    def test_empty_html(self) -> None:
        assert extract_jsonld_blocks("") == []

    def test_no_jsonld(self) -> None:
        assert extract_jsonld_blocks(HTML_NO_STRUCTURED_DATA) == []

    def test_valid_article(self) -> None:
        blocks = extract_jsonld_blocks(HTML_ARTICLE_COMPLETE)
        assert len(blocks) == 1
        assert blocks[0].schema_type == "Article"
        assert blocks[0].has_valid_context is True
        assert blocks[0].error is None

    def test_invalid_json_captured(self) -> None:
        blocks = extract_jsonld_blocks(HTML_INVALID_JSON)
        assert len(blocks) == 1
        assert blocks[0].parsed is None
        assert blocks[0].error is not None

    def test_wrong_context_flagged(self) -> None:
        blocks = extract_jsonld_blocks(HTML_WRONG_CONTEXT)
        assert len(blocks) == 1
        assert blocks[0].has_valid_context is False

    def test_graph_array_expanded(self) -> None:
        blocks = extract_jsonld_blocks(HTML_GRAPH_ARRAY)
        assert len(blocks) == 2
        types = {b.schema_type for b in blocks}
        assert "Organization" in types
        assert "WebPage" in types

    def test_http_context_accepted(self) -> None:
        html = """<script type="application/ld+json">{"@context": "http://schema.org", "@type": "Person", "name": "Bob"}</script>"""
        blocks = extract_jsonld_blocks(html)
        assert blocks[0].has_valid_context is True

    def test_schema_type_list(self) -> None:
        html = (
            '<script type="application/ld+json">'
            '{"@context": "https://schema.org", "@type": ["Article", "NewsArticle"], "headline": "Test"}'
            "</script>"
        )
        blocks = extract_jsonld_blocks(html)
        assert blocks[0].schema_type in {"Article", "NewsArticle"}

    def test_multiple_script_blocks(self) -> None:
        html = (
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"Organization","name":"X","url":"https://x.com","description":"Y"}</script>'
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"FAQPage","mainEntity":[]}</script>'
        )
        blocks = extract_jsonld_blocks(html)
        assert len(blocks) == 2


# ---------------------------------------------------------------------------
# extract_microdata
# ---------------------------------------------------------------------------

class TestExtractMicrodata:
    def test_empty_html(self) -> None:
        assert extract_microdata("") == []

    def test_no_microdata(self) -> None:
        assert extract_microdata(HTML_NO_STRUCTURED_DATA) == []

    def test_detects_product_microdata(self) -> None:
        items = extract_microdata(HTML_MICRODATA)
        assert len(items) == 1
        assert items[0].item_type == "https://schema.org/Product"
        assert "name" in items[0].properties
        assert "description" in items[0].properties

    def test_returns_microdata_item_type(self) -> None:
        items = extract_microdata(HTML_MICRODATA)
        assert isinstance(items[0], MicrodataItem)


# ---------------------------------------------------------------------------
# has_rdfa
# ---------------------------------------------------------------------------

class TestHasRdfa:
    def test_empty_html(self) -> None:
        assert has_rdfa("") is False

    def test_no_rdfa(self) -> None:
        assert has_rdfa(HTML_NO_STRUCTURED_DATA) is False

    def test_detects_rdfa(self) -> None:
        assert has_rdfa(HTML_RDFA) is True


# ---------------------------------------------------------------------------
# analyze_structured_data (scoring)
# ---------------------------------------------------------------------------

class TestAnalyzeStructuredData:
    def test_no_data_returns_zero(self) -> None:
        summary = StructuredDataSummary()
        score, issues = analyze_structured_data(summary)
        assert score == 0
        high = [i for i in issues if i.severity == Severity.HIGH]
        assert any("No structured data" in i.title for i in high)

    def test_complete_article_scores_high(self) -> None:
        blocks = extract_jsonld_blocks(HTML_ARTICLE_COMPLETE)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        score, issues = analyze_structured_data(summary)
        assert score >= 80

    def test_article_missing_props_scores_medium(self) -> None:
        blocks = extract_jsonld_blocks(HTML_ARTICLE_MISSING_PROPS)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        score, _ = analyze_structured_data(summary)
        assert 40 <= score < 80

    def test_missing_props_generates_issue(self) -> None:
        blocks = extract_jsonld_blocks(HTML_ARTICLE_MISSING_PROPS)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        _, issues = analyze_structured_data(summary)
        missing_issues = [i for i in issues if "missing AI-critical" in i.title]
        assert len(missing_issues) == 1
        assert "author" in missing_issues[0].details["missing_properties"]
        assert "datePublished" in missing_issues[0].details["missing_properties"]

    def test_invalid_json_generates_high_issue(self) -> None:
        blocks = extract_jsonld_blocks(HTML_INVALID_JSON)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        _, issues = analyze_structured_data(summary)
        high = [i for i in issues if i.severity == Severity.HIGH]
        assert any("Invalid JSON" in i.title for i in high)

    def test_wrong_context_generates_issue(self) -> None:
        blocks = extract_jsonld_blocks(HTML_WRONG_CONTEXT)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        _, issues = analyze_structured_data(summary)
        assert any("@context" in i.title for i in issues)

    def test_faqpage_complete_scores_high(self) -> None:
        blocks = extract_jsonld_blocks(HTML_FAQPAGE_COMPLETE)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        score, _ = analyze_structured_data(summary)
        assert score >= 70

    def test_microdata_detected_info_issue(self) -> None:
        items = extract_microdata(HTML_MICRODATA)
        summary = StructuredDataSummary(microdata_items=items)
        _, issues = analyze_structured_data(summary)
        assert any("Microdata" in i.title for i in issues)

    def test_rdfa_detected_info_issue(self) -> None:
        summary = StructuredDataSummary(has_rdfa=True)
        _, issues = analyze_structured_data(summary)
        assert any("RDFa" in i.title for i in issues)

    def test_graph_array_both_types_found(self) -> None:
        blocks = extract_jsonld_blocks(HTML_GRAPH_ARRAY)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        score, issues = analyze_structured_data(summary)
        info = [i for i in issues if i.severity == Severity.INFO and "Detected schema" in i.title]
        assert len(info) == 1
        assert "Organization" in info[0].details["types"]

    def test_score_clamped_to_100(self) -> None:
        blocks = extract_jsonld_blocks(HTML_ARTICLE_COMPLETE)
        summary = StructuredDataSummary(jsonld_blocks=blocks, has_rdfa=True)
        score, _ = analyze_structured_data(summary)
        assert score <= 100

    def test_all_issues_have_correct_category(self) -> None:
        blocks = extract_jsonld_blocks(HTML_ARTICLE_MISSING_PROPS)
        summary = StructuredDataSummary(jsonld_blocks=blocks)
        _, issues = analyze_structured_data(summary)
        for issue in issues:
            assert issue.category == Category.STRUCTURED_DATA


# ---------------------------------------------------------------------------
# Full Analyzer Integration
# ---------------------------------------------------------------------------

class TestStructuredDataAnalyzer:
    @pytest.mark.asyncio
    async def test_returns_correct_category(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_ARTICLE_COMPLETE, {})
        assert score.category == Category.STRUCTURED_DATA

    @pytest.mark.asyncio
    async def test_score_in_valid_range(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_ARTICLE_COMPLETE, {})
        assert 0 <= score.value <= 100

    @pytest.mark.asyncio
    async def test_complete_article_scores_above_80(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_ARTICLE_COMPLETE, {})
        assert score.value >= 80

    @pytest.mark.asyncio
    async def test_no_structured_data_scores_zero(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_NO_STRUCTURED_DATA, {})
        assert score.value == 0

    @pytest.mark.asyncio
    async def test_article_missing_props_has_issues(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_ARTICLE_MISSING_PROPS, {})
        missing = [i for i in score.issues if "missing AI-critical" in i.title]
        assert len(missing) >= 1

    @pytest.mark.asyncio
    async def test_invalid_json_detected(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_INVALID_JSON, {})
        high_issues = [i for i in score.issues if i.severity == Severity.HIGH]
        assert any("Invalid JSON" in i.title for i in high_issues)

    @pytest.mark.asyncio
    async def test_microdata_detected(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_MICRODATA, {})
        assert any("Microdata" in i.title for i in score.issues)

    @pytest.mark.asyncio
    async def test_rdfa_detected(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_RDFA, {})
        assert any("RDFa" in i.title for i in score.issues)

    @pytest.mark.asyncio
    async def test_handles_empty_html(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", "", {})
        assert score.category == Category.STRUCTURED_DATA
        assert score.value == 0

    @pytest.mark.asyncio
    async def test_faqpage_complete(self, analyzer: StructuredDataAnalyzer) -> None:
        score = await analyzer.analyze("https://example.com", HTML_FAQPAGE_COMPLETE, {})
        assert score.value >= 70
