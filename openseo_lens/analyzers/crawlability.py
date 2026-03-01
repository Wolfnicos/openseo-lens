"""AI crawlability analyzer — robots.txt directives, meta robots, X-Robots-Tag.

Analyzes how AI-powered search engines can access and crawl your content.
Checks robots.txt for AI-specific bot directives (12 known bots), meta robots
tags, and X-Robots-Tag HTTP headers. Produces a weighted accessibility score.

Follows RFC 9309 for robots.txt parsing:
- Most specific User-Agent match takes precedence over wildcard
- Longest path match wins within a group
- No matching rule defaults to allowed
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from openseo_lens.analyzers import AnalyzerBase
from openseo_lens.models import Category, Issue, Score, Severity

# Known AI crawler user agents and their market-importance weights (total = 100)
AI_BOTS: dict[str, tuple[str, int]] = {
    "GPTBot": ("OpenAI (ChatGPT training data)", 12),
    "ChatGPT-User": ("OpenAI (ChatGPT live browsing)", 10),
    "Google-Extended": ("Google (Gemini training data)", 12),
    "GoogleOther": ("Google (AI Overviews, other AI)", 10),
    "CCBot": ("Common Crawl (used by many AI models)", 10),
    "anthropic-ai": ("Anthropic (Claude training data)", 8),
    "ClaudeBot": ("Anthropic (Claude web search)", 8),
    "PerplexityBot": ("Perplexity AI", 8),
    "Bytespider": ("ByteDance (TikTok AI)", 5),
    "Amazonbot": ("Amazon (Alexa, AI services)", 5),
    "meta-externalagent": ("Meta (Facebook AI, LLaMA)", 7),
    "cohere-ai": ("Cohere", 5),
}

# Bots whose blocking is HIGH severity (major AI search providers)
HIGH_IMPACT_BOTS = {"GPTBot", "ChatGPT-User", "Google-Extended", "GoogleOther"}


@dataclass
class RobotsRule:
    """A single Allow or Disallow rule."""

    path: str
    allow: bool  # True = Allow, False = Disallow


@dataclass
class RobotsGroup:
    """A User-Agent group in robots.txt."""

    user_agents: list[str] = field(default_factory=list)
    rules: list[RobotsRule] = field(default_factory=list)
    crawl_delay: float | None = None


@dataclass
class BotDirective:
    """Result of checking a single bot's access."""

    bot_name: str
    operator: str
    allowed: bool
    reason: str  # "explicit allow", "explicit block", "wildcard block", etc.
    matching_rule: str | None = None


def parse_robots_txt(content: str) -> list[RobotsGroup]:
    """Parse robots.txt content into structured groups per RFC 9309.

    Args:
        content: Raw robots.txt file content.

    Returns:
        List of RobotsGroup, each with user-agents and their rules.
    """
    groups: list[RobotsGroup] = []
    current_group: RobotsGroup | None = None

    for raw_line in content.splitlines():
        # Strip comments
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue

        # Parse directive: value
        if ":" not in line:
            continue

        directive, _, value = line.partition(":")
        directive = directive.strip().lower()
        value = value.strip()

        if directive == "user-agent":
            # If previous group has no rules yet, add to it (multi-UA group)
            if current_group is not None and not current_group.rules:
                current_group.user_agents.append(value)
            else:
                current_group = RobotsGroup(user_agents=[value])
                groups.append(current_group)

        elif directive == "disallow" and current_group is not None:
            if value:  # Empty Disallow means allow all
                current_group.rules.append(RobotsRule(path=value, allow=False))

        elif directive == "allow" and current_group is not None:
            current_group.rules.append(RobotsRule(path=value, allow=True))

        elif directive == "crawl-delay" and current_group is not None:
            with contextlib.suppress(ValueError):
                current_group.crawl_delay = float(value)

    return groups


def check_bot_access(
    groups: list[RobotsGroup],
    bot_name: str,
    path: str = "/",
) -> BotDirective:
    """Check if a specific bot can access a path based on robots.txt rules.

    Priority per RFC 9309:
    1. Most specific User-Agent match (exact bot name) takes precedence
    2. Falls back to wildcard (*) group
    3. No matching group = allowed by default

    Within a group, the longest matching path rule wins.

    Args:
        groups: Parsed robots.txt groups.
        bot_name: The bot user-agent to check.
        path: URL path to check access for.

    Returns:
        BotDirective with access result and reasoning.
    """
    operator = AI_BOTS.get(bot_name, (bot_name, 0))[0]

    # Find the most specific matching group
    specific_group: RobotsGroup | None = None
    wildcard_group: RobotsGroup | None = None

    bot_lower = bot_name.lower()
    for group in groups:
        for ua in group.user_agents:
            ua_lower = ua.strip().lower()
            if ua_lower == bot_lower:
                specific_group = group
            elif ua_lower == "*":
                wildcard_group = group

    # Use specific group if found, otherwise wildcard
    matched_group = specific_group or wildcard_group

    if matched_group is None:
        return BotDirective(
            bot_name=bot_name,
            operator=operator,
            allowed=True,
            reason="no matching rule (default allow)",
        )

    group_type = "specific" if specific_group else "wildcard"

    # Find the longest matching rule
    best_rule: RobotsRule | None = None
    best_length = -1

    for rule in matched_group.rules:
        if path.startswith(rule.path) or rule.path == "/" or rule.path == "":
            match_len = len(rule.path)
            if match_len > best_length:
                best_length = match_len
                best_rule = rule

    if best_rule is None:
        # Group exists but no rules match this path
        return BotDirective(
            bot_name=bot_name,
            operator=operator,
            allowed=True,
            reason=f"{group_type} group, no matching path rule (default allow)",
        )

    action = "allow" if best_rule.allow else "block"
    return BotDirective(
        bot_name=bot_name,
        operator=operator,
        allowed=best_rule.allow,
        reason=f"{group_type} {action} (path: {best_rule.path})",
        matching_rule=f"{'Allow' if best_rule.allow else 'Disallow'}: {best_rule.path}",
    )


