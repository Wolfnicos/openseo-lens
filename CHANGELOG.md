# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Stub analyzers for Structured Data, Content Extractability, and Citation & Attribution (interface defined, implementation in progress)
- GitHub Actions CI pipeline (Python 3.10–3.13 matrix)
- Issue templates: bug report, feature request, analyzer proposal
- Pull request template with checklist

### Changed
- README: honest project status table marking in-development analyzers
- pyproject.toml: corrected GitHub URLs (anthropics → Wolfnicos)
- CONTRIBUTING.md: corrected clone URL

## [0.1.0] - 2026-03-01

### Added
- AI Crawlability analyzer: robots.txt parsing per RFC 9309, 12 AI bot directives, meta robots tags, X-Robots-Tag headers, weighted scoring
- TDM-Reservation compliance analyzer: EU DSM Directive Art. 4, HTTP header + HTML meta/link tags + tdmrep.json, conflict detection
- CLI: `openseo-lens analyze` with `--format text|json|html`, `--output`, `--only` flags
- JSON reporter: structured output with scores and issues
- HTML reporter: standalone dark-mode report page
- Core models: `Issue`, `Score`, `AnalysisResult` dataclasses
- 99 tests covering crawlability (94%) and TDM (88%) analyzers

[Unreleased]: https://github.com/Wolfnicos/openseo-lens/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Wolfnicos/openseo-lens/releases/tag/v0.1.0
