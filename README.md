# OpenSEO Lens

**AI Search Readiness & Web Discoverability Toolkit**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Funded by EU](https://img.shields.io/badge/Funded%20by-EU%20Horizon%20Europe-blue)](https://www.ngi.eu/ngi-projects/ngi-zero-commons-fund/)

> Analyze how well your website is prepared for AI-powered search engines — Google AI Overviews, Bing Copilot, Perplexity, ChatGPT Search, and others.

---

## Why This Matters

The way people discover content on the web is fundamentally changing. AI-powered search engines don't just index pages — they **read, interpret, and synthesize** content to generate direct answers. Websites that aren't optimized for this new paradigm risk becoming invisible.

- **62% of Google searches** now trigger AI Overviews (2025)
- AI engines prefer content that is **structured, citeable, and machine-readable**
- EU regulations (DSM Directive Art. 4, GDPR) create new obligations around text and data mining
- Most existing SEO tools focus on traditional ranking signals, not AI readiness

**OpenSEO Lens** bridges this gap with an open source toolkit that analyzes your website's readiness for the AI search era.

## Key Features

### Structured Data Validation
- Detects and validates **JSON-LD**, **Microdata**, and **RDFa** markup
- Checks schema.org compliance and completeness
- Identifies missing schemas critical for AI citation (FAQ, HowTo, Article, Organization)
- Reports schema nesting errors and property violations

### AI Crawlability Analysis
- Parses `robots.txt` for AI-specific bot directives (GPTBot, Google-Extended, CCBot, Anthropic)
- Detects **TDM-Reservation** HTTP headers (EU DSM Directive Art. 4 compliance)
- Analyzes `ai.txt` and meta robot tags for AI crawler permissions
- Reports conflicting or overly restrictive directives

### Content Extractability Scoring
- Evaluates how easily AI engines can extract and understand your content
- Checks heading hierarchy, content structure, and semantic HTML
- Measures answer-readiness: can an AI cite a clear, factual answer from your page?
- Scores content clarity, entity density, and information architecture

### Citation & Attribution Auditing
- Analyzes whether your content is likely to be cited by AI engines
- Checks for proper authorship signals (E-E-A-T patterns)
- Evaluates source attribution and reference quality
- Identifies opportunities to improve citability

## Installation

```bash
pip install openseo-lens
```

Or install from source:

```bash
git clone https://github.com/anthropics/openseo-lens.git
cd openseo-lens
pip install -e .
```

## Quick Start

```bash
# Analyze a single URL
openseo-lens analyze https://example.com

# Output as JSON
openseo-lens analyze https://example.com --format json

# Save report to file
openseo-lens analyze https://example.com --format html --output report.html

# Analyze with specific checks only
openseo-lens analyze https://example.com --only structured-data,crawlability
```

## Example Output

```
OpenSEO Lens — AI Search Readiness Report
==========================================

URL: https://example.com
Overall Score: 72/100

  Structured Data     ████████░░  82/100
  AI Crawlability     ██████░░░░  65/100
  Extractability      ████████░░  78/100
  Citation Readiness  ██████░░░░  63/100

Issues Found: 7
  [HIGH]   Missing FAQPage schema — AI engines prioritize FAQ content
  [HIGH]   GPTBot blocked in robots.txt — content invisible to ChatGPT
  [MEDIUM] No TDM-Reservation header — EU DSM Art. 4 compliance gap
  [MEDIUM] H1 tag missing on 3 pages
  [LOW]    No author markup detected (E-E-A-T signal)
  ...
```

## EU Compliance Focus

OpenSEO Lens is built with European regulations in mind:

- **DSM Directive Art. 4** (Text and Data Mining): Detects whether your site properly declares TDM reservation rights via HTTP headers or robots.txt, as required by EU Directive 2019/790
- **GDPR-aware**: The tool runs entirely offline after fetching public HTML — no data is stored, transmitted, or processed on external servers
- **Multilingual**: Full support for EN, FR, DE, RO with locale-aware analysis and reporting
- **European Accessibility Act (EAA 2025)**: Content structure checks align with WCAG 2.1 AA requirements

## Architecture

```
openseo_lens/
├── cli.py                  # Click-based CLI entry point
├── models.py               # Dataclasses for results
├── analyzers/
│   ├── structured_data.py  # JSON-LD / Microdata / RDFa
│   ├── crawlability.py     # robots.txt, TDM headers, ai.txt
│   ├── extractability.py   # Content quality for AI consumption
│   └── attribution.py      # Citation & authorship auditing
└── reporters/
    ├── json_reporter.py    # JSON output
    └── html_reporter.py    # HTML report generation
```

**Design principles:**
- Each analyzer is independent and composable
- Offline-first: fetch once, analyze locally
- No external API keys required for core functionality
- No tracking, no telemetry, no data collection
- Results are deterministic — same input, same output

## Roadmap

| Phase | Timeline | Milestone |
|-------|----------|-----------|
| **M1** | Month 1-2 | Core analyzers (structured data + crawlability) |
| **M2** | Month 3-4 | Content extractability scoring engine |
| **M3** | Month 5-6 | Citation auditing + E-E-A-T analysis |
| **M4** | Month 7-8 | Multilingual support (EN/FR/DE/RO) |
| **M5** | Month 9-10 | HTML reporting + batch analysis |
| **M6** | Month 11-12 | Documentation, benchmarks, v1.0 release |

### Future (post-v1.0)
- Browser extension for real-time analysis
- CI/CD integration (GitHub Actions, GitLab CI)
- WordPress / CMS plugins
- Comparative analysis (benchmark against competitors)
- API server mode for integration with other tools

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| CLI | Click |
| HTTP | httpx |
| HTML Parsing | BeautifulSoup4 + lxml |
| Output | Rich (terminal), JSON, HTML |
| Testing | pytest |
| Linting | Ruff |
| Type Checking | mypy |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/anthropics/openseo-lens.git
cd openseo-lens
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Type checking
mypy openseo_lens/
```

## License

MIT License — see [LICENSE](LICENSE) for details.

## Funding

<table>
  <tr>
    <td>
      This project is funded through the <a href="https://nlnet.nl/commonsfund/">NGI Zero Commons Fund</a>, a fund established by <a href="https://nlnet.nl/">NLnet</a> with financial support from the European Commission's <a href="https://ngi.eu/">Next Generation Internet</a> programme, under the aegis of DG Communications Networks, Content and Technology under grant agreement No 101135429.
    </td>
  </tr>
</table>

---

**OpenSEO Lens** — Making the web discoverable in the AI era.
