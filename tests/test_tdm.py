"""Comprehensive tests for the TDM-Reservation compliance analyzer."""

from unittest.mock import AsyncMock, patch

import pytest

from openseo_lens.analyzers.tdm import (
    TdmAnalyzer,
    TdmPolicy,
    TdmSignal,
    check_tdm_http_header,
    check_tdm_meta_tags,
    detect_conflicts,
)
from openseo_lens.models import Category, Severity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer() -> TdmAnalyzer:
    return TdmAnalyzer()


# ---------------------------------------------------------------------------
# HTTP Header Checking
# ---------------------------------------------------------------------------

class TestCheckTdmHttpHeader:
    def test_no_header(self) -> None:
        assert check_tdm_http_header({}) is None

    def test_reserved(self) -> None:
        signal = check_tdm_http_header({"TDM-Reservation": "1"})
        assert signal is not None
        assert signal.policy == TdmPolicy.RESERVED
        assert signal.source == "http_header"

    def test_not_reserved(self) -> None:
        signal = check_tdm_http_header({"TDM-Reservation": "0"})
        assert signal is not None
        assert signal.policy == TdmPolicy.NOT_RESERVED

    def test_invalid_value(self) -> None:
        signal = check_tdm_http_header({"TDM-Reservation": "yes"})
        assert signal is not None
        assert signal.policy == TdmPolicy.NOT_DECLARED
        assert signal.raw_value == "yes"

    def test_case_insensitive_header_name(self) -> None:
        signal = check_tdm_http_header({"tdm-reservation": "1"})
        assert signal is not None
        assert signal.policy == TdmPolicy.RESERVED

    def test_whitespace_stripped(self) -> None:
        signal = check_tdm_http_header({"TDM-Reservation": " 1 "})
        assert signal is not None
        assert signal.policy == TdmPolicy.RESERVED

    def test_empty_value(self) -> None:
        signal = check_tdm_http_header({"TDM-Reservation": ""})
        assert signal is not None
        assert signal.policy == TdmPolicy.NOT_DECLARED


# ---------------------------------------------------------------------------
# HTML Meta/Link Tag Checking
# ---------------------------------------------------------------------------

class TestCheckTdmMetaTags:
    def test_empty_html(self) -> None:
        assert check_tdm_meta_tags("") == []

    def test_no_tdm_tags(self) -> None:
        html = "<html><head><title>Test</title></head><body></body></html>"
        assert check_tdm_meta_tags(html) == []

    def test_meta_reserved(self) -> None:
        html = '<html><head><meta name="tdm-reservation" content="1"></head></html>'
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 1
        assert signals[0].policy == TdmPolicy.RESERVED
        assert signals[0].source == "meta_tag"

    def test_meta_not_reserved(self) -> None:
        html = '<html><head><meta name="tdm-reservation" content="0"></head></html>'
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 1
        assert signals[0].policy == TdmPolicy.NOT_RESERVED

    def test_meta_invalid_value(self) -> None:
        html = '<html><head><meta name="tdm-reservation" content="true"></head></html>'
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 1
        assert signals[0].policy == TdmPolicy.NOT_DECLARED

    def test_meta_case_insensitive(self) -> None:
        html = '<html><head><meta name="TDM-Reservation" content="1"></head></html>'
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 1
        assert signals[0].policy == TdmPolicy.RESERVED

    def test_link_tdm_policy(self) -> None:
        html = '<html><head><link rel="tdm-policy" href="/tdmrep.json"></head></html>'
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 1
        assert signals[0].source == "link_tag"
        assert signals[0].policy == TdmPolicy.RESERVED
        assert signals[0].raw_value == "/tdmrep.json"

    def test_both_meta_and_link(self) -> None:
        html = (
            "<html><head>"
            '<meta name="tdm-reservation" content="1">'
            '<link rel="tdm-policy" href="/tdmrep.json">'
            "</head></html>"
        )
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 2

    def test_link_without_href_ignored(self) -> None:
        html = '<html><head><link rel="tdm-policy"></head></html>'
        signals = check_tdm_meta_tags(html)
        assert len(signals) == 0


# ---------------------------------------------------------------------------
# Conflict Detection
# ---------------------------------------------------------------------------

