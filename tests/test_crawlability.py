"""Comprehensive tests for the AI crawlability analyzer."""

from unittest.mock import AsyncMock, patch

import pytest

from openseo_lens.analyzers.crawlability import (
    AI_BOTS,
    BotDirective,
    CrawlabilityAnalyzer,
    check_bot_access,
    check_meta_robots,
    check_x_robots_tag,
    parse_robots_txt,
)
from openseo_lens.models import Category, Severity


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analyzer() -> CrawlabilityAnalyzer:
    return CrawlabilityAnalyzer()


# ---------------------------------------------------------------------------
# AI Bot Registry
# ---------------------------------------------------------------------------

class TestAIBotRegistry:
    def test_contains_12_bots(self) -> None:
        assert len(AI_BOTS) == 12

    def test_major_bots_present(self) -> None:
        for bot in [
            "GPTBot", "ChatGPT-User", "Google-Extended", "GoogleOther",
            "CCBot", "anthropic-ai", "ClaudeBot", "PerplexityBot",
            "Bytespider", "Amazonbot", "meta-externalagent", "cohere-ai",
        ]:
            assert bot in AI_BOTS, f"{bot} missing from registry"

    def test_each_bot_has_operator_and_weight(self) -> None:
        for bot_name, (operator, weight) in AI_BOTS.items():
            assert isinstance(operator, str) and operator
            assert isinstance(weight, int) and weight > 0

    def test_weights_sum_to_100(self) -> None:
        total = sum(weight for _, weight in AI_BOTS.values())
        assert total == 100


# ---------------------------------------------------------------------------
# robots.txt Parsing
# ---------------------------------------------------------------------------

class TestParseRobotsTxt:
    def test_empty_content(self) -> None:
        groups = parse_robots_txt("")
        assert groups == []

    def test_comments_only(self) -> None:
        content = "# This is a comment\n# Another comment\n"
        groups = parse_robots_txt(content)
        assert groups == []

    def test_single_wildcard_disallow_all(self) -> None:
        content = "User-agent: *\nDisallow: /\n"
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert groups[0].user_agents == ["*"]
        assert len(groups[0].rules) == 1
        assert groups[0].rules[0].path == "/"
        assert groups[0].rules[0].allow is False

    def test_single_bot_blocked(self) -> None:
        content = "User-agent: GPTBot\nDisallow: /\n"
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert groups[0].user_agents == ["GPTBot"]
        assert groups[0].rules[0].allow is False

    def test_multiple_groups(self) -> None:
        content = (
            "User-agent: GPTBot\n"
            "Disallow: /\n"
            "\n"
            "User-agent: Google-Extended\n"
            "Allow: /\n"
        )
        groups = parse_robots_txt(content)
        assert len(groups) == 2
        assert groups[0].user_agents == ["GPTBot"]
        assert groups[1].user_agents == ["Google-Extended"]

    def test_multi_user_agent_group(self) -> None:
        content = (
            "User-agent: GPTBot\n"
            "User-agent: ChatGPT-User\n"
            "Disallow: /\n"
        )
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert "GPTBot" in groups[0].user_agents
        assert "ChatGPT-User" in groups[0].user_agents

    def test_allow_and_disallow_in_same_group(self) -> None:
        content = (
            "User-agent: *\n"
            "Disallow: /private/\n"
            "Allow: /private/public-page\n"
        )
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert len(groups[0].rules) == 2

    def test_crawl_delay(self) -> None:
        content = "User-agent: *\nCrawl-delay: 10\nDisallow: /tmp/\n"
        groups = parse_robots_txt(content)
        assert groups[0].crawl_delay == 10.0

    def test_invalid_crawl_delay(self) -> None:
        content = "User-agent: *\nCrawl-delay: abc\nDisallow: /\n"
        groups = parse_robots_txt(content)
        assert groups[0].crawl_delay is None

    def test_inline_comments_stripped(self) -> None:
        content = "User-agent: GPTBot # OpenAI bot\nDisallow: / # block all\n"
        groups = parse_robots_txt(content)
        assert groups[0].user_agents == ["GPTBot"]
        assert groups[0].rules[0].path == "/"

    def test_empty_disallow_is_ignored(self) -> None:
        """Empty Disallow means allow all (RFC 9309)."""
        content = "User-agent: *\nDisallow:\n"
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert len(groups[0].rules) == 0

    def test_malformed_lines_skipped(self) -> None:
        content = "This is garbage\nUser-agent: GPTBot\nmore garbage\nDisallow: /\n"
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert groups[0].user_agents == ["GPTBot"]

    def test_case_insensitive_directives(self) -> None:
        content = "user-agent: GPTBot\ndisallow: /\n"
        groups = parse_robots_txt(content)
        assert len(groups) == 1
        assert groups[0].user_agents == ["GPTBot"]


# ---------------------------------------------------------------------------
# Bot Access Resolution
# ---------------------------------------------------------------------------

