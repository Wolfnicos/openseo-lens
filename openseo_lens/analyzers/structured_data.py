"""Structured data analyzer — JSON-LD, Microdata, and RDFa validation.

Detects and validates structured data markup on web pages, checking
for schema.org compliance and completeness. Identifies missing schemas
that are critical for AI search citation (FAQ, HowTo, Article, Organization).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup

from openseo_lens.analyzers import AnalyzerBase
from openseo_lens.models import Category, Issue, Score, Severity

# schema.org context variants accepted as valid
VALID_SCHEMA_CONTEXTS = {"https://schema.org", "http://schema.org", "https://schema.org/", "http://schema.org/"}

# AI-critical schema types and the properties that matter for AI citation
AI_CRITICAL_SCHEMAS: dict[str, list[str]] = {
    "Article": ["headline", "author", "datePublished", "image", "description"],
    "NewsArticle": ["headline", "author", "datePublished", "image", "description"],
    "BlogPosting": ["headline", "author", "datePublished", "description"],
    "FAQPage": ["mainEntity"],
    "HowTo": ["name", "step"],
    "Product": ["name", "image", "description", "offers"],
    "Organization": ["name", "url", "description"],
    "Person": ["name", "url"],
    "Event": ["name", "startDate", "location"],
    "Recipe": ["name", "recipeIngredient", "recipeInstructions"],
    "WebPage": ["name", "description"],
    "LocalBusiness": ["name", "address", "telephone"],
}


@dataclass
class JsonLdBlock:
    """A single JSON-LD block extracted from the page."""

    raw: str
    parsed: dict[str, Any] | None  # None if JSON is invalid
    schema_type: str | None = None
    has_valid_context: bool = False
    error: str | None = None  # parse error if any


@dataclass
class MicrodataItem:
    """A Microdata item detected in HTML."""

    item_type: str | None  # value of itemtype attribute
    properties: list[str] = field(default_factory=list)  # itemprop names found


@dataclass
class StructuredDataSummary:
    """Aggregated structured data findings for a page."""

    jsonld_blocks: list[JsonLdBlock] = field(default_factory=list)
    microdata_items: list[MicrodataItem] = field(default_factory=list)
    has_rdfa: bool = False


def extract_jsonld_blocks(html: str) -> list[JsonLdBlock]:
    """Extract and parse all JSON-LD script blocks from HTML.

    Args:
        html: Raw HTML content.

    Returns:
        List of JsonLdBlock, one per <script type="application/ld+json"> tag.
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    blocks: list[JsonLdBlock] = []

    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.get_text(strip=True)
        if not raw:
            continue

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            blocks.append(JsonLdBlock(raw=raw, parsed=None, error=str(e)))
            continue

        # Handle both single object and @graph array
        objects = []
        if isinstance(parsed, dict):
            graph = parsed.get("@graph")
            objects = graph if isinstance(graph, list) else [parsed]
        elif isinstance(parsed, list):
            objects = parsed

        for obj in objects:
            if not isinstance(obj, dict):
                continue
            context = obj.get("@context", "")
            schema_type = obj.get("@type")
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else None

            blocks.append(JsonLdBlock(
                raw=raw,
                parsed=obj,
                schema_type=schema_type,
                has_valid_context=str(context).rstrip("/") in {c.rstrip("/") for c in VALID_SCHEMA_CONTEXTS},
                error=None,
            ))

    return blocks


def extract_microdata(html: str) -> list[MicrodataItem]:
    """Detect Microdata itemscope/itemprop usage in HTML.

    Args:
        html: Raw HTML content.

    Returns:
        List of MicrodataItem found.
    """
    if not html or not html.strip():
        return []

    soup = BeautifulSoup(html, "html.parser")
    items: list[MicrodataItem] = []

    for tag in soup.find_all(attrs={"itemscope": True}):
        # BeautifulSoup typing returns Union — narrow to str for our schema
        raw_type = tag.get("itemtype")
        item_type: str | None = raw_type if isinstance(raw_type, str) else None
        props: list[str] = []
        for child in tag.find_all(attrs={"itemprop": True}):
            prop = child.get("itemprop")
            if isinstance(prop, str):
                props.append(prop)
        items.append(MicrodataItem(item_type=item_type, properties=props))

    return items


