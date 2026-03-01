"""Command-line interface for OpenSEO Lens."""

from __future__ import annotations

import asyncio
import json
import sys

import click
import httpx
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

    stderr = Console(stderr=True)
    stderr.print(f"\n[bold]OpenSEO Lens v{__version__}[/bold]")
    stderr.print(f"Analyzing: [cyan]{url}[/cyan]\n")

    result = asyncio.run(_run_analysis(url, selected))

    if output_format == "json":
        _output_json(result, output)
    elif output_format == "html":
        _output_html(result, output)
    else:
        _output_text(result)


async def _run_analysis(url: str, selected: list[str]) -> AnalysisResult:
    """Fetch the URL and run selected analyzers."""
    result = AnalysisResult(url=url)

    # Fetch the page
    html = ""
    headers: dict[str, str] = {}
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            response = await client.get(url)
            html = response.text
            headers = dict(response.headers)
    except (httpx.HTTPError, httpx.TimeoutException) as e:
        console.print(f"[red]Failed to fetch {url}: {e}[/red]")
        console.print("[yellow]Running analysis with empty content...[/yellow]\n")

    # Run selected analyzers
    if "crawlability" in selected:
        from openseo_lens.analyzers.crawlability import CrawlabilityAnalyzer

        analyzer = CrawlabilityAnalyzer()
        score = await analyzer.analyze(url=url, html=html, headers=headers)
        result.scores.append(score)
        result.issues.extend(score.issues)

    if "tdm" in selected:
        from openseo_lens.analyzers.tdm import TdmAnalyzer

        analyzer_tdm = TdmAnalyzer()
        score = await analyzer_tdm.analyze(url=url, html=html, headers=headers)
        result.scores.append(score)
        result.issues.extend(score.issues)

    if "structured-data" in selected:
        from openseo_lens.analyzers.structured_data import StructuredDataAnalyzer

        analyzer_sd = StructuredDataAnalyzer()
        score = await analyzer_sd.analyze(url=url, html=html, headers=headers)
        result.scores.append(score)
        result.issues.extend(score.issues)

    if "extractability" in selected:
        from openseo_lens.analyzers.extractability import ExtractabilityAnalyzer

        analyzer_ext = ExtractabilityAnalyzer()
        score = await analyzer_ext.analyze(url=url, html=html, headers=headers)
        result.scores.append(score)
        result.issues.extend(score.issues)

    if "attribution" in selected:
        from openseo_lens.analyzers.attribution import AttributionAnalyzer

        analyzer_attr = AttributionAnalyzer()
        score = await analyzer_attr.analyze(url=url, html=html, headers=headers)
        result.scores.append(score)
        result.issues.extend(score.issues)

    return result


def _output_text(result: AnalysisResult) -> None:
    """Print results as rich text to terminal."""
    table = Table(title="AI Search Readiness Report")
    table.add_column("Category", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Issues", justify="right")

    for score in result.scores:
        bar_filled = round(score.value / 10)
        bar_empty = 10 - bar_filled
        bar = f"{'█' * bar_filled}{'░' * bar_empty}"
        table.add_row(
            score.category.value.replace("_", " ").title(),
            f"{bar}  {score.value}/{score.max_value}",
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
        console.print(f"         {issue.recommendation}\n")

    if not result.issues:
        console.print("  [green]No issues found — all clear![/green]")


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
                "details": i.details,
            }
            for i in result.issues
        ],
    }
    output_str = json.dumps(data, indent=2, ensure_ascii=False)
    if path:
        with open(path, "w") as f:
            f.write(output_str)
        console.print(f"[green]Report saved to {path}[/green]")
    else:
        click.echo(output_str)


def _output_html(result: AnalysisResult, path: str | None) -> None:
    """Output results as HTML."""
    from openseo_lens.reporters.html_reporter import HtmlReporter

    reporter = HtmlReporter()
    html = reporter.render(result)
    if path:
        with open(path, "w") as f:
            f.write(html)
        console.print(f"[green]HTML report saved to {path}[/green]")
    else:
        click.echo(html)


if __name__ == "__main__":
    main()