class TestCheckBotAccess:
    def test_no_groups_means_allowed(self) -> None:
        result = check_bot_access([], "GPTBot")
        assert result.allowed is True
        assert "default allow" in result.reason

    def test_explicit_block(self) -> None:
        groups = parse_robots_txt("User-agent: GPTBot\nDisallow: /\n")
        result = check_bot_access(groups, "GPTBot")
        assert result.allowed is False
        assert "specific" in result.reason

    def test_explicit_allow(self) -> None:
        groups = parse_robots_txt("User-agent: GPTBot\nAllow: /\n")
        result = check_bot_access(groups, "GPTBot")
        assert result.allowed is True

    def test_wildcard_block_applies_to_unlisted_bot(self) -> None:
        groups = parse_robots_txt("User-agent: *\nDisallow: /\n")
        result = check_bot_access(groups, "PerplexityBot")
        assert result.allowed is False
        assert "wildcard" in result.reason

    def test_specific_overrides_wildcard(self) -> None:
        """Specific User-Agent match should override wildcard block."""
        content = (
            "User-agent: *\n"
            "Disallow: /\n"
            "\n"
            "User-agent: GPTBot\n"
            "Allow: /\n"
        )
        groups = parse_robots_txt(content)
        result = check_bot_access(groups, "GPTBot")
        assert result.allowed is True
        assert "specific" in result.reason

    def test_specific_block_overrides_wildcard_allow(self) -> None:
        content = (
            "User-agent: *\n"
            "Allow: /\n"
            "\n"
            "User-agent: GPTBot\n"
            "Disallow: /\n"
        )
        groups = parse_robots_txt(content)
        result = check_bot_access(groups, "GPTBot")
        assert result.allowed is False

    def test_longest_path_wins(self) -> None:
        content = (
            "User-agent: *\n"
            "Disallow: /\n"
            "Allow: /public/\n"
        )
        groups = parse_robots_txt(content)
        # /public/ is more specific than /
        result = check_bot_access(groups, "GPTBot", path="/public/page")
        assert result.allowed is True

    def test_case_insensitive_ua_matching(self) -> None:
        groups = parse_robots_txt("User-agent: gptbot\nDisallow: /\n")
        result = check_bot_access(groups, "GPTBot")
        assert result.allowed is False

    def test_unknown_bot_uses_wildcard(self) -> None:
        groups = parse_robots_txt("User-agent: *\nDisallow: /secret/\n")
        result = check_bot_access(groups, "UnknownBot", path="/secret/data")
        assert result.allowed is False

    def test_bot_directive_has_matching_rule(self) -> None:
        groups = parse_robots_txt("User-agent: GPTBot\nDisallow: /\n")
        result = check_bot_access(groups, "GPTBot")
        assert result.matching_rule == "Disallow: /"

    def test_returns_bot_directive_type(self) -> None:
        result = check_bot_access([], "GPTBot")
        assert isinstance(result, BotDirective)


# ---------------------------------------------------------------------------
# Meta Robots Checking
# ---------------------------------------------------------------------------

class TestCheckMetaRobots:
    def test_empty_html(self) -> None:
        assert check_meta_robots("") == []

    def test_no_meta_robots(self) -> None:
        html = "<html><head><title>Test</title></head><body></body></html>"
        assert check_meta_robots(html) == []

    def test_noindex_detected(self) -> None:
        html = '<html><head><meta name="robots" content="noindex"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH
        assert "noindex" in issues[0].title

    def test_nofollow_detected(self) -> None:
        html = '<html><head><meta name="robots" content="nofollow"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 1
        assert issues[0].severity == Severity.MEDIUM
        assert "nofollow" in issues[0].title

    def test_noindex_nofollow_combined(self) -> None:
        html = '<html><head><meta name="robots" content="noindex, nofollow"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 2

    def test_noai_detected(self) -> None:
        html = '<html><head><meta name="robots" content="noai"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 1
        assert "noai" in issues[0].title

    def test_noimageai_detected(self) -> None:
        html = '<html><head><meta name="robots" content="noimageai"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 1
        assert "noimageai" in issues[0].title

    def test_googlebot_specific_meta(self) -> None:
        html = '<html><head><meta name="googlebot" content="noindex"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 1
        assert "googlebot" in issues[0].title

    def test_case_insensitive_meta_name(self) -> None:
        html = '<html><head><meta name="ROBOTS" content="noindex"></head><body></body></html>'
        issues = check_meta_robots(html)
        assert len(issues) == 1

    def test_all_issues_have_correct_category(self) -> None:
        html = '<html><head><meta name="robots" content="noindex, nofollow"></head><body></body></html>'
        issues = check_meta_robots(html)
        for issue in issues:
            assert issue.category == Category.CRAWLABILITY


# ---------------------------------------------------------------------------
# X-Robots-Tag Header Checking
# ---------------------------------------------------------------------------