def has_rdfa(html: str) -> bool:
    """Check if page uses RDFa attributes (typeof, property, vocab).

    Args:
        html: Raw HTML content.

    Returns:
        True if RDFa attributes are detected.
    """
    if not html or not html.strip():
        return False

    soup = BeautifulSoup(html, "html.parser")
    return bool(
        soup.find(attrs={"typeof": True})
        or soup.find(attrs={"vocab": True})
        or soup.find(attrs={"property": True, "typeof": True})
    )


def _check_ai_properties(schema_type: str, obj: dict[str, Any]) -> list[str]:
    """Return list of missing AI-critical properties for a given schema type."""
    required = AI_CRITICAL_SCHEMAS.get(schema_type, [])
    return [prop for prop in required if prop not in obj]


def analyze_structured_data(summary: StructuredDataSummary) -> tuple[int, list[Issue]]:
    """Score structured data completeness and generate issues.

    Scoring (0–100):
    - Any valid structured data present: +40
    - All JSON-LD blocks parse as valid JSON: +20
    - At least one block has correct schema.org @context: +10
    - AI-critical properties completeness (per detected type): up to +30

    Args:
        summary: Aggregated detection results.

    Returns:
        (score_value, issues)
    """
    issues: list[Issue] = []
    score = 0

    has_any = (
        bool(summary.jsonld_blocks)
        or bool(summary.microdata_items)
        or summary.has_rdfa
    )

    if not has_any:
        issues.append(Issue(
            severity=Severity.HIGH,
            category=Category.STRUCTURED_DATA,
            title="No structured data detected",
            description=(
                "No JSON-LD, Microdata, or RDFa markup was found on this page. "
                "Structured data is the primary way AI search engines understand "
                "page context, type, and content relationships."
            ),
            recommendation=(
                "Add JSON-LD structured data relevant to your content type. "
                "For articles: Article or BlogPosting schema. "
                "For businesses: Organization or LocalBusiness. "
                "For FAQs: FAQPage schema."
            ),
        ))
        return 0, issues

    # +40: has any structured data
    score += 40

    # Analyze JSON-LD blocks
    valid_blocks = [b for b in summary.jsonld_blocks if b.parsed is not None]
    invalid_blocks = [b for b in summary.jsonld_blocks if b.parsed is None]

    # +20: all JSON-LD is valid (partial credit if some valid)
    if summary.jsonld_blocks:
        if not invalid_blocks:
            score += 20
        elif valid_blocks:
            score += 10  # partial
    elif summary.microdata_items or summary.has_rdfa:
        score += 10  # non-JSON-LD format, give partial credit

    for block in invalid_blocks:
        issues.append(Issue(
            severity=Severity.HIGH,
            category=Category.STRUCTURED_DATA,
            title="Invalid JSON in JSON-LD block",
            description=(
                f"A <script type=\"application/ld+json\"> block contains invalid JSON "
                f"and will be ignored by search engines and AI crawlers. "
                f"Parse error: {block.error}"
            ),
            recommendation=(
                "Validate your JSON-LD using the Google Rich Results Test or "
                "schema.org validator, then fix the syntax error."
            ),
            details={"error": block.error},
        ))

    # +10: valid schema.org @context
    has_valid_context = any(b.has_valid_context for b in valid_blocks)
    if has_valid_context:
        score += 10
    elif valid_blocks:
        # Parsed OK but wrong/missing context
        issues.append(Issue(
            severity=Severity.MEDIUM,
            category=Category.STRUCTURED_DATA,
            title="Missing or incorrect schema.org @context",
            description=(
                "JSON-LD blocks are present but lack a valid schema.org @context. "
                'Without @context, structured data cannot be interpreted by search engines.'
            ),
            recommendation=(
                'Add "@context": "https://schema.org" to each JSON-LD block.'
            ),
        ))

    # +30: AI-critical property completeness
    if valid_blocks:
        property_scores: list[float] = []

        for block in valid_blocks:
            if not block.has_valid_context or not block.schema_type:
                continue

            missing = _check_ai_properties(block.schema_type, block.parsed or {})
            required = AI_CRITICAL_SCHEMAS.get(block.schema_type, [])

            if not required:
                # Unknown type — neutral, no penalty
                property_scores.append(1.0)
                continue

            completeness = 1.0 - (len(missing) / len(required))
            property_scores.append(completeness)

            if missing:
                severity = Severity.HIGH if completeness < 0.5 else Severity.MEDIUM
                issues.append(Issue(
                    severity=severity,
                    category=Category.STRUCTURED_DATA,
                    title=f"{block.schema_type}: missing AI-critical properties",
                    description=(
                        f"The {block.schema_type} schema is missing properties that AI "
                        f"search engines use to understand and cite this content: "
                        f"{', '.join(missing)}."
                    ),
                    recommendation=(
                        f"Add the following properties to your {block.schema_type} schema: "
                        f"{', '.join(missing)}."
                    ),
                    details={
                        "schema_type": block.schema_type,
                        "missing_properties": missing,
                        "present_properties": [p for p in (AI_CRITICAL_SCHEMAS.get(block.schema_type) or []) if p not in missing],
                    },
                ))

        if property_scores:
            avg_completeness = sum(property_scores) / len(property_scores)
            score += round(avg_completeness * 30)

    # Informational: report what was found
    found_types = [b.schema_type for b in valid_blocks if b.schema_type]
    if found_types:
        issues.append(Issue(
            severity=Severity.INFO,
            category=Category.STRUCTURED_DATA,
            title=f"Detected schema types: {', '.join(set(found_types))}",
            description=(
                f"Found {len(valid_blocks)} valid JSON-LD block(s) with schema type(s): "
                f"{', '.join(set(found_types))}."
            ),
            recommendation="Review completeness of AI-critical properties for each schema type.",
            details={"types": list(set(found_types)), "block_count": len(valid_blocks)},
        ))

    if summary.microdata_items:
        issues.append(Issue(
            severity=Severity.INFO,
            category=Category.STRUCTURED_DATA,
            title=f"Microdata detected: {len(summary.microdata_items)} item(s)",
            description=(
                "Microdata (itemscope/itemprop attributes) was detected. "
                "While valid, JSON-LD is the preferred format for AI search engines."
            ),
            recommendation=(
                "Consider migrating Microdata to JSON-LD for better compatibility "
                "with AI search engines and easier maintenance."
            ),
            details={"item_count": len(summary.microdata_items)},
        ))

    if summary.has_rdfa:
        issues.append(Issue(
            severity=Severity.INFO,
            category=Category.STRUCTURED_DATA,
            title="RDFa markup detected",
            description="RDFa attributes (typeof, vocab, property) were detected on the page.",
            recommendation=(
                "RDFa is valid but less commonly supported by AI engines than JSON-LD. "
                "Consider supplementing with JSON-LD."
            ),
        ))

    return max(0, min(100, score)), issues


class StructuredDataAnalyzer(AnalyzerBase):
    """Analyze structured data markup for AI search readiness."""

    async def analyze(self, url: str, html: str, headers: dict[str, str]) -> Score:
        """Analyze structured data on the page.

        Checks:
        - JSON-LD blocks: presence, validity, schema.org compliance
        - Microdata: itemscope/itemprop attributes
        - RDFa: typeof/vocab/property attributes
        - Missing critical schemas for AI citation
        - Property completeness for AI-critical schema types
        """
        summary = StructuredDataSummary(
            jsonld_blocks=extract_jsonld_blocks(html),
            microdata_items=extract_microdata(html),
            has_rdfa=has_rdfa(html),
        )

        score_value, issues = analyze_structured_data(summary)

        return Score(
            category=Category.STRUCTURED_DATA,
            value=score_value,
            issues=issues,
        )