class TestDetectConflicts:
    def test_no_signals(self) -> None:
        assert detect_conflicts([]) == []

    def test_consistent_reserved(self) -> None:
        signals = [
            TdmSignal("http_header", TdmPolicy.RESERVED, "1"),
            TdmSignal("meta_tag", TdmPolicy.RESERVED, "1"),
        ]
        assert detect_conflicts(signals) == []

    def test_consistent_not_reserved(self) -> None:
        signals = [
            TdmSignal("http_header", TdmPolicy.NOT_RESERVED, "0"),
            TdmSignal("meta_tag", TdmPolicy.NOT_RESERVED, "0"),
        ]
        assert detect_conflicts(signals) == []

    def test_conflict_detected(self) -> None:
        signals = [
            TdmSignal("http_header", TdmPolicy.RESERVED, "1"),
            TdmSignal("meta_tag", TdmPolicy.NOT_RESERVED, "0"),
        ]
        issues = detect_conflicts(signals)
        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH
        assert "Conflicting" in issues[0].title

    def test_not_declared_ignored_in_conflict_check(self) -> None:
        signals = [
            TdmSignal("http_header", TdmPolicy.RESERVED, "1"),
            TdmSignal("meta_tag", TdmPolicy.NOT_DECLARED, "invalid"),
        ]
        assert detect_conflicts(signals) == []

    def test_conflict_details(self) -> None:
        signals = [
            TdmSignal("http_header", TdmPolicy.RESERVED, "1"),
            TdmSignal("meta_tag", TdmPolicy.NOT_RESERVED, "0"),
        ]
        issues = detect_conflicts(signals)
        assert "http_header" in issues[0].details["reserved_by"]
        assert "meta_tag" in issues[0].details["allowed_by"]


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestTdmScoring:
    @pytest.mark.asyncio
    async def test_no_declaration_scores_30(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert score.value == 30

    @pytest.mark.asyncio
    async def test_single_channel_scores_70(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", "<html></html>",
                {"TDM-Reservation": "1"},
            )
        assert score.value == 70

    @pytest.mark.asyncio
    async def test_two_channels_scores_90(self, analyzer: TdmAnalyzer) -> None:
        html = '<html><head><meta name="tdm-reservation" content="1"></head></html>'
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", html,
                {"TDM-Reservation": "1"},
            )
        assert score.value == 90

    @pytest.mark.asyncio
    async def test_three_channels_scores_100(self, analyzer: TdmAnalyzer) -> None:
        html = '<html><head><meta name="tdm-reservation" content="1"></head></html>'
        tdmrep = TdmSignal("tdmrep_json", TdmPolicy.RESERVED, "https://example.com/tdmrep.json")
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=tdmrep):
            score = await analyzer.analyze(
                "https://example.com", html,
                {"TDM-Reservation": "1"},
            )
        assert score.value == 100

    @pytest.mark.asyncio
    async def test_invalid_value_penalized(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", "<html></html>",
                {"TDM-Reservation": "banana"},
            )
        assert score.value == 5  # 20 (only invalid) - 15 (penalty) = 5

    @pytest.mark.asyncio
    async def test_conflict_penalized(self, analyzer: TdmAnalyzer) -> None:
        html = '<html><head><meta name="tdm-reservation" content="0"></head></html>'
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", html,
                {"TDM-Reservation": "1"},
            )
        # 2 valid channels = 90, minus 30 for conflict = 60
        assert score.value == 60


# ---------------------------------------------------------------------------
# Full Analyzer Integration
# ---------------------------------------------------------------------------

class TestTdmAnalyzer:
    @pytest.mark.asyncio
    async def test_returns_correct_category(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert score.category == Category.TDM

    @pytest.mark.asyncio
    async def test_score_in_valid_range(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert 0 <= score.value <= 100

    @pytest.mark.asyncio
    async def test_no_policy_generates_issue(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        titles = [i.title for i in score.issues]
        assert any("No TDM policy" in t for t in titles)

    @pytest.mark.asyncio
    async def test_valid_policy_generates_info(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", "<html></html>",
                {"TDM-Reservation": "1"},
            )
        info_issues = [i for i in score.issues if i.severity == Severity.INFO]
        assert len(info_issues) == 1
        assert "reserved" in info_issues[0].title.lower()

    @pytest.mark.asyncio
    async def test_opt_in_policy_info(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", "<html></html>",
                {"TDM-Reservation": "0"},
            )
        info_issues = [i for i in score.issues if i.severity == Severity.INFO]
        assert len(info_issues) == 1
        assert "not reserved" in info_issues[0].title.lower()

    @pytest.mark.asyncio
    async def test_invalid_header_generates_issue(self, analyzer: TdmAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze(
                "https://example.com", "<html></html>",
                {"TDM-Reservation": "maybe"},
            )
        medium_issues = [i for i in score.issues if i.severity == Severity.MEDIUM]
        assert any("Invalid TDM-Reservation header" in i.title for i in medium_issues)

    @pytest.mark.asyncio
    async def test_all_channels_consistent(self, analyzer: TdmAnalyzer) -> None:
        """Full compliance: header + meta + tdmrep.json, all consistent."""
        html = (
            "<html><head>"
            '<meta name="tdm-reservation" content="1">'
            '<link rel="tdm-policy" href="/tdmrep.json">'
            "</head></html>"
        )
        tdmrep = TdmSignal("tdmrep_json", TdmPolicy.RESERVED, "https://example.com/tdmrep.json")
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=tdmrep):
            score = await analyzer.analyze(
                "https://example.com", html,
                {"TDM-Reservation": "1"},
            )
        assert score.value == 100
        conflict_issues = [i for i in score.issues if "Conflicting" in i.title]
        assert len(conflict_issues) == 0

    @pytest.mark.asyncio
    async def test_real_world_no_tdm(self, analyzer: TdmAnalyzer) -> None:
        """Typical website with no TDM declarations at all."""
        html = (
            "<!DOCTYPE html><html><head>"
            "<title>My Business</title>"
            '<meta name="description" content="We sell things">'
            "</head><body><h1>Welcome</h1></body></html>"
        )
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://mybusiness.eu", html, {})
        assert score.value == 30
        assert any("No TDM policy" in i.title for i in score.issues)

    @pytest.mark.asyncio
    async def test_eu_compliant_site(self, analyzer: TdmAnalyzer) -> None:
        """EU-compliant site with header and meta tag, rights reserved."""
        html = '<html><head><meta name="tdm-reservation" content="1"></head></html>'
        headers = {"TDM-Reservation": "1", "Content-Type": "text/html"}
        with patch.object(analyzer, "_fetch_tdmrep", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://publisher.eu", html, headers)
        assert score.value == 90
        info = [i for i in score.issues if i.severity == Severity.INFO]
        assert len(info) == 1
        assert "reserved" in info[0].title.lower()