def check_meta_robots(html: str) -> list[Issue]:
    """Parse HTML for meta robots directives relevant to AI crawling.

    Checks for:
    - <meta name="robots" content="...">
    - <meta name="googlebot" content="...">
    - <meta name="robots" content="noai">
    - <meta name="robots" content="noimageai">

    Args:
        html: Raw HTML content.

    Returns:
        List of Issues found.
    """
    if not html or not html.strip():
        return []

    issues: list[Issue] = []
    soup = BeautifulSoup(html, "html.parser")

    # Find all meta robots-like tags
    meta_names = ["robots", "googlebot", "googlebot-news", "bingbot"]
    for name in meta_names:
        target = name  # bind loop var for lambda
        tag = soup.find("meta", attrs={"name": lambda v, t=target: v and v.lower() == t})
        if tag is None:
            continue

        content = (tag.get("content") or "").lower()  # type: ignore[union-attr]
        directives = [d.strip() for d in content.split(",")]

        if "noindex" in directives:
            issues.append(Issue(
                severity=Severity.HIGH,
                category=Category.CRAWLABILITY,
                title=f"meta {name}: noindex directive found",
                description=(
                    f'The <meta name="{name}"> tag contains "noindex", which tells '
                    f"search engines not to index this page. AI search engines that "
                    f"respect this directive will skip this content entirely."
                ),
                recommendation=(
                    f'Remove "noindex" from the <meta name="{name}"> tag if you want '
                    f"this page to appear in AI search results."
                ),
                details={"meta_name": name, "content": content},
            ))

        if "nofollow" in directives:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category=Category.CRAWLABILITY,
                title=f"meta {name}: nofollow directive found",
                description=(
                    f'The <meta name="{name}"> tag contains "nofollow", which tells '
                    f"crawlers not to follow links on this page. This limits content "
                    f"discovery by AI search engines."
                ),
                recommendation=(
                    'Consider removing "nofollow" if you want AI crawlers to '
                    "discover linked content from this page."
                ),
                details={"meta_name": name, "content": content},
            ))

        if "noai" in directives or "noimageai" in directives:
            directive_name = "noai" if "noai" in directives else "noimageai"
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category=Category.CRAWLABILITY,
                title=f"meta {name}: {directive_name} directive found",
                description=(
                    f'The <meta name="{name}"> tag contains "{directive_name}", '
                    f"which signals that content should not be used for AI training "
                    f"or AI-generated responses."
                ),
                recommendation=(
                    "This is a valid choice if you want to opt out of AI usage. "
                    "Be aware that not all AI engines respect this directive yet."
                ),
                details={"meta_name": name, "content": content},
            ))

    return issues


def check_x_robots_tag(headers: dict[str, str]) -> list[Issue]:
    """Check X-Robots-Tag HTTP header for AI-relevant directives.

    Args:
        headers: HTTP response headers (case-insensitive lookup).

    Returns:
        List of Issues found.
    """
    issues: list[Issue] = []

    # Case-insensitive header lookup
    header_value = None
    for key, value in headers.items():
        if key.lower() == "x-robots-tag":
            header_value = value
            break

    if header_value is None:
        return issues

    directives = [d.strip().lower() for d in header_value.split(",")]

    if "noindex" in directives:
        issues.append(Issue(
            severity=Severity.HIGH,
            category=Category.CRAWLABILITY,
            title="X-Robots-Tag: noindex header found",
            description=(
                "The X-Robots-Tag HTTP header contains 'noindex', which tells "
                "search engines and AI crawlers not to index this page."
            ),
            recommendation=(
                "Remove 'noindex' from the X-Robots-Tag header if you want "
                "this page to appear in AI search results."
            ),
            details={"header_value": header_value},
        ))

    if "noai" in directives or "noimageai" in directives:
        directive_name = "noai" if "noai" in directives else "noimageai"
        issues.append(Issue(
            severity=Severity.MEDIUM,
            category=Category.CRAWLABILITY,
            title=f"X-Robots-Tag: {directive_name} header found",
            description=(
                f"The X-Robots-Tag HTTP header contains '{directive_name}', "
                f"signaling that content should not be used for AI purposes."
            ),
            recommendation=(
                "This is a valid opt-out signal. Be aware that enforcement "
                "varies across AI providers."
            ),
            details={"header_value": header_value},
        ))

    return issues


