"""Command-line interface for OpenSEO Lens."""

from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from openseo_lens import __version__
from openseo_lens.models import AnalysisResult, Severity

console = Console()

ANALYZER_NAMES = ["crawlability", "tdm", "structured-data", "extractability", "attribution"]


@click.group()
@click.version_option(version=__version__, prog_name="openseo-lens")
def main() -> None:
    """OpenSEO Lens — AI Search Readiness & Web Discoverability Toolkit."""


@main.command()
@click.argument("url")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["text", "json", "html"]),
    default="text",
    help="Output format.",
)
@click.option("--output", "-o", type=click.Path(), default=None, help="Save report to file.")
@click.option(
    "--only",
    type=str,
    default=None,
    help="Comma-separated list of analyzers to run.",
)
def analyze(url: str, output_format: str, output: str | None, only: str | None) -> None:
    """Analyze a URL for AI search readiness."""
    selected = only.split(",") if only else ANALYZER_NAMES

    for name in selected:
        if name not in ANALYZER_NAMES:
            console.print(f"[red]Unknown analyzer: {name}[/red]")
            console.print(f"Available: {', '.join(ANALYZER_NAMES)}")
            sys.exit(1)

    console.print(f"\n[bold]OpenSEO Lens v{__version__}[/bold]")
    console.print(f"Analyzing: [cyan]{url}[/cyan]\n")

    # TODO: Run analyzers and collect results
    result = AnalysisResult(url=url)
    console.print("[yellow]Analysis engine not yet implemented. Coming soon![/yellow]\n")

    if output_format == "json":
        _output_json(result, output)
    elif output_format == "html":
        _output_html(result, output)
    else:
        _output_text(result)


def _output_text(result: AnalysisResult) -> None:
    """Print results as rich text to terminal."""
    table = Table(title="AI Search Readiness Report")
    table.add_column("Category", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", justify="right")

    for score in result.scores:
        table.add_row(
            score.category.value.replace("_", " ").title(),
            f"{score.value}/{score.max_value}",
            str(len(score.issues)),
        )

    console.print(table)
    console.print(f"\nOverall Score: [bold]{result.overall_score}/100[/bold]")
    console.print(f"Issues Found: {result.issue_count}\n")

    for issue in result.issues:
        color = {
            Severity.HIGH: "red",
            Severity.MEDIUM: "yellow",
            Severity.LOW: "blue",
            Severity.INFO: "dim",
        }[issue.severity]
        console.print(f"  [{color}][{issue.severity.value.upper()}][/{color}] {issue.title}")

    if not result.issues:
        console.print("  [green]No issues found.[/green]")


def _output_json(result: AnalysisResult, path: str | None) -> None:
    """Output results as JSON."""
    data = {
        "url": result.url,
        "overall_score": result.overall_score,
        "scores": [
            {
                "category": s.category.value,
                "value": s.value,
                "max_value": s.max_value,
            }
            for s in result.scores
        ],
        "issues": [
            {
                "severity": i.severity.value,
                "category": i.category.value,
                "title": i.title,
                "description": i.description,
                "recommendation": i.recommendation,
            }
            for i in result.issues
        ],
    }
    output = json.dumps(data, indent=2, ensure_ascii=False)
    if path:
        with open(path, "w") as f:
            f.write(output)
        console.print(f"[green]Report saved to {path}[/green]")
    else:
        click.echo(output)


def _output_html(result: AnalysisResult, path: str | None) -> None:
    """Output results as HTML."""
    # TODO: Implement HTML reporter
    console.print("[yellow]HTML reporter not yet implemented.[/yellow]")


if __name__ == "__main__":
    main()