class TestCheckXRobotsTag:
    def test_no_header(self) -> None:
        assert check_x_robots_tag({}) == []

    def test_noindex_header(self) -> None:
        issues = check_x_robots_tag({"X-Robots-Tag": "noindex"})
        assert len(issues) == 1
        assert issues[0].severity == Severity.HIGH
        assert "noindex" in issues[0].title

    def test_noai_header(self) -> None:
        issues = check_x_robots_tag({"X-Robots-Tag": "noai"})
        assert len(issues) == 1
        assert "noai" in issues[0].title

    def test_case_insensitive_header_name(self) -> None:
        issues = check_x_robots_tag({"x-robots-tag": "noindex"})
        assert len(issues) == 1

    def test_multiple_directives(self) -> None:
        issues = check_x_robots_tag({"X-Robots-Tag": "noindex, noai"})
        assert len(issues) == 2

    def test_irrelevant_directives_ignored(self) -> None:
        issues = check_x_robots_tag({"X-Robots-Tag": "nosnippet"})
        assert len(issues) == 0


# ---------------------------------------------------------------------------
# Full Analyzer Integration
# ---------------------------------------------------------------------------

ROBOTS_ALL_BLOCKED = "User-agent: *\nDisallow: /\n"
ROBOTS_GPTBOT_BLOCKED = "User-agent: GPTBot\nDisallow: /\n"
ROBOTS_ALL_ALLOWED = "User-agent: *\nAllow: /\n"


class TestCrawlabilityAnalyzer:
    @pytest.mark.asyncio
    async def test_returns_correct_category(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_ALLOWED):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert score.category == Category.CRAWLABILITY

    @pytest.mark.asyncio
    async def test_score_in_valid_range(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_BLOCKED):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert 0 <= score.value <= 100

    @pytest.mark.asyncio
    async def test_all_allowed_scores_100(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_ALLOWED):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert score.value == 100

    @pytest.mark.asyncio
    async def test_all_blocked_scores_zero(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_BLOCKED):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert score.value == 0

    @pytest.mark.asyncio
    async def test_single_bot_blocked_reduces_score(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_GPTBOT_BLOCKED):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert 80 <= score.value <= 95  # GPTBot weight is 12, so ~88

    @pytest.mark.asyncio
    async def test_blocked_bot_creates_issue(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_GPTBOT_BLOCKED):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        bot_issues = [i for i in score.issues if "GPTBot" in i.title]
        assert len(bot_issues) == 1
        assert bot_issues[0].severity == Severity.HIGH

    @pytest.mark.asyncio
    async def test_meta_noindex_reduces_score(self, analyzer: CrawlabilityAnalyzer) -> None:
        html = '<html><head><meta name="robots" content="noindex"></head><body></body></html>'
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_ALLOWED):
            score = await analyzer.analyze("https://example.com", html, {})
        assert score.value == 90  # 100 - 10 for noindex

    @pytest.mark.asyncio
    async def test_x_robots_tag_reduces_score(self, analyzer: CrawlabilityAnalyzer) -> None:
        headers = {"X-Robots-Tag": "noindex"}
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_ALLOWED):
            score = await analyzer.analyze("https://example.com", "<html></html>", headers)
        assert score.value == 95  # 100 - 5 for X-Robots-Tag noindex

    @pytest.mark.asyncio
    async def test_robots_txt_not_found(self, analyzer: CrawlabilityAnalyzer) -> None:
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=None):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        assert score.value == 100  # No robots.txt = all allowed
        info_issues = [i for i in score.issues if "robots.txt" in i.title.lower()]
        assert len(info_issues) == 1

    @pytest.mark.asyncio
    async def test_conflict_detection(self, analyzer: CrawlabilityAnalyzer) -> None:
        """Wildcard block + specific allow should trigger conflict warning."""
        robots = (
            "User-agent: *\nDisallow: /\n\n"
            "User-agent: GPTBot\nAllow: /\n"
        )
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=robots):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})
        conflict_issues = [i for i in score.issues if "Conflicting" in i.title]
        assert len(conflict_issues) == 1

    @pytest.mark.asyncio
    async def test_combined_penalties_clamp_to_zero(self, analyzer: CrawlabilityAnalyzer) -> None:
        html = '<html><head><meta name="robots" content="noindex, nofollow"></head><body></body></html>'
        headers = {"X-Robots-Tag": "noindex, noai"}
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=ROBOTS_ALL_BLOCKED):
            score = await analyzer.analyze("https://example.com", html, headers)
        assert score.value == 0  # Can't go below 0

    @pytest.mark.asyncio
    async def test_real_world_robots_txt(self, analyzer: CrawlabilityAnalyzer) -> None:
        """Test with a realistic robots.txt from a news site."""
        robots = (
            "User-agent: *\n"
            "Allow: /\n"
            "Disallow: /admin/\n"
            "Disallow: /private/\n"
            "\n"
            "User-agent: GPTBot\n"
            "Disallow: /\n"
            "\n"
            "User-agent: Google-Extended\n"
            "Disallow: /\n"
            "\n"
            "User-agent: CCBot\n"
            "Disallow: /\n"
        )
        with patch.object(analyzer, "_fetch_robots_txt", new_callable=AsyncMock, return_value=robots):
            score = await analyzer.analyze("https://example.com", "<html></html>", {})

        # GPTBot (12) + Google-Extended (12) + CCBot (10) = 34 blocked
        # So 66 out of 100 allowed
        assert score.value == 66

        blocked = [i for i in score.issues if "blocked" in i.title.lower() or "block" in i.title.lower()]
        assert len(blocked) >= 3
