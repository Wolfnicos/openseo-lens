"""JSON reporter — outputs analysis results as structured JSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from openseo_lens import __version__
from openseo_lens.models import AnalysisResult
from openseo_lens.reporters import ReporterBase


class JsonReporter(ReporterBase):
    """Render analysis results as JSON."""

    def render(self, result: AnalysisResult) -> str:
        """Render the analysis result as a JSON string."""
        data = {
            "version": __version__,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "url": result.url,
            "overall_score": result.overall_score,
            "scores": [
                {
                    "category": score.category.value,
                    "value": score.value,
                    "max_value": score.max_value,
                    "issue_count": len(score.issues),
                }
                for score in result.scores
            ],
            "issues": [
                {
                    "severity": issue.severity.value,
                    "category": issue.category.value,
                    "title": issue.title,
                    "description": issue.description,
                    "recommendation": issue.recommendation,
                    "details": issue.details,
                }
                for issue in result.issues
            ],
            "metadata": result.metadata,
        }
        return json.dumps(data, indent=2, ensure_ascii=False)
