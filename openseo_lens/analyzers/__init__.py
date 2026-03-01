"""Analyzers for AI search readiness dimensions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from openseo_lens.models import Issue, Score


class AnalyzerBase(ABC):
    """Base class for all analyzers.

    Each analyzer examines one dimension of AI search readiness
    and returns a score with a list of issues found.
    """

    @abstractmethod
    async def analyze(self, url: str, html: str, headers: dict[str, str]) -> Score:
        """Analyze a page and return a score with issues.

        Args:
            url: The URL being analyzed.
            html: The raw HTML content of the page.
            headers: HTTP response headers.

        Returns:
            A Score object with the analysis results.
        """
        ...

    @staticmethod
    def _issue(
        severity: str,
        category: str,
        title: str,
        description: str,
        recommendation: str,
        **details: object,
    ) -> Issue:
        """Convenience method to create an Issue."""
        from openseo_lens.models import Category, Severity

        return Issue(
            severity=Severity(severity),
            category=Category(category),
            title=title,
            description=description,
            recommendation=recommendation,
            details=dict(details),
        )
