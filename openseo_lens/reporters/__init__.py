"""Report generators for analysis results."""

from __future__ import annotations

from abc import ABC, abstractmethod

from openseo_lens.models import AnalysisResult


class ReporterBase(ABC):
    """Base class for all reporters.

    Reporters take an AnalysisResult and render it into
    a specific output format (JSON, HTML, text, etc.).
    """

    @abstractmethod
    def render(self, result: AnalysisResult) -> str:
        """Render the analysis result into the target format.

        Args:
            result: The complete analysis result.

        Returns:
            The rendered output as a string.
        """
        ...