class CrawlabilityAnalyzer(AnalyzerBase):
    """Analyze AI crawlability: robots.txt, meta robots, X-Robots-Tag."""

    async def analyze(self, url: str, html: str, headers: dict[str, str]) -> Score:
        """Analyze crawlability for AI search engines.

        Fetches robots.txt, parses it for 12 AI bot directives, checks
        meta robots tags in HTML, and inspects X-Robots-Tag headers.
        Returns a weighted score (0-100) reflecting overall AI accessibility.
        """
        issues: list[Issue] = []

        # 1. Fetch and parse robots.txt
        robots_content = await self._fetch_robots_txt(url)
        if robots_content is not None:
            groups = parse_robots_txt(robots_content)
        else:
            groups = []
            issues.append(Issue(
                severity=Severity.LOW,
                category=Category.CRAWLABILITY,
                title="robots.txt not found or inaccessible",
                description=(
                    "Could not fetch robots.txt for this site. Without robots.txt, "
                    "all AI crawlers assume they have full access (which is good for "
                    "visibility, but you have no control over AI training usage)."
                ),
                recommendation=(
                    "Consider adding a robots.txt file to explicitly declare which "
                    "AI bots can access your content."
                ),
            ))

        # 2. Check each AI bot's access
        bot_results: dict[str, BotDirective] = {}
        allowed_weight = 0
        total_weight = 0

        for bot_name, (operator, weight) in AI_BOTS.items():
            total_weight += weight
            directive = check_bot_access(groups, bot_name)
            bot_results[bot_name] = directive

            if directive.allowed:
                allowed_weight += weight
            else:
                severity = (
                    Severity.HIGH if bot_name in HIGH_IMPACT_BOTS else Severity.MEDIUM
                )
                issues.append(Issue(
                    severity=severity,
                    category=Category.CRAWLABILITY,
                    title=f"{bot_name} blocked — {operator}",
                    description=(
                        f"The AI crawler {bot_name} ({operator}) is blocked "
                        f"by robots.txt ({directive.reason}). Content on this site "
                        f"will not appear in {operator.split('(')[0].strip()} results."
                    ),
                    recommendation=(
                        f"To allow {bot_name}, add or modify your robots.txt:\n"
                        f"User-agent: {bot_name}\nAllow: /"
                    ),
                    details={
                        "bot": bot_name,
                        "operator": operator,
                        "reason": directive.reason,
                        "matching_rule": directive.matching_rule,
                    },
                ))

        # 3. Detect conflicts (specific allow contradicts wildcard block)
        wildcard_directive = check_bot_access(groups, "*")
        if not wildcard_directive.allowed:
            # Wildcard blocks everything — check if any bot has specific allow
            specifically_allowed = [
                name for name, d in bot_results.items()
                if d.allowed and d.reason.startswith("specific")
            ]
            if specifically_allowed:
                issues.append(Issue(
                    severity=Severity.MEDIUM,
                    category=Category.CRAWLABILITY,
                    title="Conflicting directives: wildcard block with specific allows",
                    description=(
                        f"robots.txt blocks all bots via wildcard (*) but specifically "
                        f"allows: {', '.join(specifically_allowed)}. While this is valid "
                        f"per RFC 9309, it may cause confusion with crawlers that don't "
                        f"fully implement specificity rules."
                    ),
                    recommendation=(
                        "This configuration is technically correct. Ensure it reflects "
                        "your intent: block all AI bots except the ones listed."
                    ),
                    details={"specifically_allowed": specifically_allowed},
                ))

        # 4. Check meta robots tags
        meta_issues = check_meta_robots(html)
        issues.extend(meta_issues)

        # 5. Check X-Robots-Tag headers
        xrt_issues = check_x_robots_tag(headers)
        issues.extend(xrt_issues)

        # 6. Calculate score
        # Base: percentage of bot weight that is allowed
        score_value = round((allowed_weight / total_weight) * 100) if total_weight else 100

        # Penalties for meta/header restrictions
        for issue in meta_issues:
            if issue.severity == Severity.HIGH:
                score_value -= 10
            elif issue.severity == Severity.MEDIUM:
                score_value -= 5

        for issue in xrt_issues:
            if issue.severity == Severity.HIGH:
                score_value -= 5
            elif issue.severity == Severity.MEDIUM:
                score_value -= 3

        score_value = max(0, min(100, score_value))

        return Score(
            category=Category.CRAWLABILITY,
            value=score_value,
            issues=issues,
        )

    @staticmethod
    async def _fetch_robots_txt(url: str) -> str | None:
        """Fetch robots.txt from the site root.

        Args:
            url: Any URL on the site.

        Returns:
            robots.txt content or None if not found/error.
        """
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=5.0,
            ) as client:
                response = await client.get(robots_url)
                if response.status_code == 200:
                    return response.text
                return None
        except (httpx.HTTPError, httpx.TimeoutException):
            return None
