"""Data models for analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Issue severity level."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Category(str, Enum):
    """Analysis category."""

    STRUCTURED_DATA = "structured_data"
    CRAWLABILITY = "crawlability"
    EXTRACTABILITY = "extractability"
    ATTRIBUTION = "attribution"


@dataclass
class Issue:
    """A single issue found during analysis."""

    severity: Severity
    category: Category
    title: str
    description: str
    recommendation: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class Score:
    """Score for a single analysis dimension."""

    category: Category
    value: int  # 0-100
    max_value: int = 100
    issues: list[Issue] = field(default_factory=list)

    @property
    def percentage(self) -> float:
        return (self.value / self.max_value) * 100 if self.max_value else 0


@dataclass
class AnalysisResult:
    """Complete analysis result for a URL."""

    url: str
    scores: list[Score] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def overall_score(self) -> int:
        if not self.scores:
            return 0
        return round(sum(s.value for s in self.scores) / len(self.scores))

    @property
    def high_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == Severity.HIGH]

    @property
    def issue_count(self) -> int:
        return len(self.issues)
