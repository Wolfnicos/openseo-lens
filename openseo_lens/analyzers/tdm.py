"""TDM-Reservation compliance analyzer — EU DSM Directive Art. 4.

Checks whether a website properly declares Text and Data Mining reservation
rights as required by EU Directive 2019/790 (Digital Single Market Directive).

The DSM Directive Art. 4 allows rightsholders to reserve their TDM rights
via machine-readable means. This analyzer checks three channels:

1. TDM-Reservation HTTP header (W3C TDM Reservation Protocol)
   - Value "1" = rights reserved (opt-out of TDM)
   - Value "0" = rights not reserved (opt-in to TDM)

2. HTML <meta> / <link> tags
   - <meta name="tdm-reservation" content="1">
   - <link rel="tdm-policy" href="..."> pointing to tdmrep.json

3. tdmrep.json policy file
   - Machine-readable TDM policy declaration
   - References: https://www.w3.org/2022/tdmrep/

The score reflects how clearly and consistently a site communicates its
TDM policy. A clear policy (either opt-in or opt-out) scores higher than
no policy or conflicting signals.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from openseo_lens.analyzers import AnalyzerBase
from openseo_lens.models import Category, Issue, Score, Severity


class TdmPolicy(str, Enum):
    """TDM reservation status."""

    RESERVED = "reserved"  # Opt-out: TDM rights reserved
    NOT_RESERVED = "not_reserved"  # Opt-in: TDM allowed
    NOT_DECLARED = "not_declared"  # No policy found


@dataclass
class TdmSignal:
    """A single TDM signal found on the site."""

    source: str  # "http_header", "meta_tag", "link_tag", "tdmrep_json"
    policy: TdmPolicy
    raw_value: str
    details: str = ""


def check_tdm_http_header(headers: dict[str, str]) -> TdmSignal | None:
    """Check TDM-Reservation HTTP header.

    Per the W3C TDM Reservation Protocol:
    - "1" = rights reserved (opt-out)
    - "0" = rights not reserved (opt-in)

    Args:
        headers: HTTP response headers.

    Returns:
        TdmSignal if header found, None otherwise.
    """
    value = None
    for key, val in headers.items():
        if key.lower() == "tdm-reservation":
            value = val.strip()
            break

    if value is None:
        return None

    if value == "1":
        return TdmSignal(
            source="http_header",
            policy=TdmPolicy.RESERVED,
            raw_value=value,
            details="TDM-Reservation: 1 — rights reserved, TDM opt-out declared",
        )
    elif value == "0":
        return TdmSignal(
            source="http_header",
            policy=TdmPolicy.NOT_RESERVED,
            raw_value=value,
            details="TDM-Reservation: 0 — rights not reserved, TDM allowed",
        )
    else:
        return TdmSignal(
            source="http_header",
            policy=TdmPolicy.NOT_DECLARED,
            raw_value=value,
            details=f"TDM-Reservation: {value} — invalid value (must be 0 or 1)",
        )


def check_tdm_meta_tags(html: str) -> list[TdmSignal]:
    """Check HTML for TDM-related meta and link tags.

    Looks for:
    - <meta name="tdm-reservation" content="0|1">
    - <link rel="tdm-policy" href="...">

    Args:
        html: Raw HTML content.

    Returns:
        List of TdmSignal found.
    """
    if not html or not html.strip():
        return []

    signals: list[TdmSignal] = []
    soup = BeautifulSoup(html, "html.parser")

    # Check <meta name="tdm-reservation" content="...">
    meta = soup.find(
        "meta",
        attrs={"name": lambda v: v and v.lower() == "tdm-reservation"},
    )
    if meta is not None:
        content = (meta.get("content") or "").strip()  # type: ignore[union-attr]
        if content == "1":
            signals.append(TdmSignal(
                source="meta_tag",
                policy=TdmPolicy.RESERVED,
                raw_value=content,
                details='<meta name="tdm-reservation" content="1"> — rights reserved',
            ))
        elif content == "0":
            signals.append(TdmSignal(
                source="meta_tag",
                policy=TdmPolicy.NOT_RESERVED,
                raw_value=content,
                details='<meta name="tdm-reservation" content="0"> — TDM allowed',
            ))
        else:
            signals.append(TdmSignal(
                source="meta_tag",
                policy=TdmPolicy.NOT_DECLARED,
                raw_value=content,
                details=f'<meta name="tdm-reservation" content="{content}"> — invalid value',
            ))

    # Check <link rel="tdm-policy" href="...">
    def _has_tdm_policy_rel(v: str | list[str] | None) -> bool:
        if not v:
            return False
        return "tdm-policy" in (v if isinstance(v, list) else [v])

    link = soup.find("link", attrs={"rel": _has_tdm_policy_rel})
    if link is not None:
        href = (link.get("href") or "").strip()  # type: ignore[union-attr]
        if href:
            signals.append(TdmSignal(
                source="link_tag",
                policy=TdmPolicy.RESERVED,  # Linking to a policy implies reservation
                raw_value=href,
                details=f'<link rel="tdm-policy" href="{href}"> — TDM policy file referenced',
            ))

    return signals


async def check_tdmrep_json(url: str) -> TdmSignal | None:
    """Check if tdmrep.json exists at the site root.

    The W3C TDM Reservation Protocol recommends placing a
    tdmrep.json file at the site root for machine-readable
    TDM policy declarations.

    Args:
        url: Any URL on the site.

    Returns:
        TdmSignal if tdmrep.json found, None otherwise.
    """
    parsed = urlparse(url)
    tdmrep_url = f"{parsed.scheme}://{parsed.netloc}/tdmrep.json"

    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=5.0,
        ) as client:
            response = await client.get(tdmrep_url)
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or response.text.strip().startswith("{"):
                    return TdmSignal(
                        source="tdmrep_json",
                        policy=TdmPolicy.RESERVED,
                        raw_value=tdmrep_url,
                        details="tdmrep.json found — machine-readable TDM policy declared",
                    )
            return None
    except (httpx.HTTPError, httpx.TimeoutException):
        return None


def detect_conflicts(signals: list[TdmSignal]) -> list[Issue]:
    """Detect conflicting TDM signals across channels.

    If one channel says "reserved" and another says "not reserved",
    this is a compliance problem that must be resolved.

    Args:
        signals: All TDM signals found.

    Returns:
        List of conflict Issues.
    """
    policies = {s.policy for s in signals if s.policy != TdmPolicy.NOT_DECLARED}
    if TdmPolicy.RESERVED in policies and TdmPolicy.NOT_RESERVED in policies:
        sources_reserved = [s.source for s in signals if s.policy == TdmPolicy.RESERVED]
        sources_allowed = [s.source for s in signals if s.policy == TdmPolicy.NOT_RESERVED]
        return [Issue(
            severity=Severity.HIGH,
            category=Category.TDM,
            title="Conflicting TDM signals — reservation status unclear",
            description=(
                f"Some channels declare TDM rights reserved "
                f"({', '.join(sources_reserved)}) while others declare TDM allowed "
                f"({', '.join(sources_allowed)}). This ambiguity may invalidate "
                f"your Art. 4 reservation under EU Directive 2019/790."
            ),
            recommendation=(
                "Ensure all TDM signals are consistent. If you want to reserve "
                "TDM rights, set TDM-Reservation: 1 in HTTP headers AND "
                '<meta name="tdm-reservation" content="1"> in HTML. '
                "If you allow TDM, set both to 0 or remove the declarations."
            ),
            details={
                "reserved_by": sources_reserved,
                "allowed_by": sources_allowed,
            },
        )]
    return []


class TdmAnalyzer(AnalyzerBase):
    """Analyze TDM-Reservation compliance (EU DSM Directive Art. 4)."""

    async def analyze(self, url: str, html: str, headers: dict[str, str]) -> Score:
        """Analyze TDM reservation compliance.

        Checks three channels for TDM signals:
        1. TDM-Reservation HTTP header
        2. HTML meta/link tags
        3. tdmrep.json at site root

        Then evaluates consistency and generates a compliance score.
        A clear, consistent policy (either direction) scores highest.
        """
        issues: list[Issue] = []
        signals: list[TdmSignal] = []

        # 1. Check HTTP header
        header_signal = check_tdm_http_header(headers)
        if header_signal is not None:
            signals.append(header_signal)
            if header_signal.policy == TdmPolicy.NOT_DECLARED:
                issues.append(Issue(
                    severity=Severity.MEDIUM,
                    category=Category.TDM,
                    title="Invalid TDM-Reservation header value",
                    description=(
                        f"The TDM-Reservation HTTP header has value "
                        f'"{header_signal.raw_value}" which is not valid. '
                        f"Per W3C TDM Reservation Protocol, the value must be "
                        f'"0" (allow TDM) or "1" (reserve rights).'
                    ),
                    recommendation=(
                        "Set the TDM-Reservation header to either "
                        '"0" (allow text and data mining) or '
                        '"1" (reserve TDM rights under EU DSM Art. 4).'
                    ),
                    details={"raw_value": header_signal.raw_value},
                ))

        # 2. Check HTML meta/link tags
        meta_signals = check_tdm_meta_tags(html)
        signals.extend(meta_signals)

        for signal in meta_signals:
            if signal.policy == TdmPolicy.NOT_DECLARED:
                issues.append(Issue(
                    severity=Severity.MEDIUM,
                    category=Category.TDM,
                    title="Invalid TDM meta tag value",
                    description=(
                        f'The <meta name="tdm-reservation"> tag has value '
                        f'"{signal.raw_value}" which is not valid. '
                        f'Must be "0" or "1".'
                    ),
                    recommendation=(
                        'Set the content attribute to "0" (allow TDM) or '
                        '"1" (reserve rights).'
                    ),
                    details={"raw_value": signal.raw_value},
                ))

        # 3. Check tdmrep.json
        tdmrep_signal = await self._fetch_tdmrep(url)
        if tdmrep_signal is not None:
            signals.append(tdmrep_signal)

        # 4. Detect conflicts
        conflict_issues = detect_conflicts(signals)
        issues.extend(conflict_issues)

        # 5. Calculate score
        score_value = self._calculate_score(signals, issues)

        # 6. Generate informational issues
        if not signals:
            issues.append(Issue(
                severity=Severity.MEDIUM,
                category=Category.TDM,
                title="No TDM policy declared",
                description=(
                    "No TDM-Reservation signal found in HTTP headers, HTML meta "
                    "tags, or tdmrep.json. Under EU Directive 2019/790 Art. 4, "
                    "rightsholders must express TDM reservation in a machine-readable "
                    "way. Without a declaration, AI companies may assume TDM is allowed."
                ),
                recommendation=(
                    "Add a TDM-Reservation HTTP header to declare your policy:\n"
                    "  TDM-Reservation: 1  (reserve rights, opt-out of TDM)\n"
                    "  TDM-Reservation: 0  (allow TDM)\n\n"
                    "Optionally also add to HTML:\n"
                    '  <meta name="tdm-reservation" content="1">'
                ),
            ))
        else:
            # Report what was found
            valid_signals = [s for s in signals if s.policy != TdmPolicy.NOT_DECLARED]
            if valid_signals and not conflict_issues:
                policy = valid_signals[0].policy
                sources = [s.source for s in valid_signals]
                policy_label = (
                    "reserved (opt-out)" if policy == TdmPolicy.RESERVED
                    else "not reserved (opt-in)"
                )
                issues.append(Issue(
                    severity=Severity.INFO,
                    category=Category.TDM,
                    title=f"TDM policy declared: {policy_label}",
                    description=(
                        f"TDM reservation status is clearly declared as "
                        f'"{policy_label}" via: {", ".join(sources)}. '
                        f"This is compliant with EU DSM Directive Art. 4."
                    ),
                    recommendation=(
                        "No action needed. Your TDM policy is clearly declared."
                        if len(sources) > 1 else
                        " Consider adding TDM signals in additional channels "
                        "(HTTP header + HTML meta tag) for maximum clarity."
                    ),
                    details={
                        "policy": policy.value,
                        "sources": sources,
                        "signals": [
                            {"source": s.source, "value": s.raw_value, "details": s.details}
                            for s in valid_signals
                        ],
                    },
                ))

        return Score(
            category=Category.TDM,
            value=score_value,
            issues=issues,
        )

    @staticmethod
    def _calculate_score(signals: list[TdmSignal], issues: list[Issue]) -> int:
        """Calculate TDM compliance score.

        Scoring rubric (0-100):
        - No TDM declaration at all: 30 (policy gap)
        - Declaration via 1 channel, valid: 70
        - Declaration via 2+ channels, consistent: 90
        - Declaration via 3 channels (header + meta + tdmrep.json): 100
        - Invalid values: -15 per invalid signal
        - Conflicting signals: -30

        A low score doesn't mean "bad" — it means the TDM policy
        is unclear or missing, which is a compliance gap.
        """
        valid_signals = [s for s in signals if s.policy != TdmPolicy.NOT_DECLARED]
        invalid_signals = [s for s in signals if s.policy == TdmPolicy.NOT_DECLARED]
        has_conflicts = any(i.title.startswith("Conflicting") for i in issues)

        if not signals:
            return 30  # No declaration = compliance gap

        channels = len(valid_signals)
        if channels == 0:
            base = 20  # Only invalid signals found
        elif channels == 1:
            base = 70
        elif channels == 2:
            base = 90
        else:
            base = 100  # 3+ channels

        # Penalties
        penalty = 0
        penalty += len(invalid_signals) * 15
        if has_conflicts:
            penalty += 30

        return max(0, min(100, base - penalty))

    @staticmethod
    async def _fetch_tdmrep(url: str) -> TdmSignal | None:
        """Fetch tdmrep.json from the site root."""
        return await check_tdmrep_json(url)
