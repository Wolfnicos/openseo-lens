"""Tests for the TDM-Reservation compliance analyzer."""

import pytest

from openseo_lens.analyzers.tdm import TdmAnalyzer
from openseo_lens.models import Category


@pytest.fixture
def analyzer() -> TdmAnalyzer:
    return TdmAnalyzer()


@pytest.mark.asyncio
async def test_analyzer_returns_score(analyzer: TdmAnalyzer) -> None:
    """Analyzer should return a score with the correct category."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="<html><body></body></html>",
        headers={},
    )
    assert score.category == Category.TDM
    assert 0 <= score.value <= 100


@pytest.mark.asyncio
async def test_analyzer_handles_tdm_header(analyzer: TdmAnalyzer) -> None:
    """Analyzer should process TDM-Reservation header."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="<html><body></body></html>",
        headers={"TDM-Reservation": "1"},
    )
    assert score.category == Category.TDM


@pytest.mark.asyncio
async def test_analyzer_handles_no_tdm_header(analyzer: TdmAnalyzer) -> None:
    """Analyzer should handle missing TDM-Reservation header."""
    score = await analyzer.analyze(
        url="https://example.com",
        html="<html><body></body></html>",
        headers={},
    )
    assert score.category == Category.TDM
