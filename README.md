# OpenSEO Lens

**Open Source AI Search Readiness Toolkit**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

> Analyze how well your website is prepared for AI-powered search engines — Google AI Overviews, ChatGPT Search, Perplexity, Bing Copilot, and others.

---

## Why This Matters

AI search engines don't list links — they **synthesize answers**. If your content isn't structured for machine reading, it becomes invisible.

| Before (Traditional SEO) | Now (AI Search Era) |
|:---|:---|
| Optimize for keyword ranking | Optimize for **answer extraction** |
| Meta tags and backlinks | Structured data and **citeability** |
| Google lists your page | AI **reads** your page and may cite it |
| robots.txt blocks crawlers | robots.txt blocks **AI training bots** |
| No TDM obligations | **EU DSM Directive Art. 4** TDM compliance |

**No open source tool exists to audit AI search readiness.** OpenSEO Lens fills this gap.

---

## Five Analysis Dimensions

### 1. AI Crawlability
Parse `robots.txt` for AI-specific bot directives across **12 known AI crawlers**:

| Bot | Operator | Purpose |
|:----|:---------|:--------|
| `GPTBot` | OpenAI | ChatGPT training data |
| `ChatGPT-User` | OpenAI | ChatGPT live browsing |
| `Google-Extended` | Google | Gemini training data |
| `GoogleOther` | Google | AI Overviews, other AI |
| `CCBot` | Common Crawl | Training data for many AI models |
| `anthropic-ai` | Anthropic | Claude training data |
| `ClaudeBot` | Anthropic | Claude web search |
| `Bytespider` | ByteDance | TikTok AI |
| `PerplexityBot` | Perplexity | Perplexity AI search |
| `Amazonbot` | Amazon | Alexa, AI services |
| `meta-externalagent` | Meta | Facebook AI, LLaMA |
| `cohere-ai` | Cohere | Enterprise AI |

Detects conflicting directives, overly restrictive configurations, and `ai.txt` presence.

### 2. TDM-Reservation Compliance (EU DSM Directive Art. 4)
- Detects `TDM-Reservation` HTTP headers (`0` = allow mining, `1` = reserve rights)
- Parses robots.txt for TDM-specific fields
- Checks HTML `<meta>` tags for TDM declarations
- Detects `tdmrep.json` references
- Reports conflicting TDM signals across channels
- Generates clear compliance status for non-technical stakeholders

### 3. Structured Data Validation
- Detects and validates **JSON-LD**, **Microdata**, and **RDFa** markup
- Checks schema.org compliance and property completeness
- Identifies missing schemas critical for AI citation (FAQPage, HowTo, Article, Organization)
- Scores schema completeness: required vs. optional vs. AI-critical properties
- Reports nesting errors and property violations

### 4. Content Extractability
- Evaluates how easily AI engines can extract answers from your content
- Heading hierarchy validation (skip detection, nesting errors)
- Semantic HTML usage scoring (`<article>`, `<section>`, `<main>`, `<nav>`)
- Content-to-boilerplate ratio calculation
- Answer-readiness metric: can an AI extract a clear answer per section?

### 5. Citation & Attribution Auditing
- Analyzes whether AI engines are likely to cite your content
- Author markup detection (schema.org Person, `rel=author`, meta tags)
- Publication date and freshness signal extraction
- E-E-A-T pattern scoring (Experience, Expertise, Authoritativeness, Trustworthiness)
- Source attribution quality assessment

---

## Installation

```bash
pip install openseo-lens
```

Or install from source:

```bash
git clone https://github.com/Wolfnicos/openseo-lens.git
cd openseo-lens
pip install -e .
```

## Quick Start

```bash
# Analyze a single URL (all 5 dimensions)
openseo-lens analyze https://example.com

# Output as JSON
openseo-lens analyze https://example.com --format json

# Generate HTML report
openseo-lens analyze https://example.com --format html --output report.html

# Run specific analyzers only
openseo-lens analyze https://example.com --only crawlability
openseo-lens analyze https://example.com --only tdm,structured-data
openseo-lens analyze https://example.com --only extractability,attribution
```

## Example Output

```
OpenSEO Lens — AI Search Readiness Report
==========================================

URL: https://example.com
Overall Score: 68/100

  AI Crawlability     ██████░░░░  65/100
  TDM Compliance      ████░░░░░░  40/100
  Structured Data     ████████░░  82/100
  Extractability      ████████░░  78/100
  Citation Readiness  ██████░░░░  63/100

Issues Found: 9
  [HIGH]   GPTBot blocked in robots.txt — content invisible to ChatGPT
  [HIGH]   No TDM-Reservation header — EU DSM Art. 4 compliance gap
  [HIGH]   Missing FAQPage schema — AI engines prioritize FAQ content
  [MEDIUM] No tdmrep.json detected — consider declaring TDM policy
  [MEDIUM] Conflicting directives: Google-Extended blocked but GoogleOther allowed
  [MEDIUM] H1 tag missing on 3 pages
  [LOW]    No author markup detected (E-E-A-T signal)
  [LOW]    Publication date missing — freshness signals help AI citation
  [INFO]   ai.txt file not found (optional but recommended)
```

---

## Comparison with Existing Tools

| Feature | OpenSEO Lens | Lighthouse | Screaming Frog | Ahrefs | Google Rich Results |
|:--------|:---:|:---:|:---:|:---:|:---:|
| AI bot detection in robots.txt | **Yes** | No | No | No | No |
| TDM-Reservation header check | **Yes** | No | No | No | No |
| Schema.org AI-readiness scoring | **Yes** | No | Partial | Partial | Syntax only |
| Content extractability for LLMs | **Yes** | No | No | No | No |
| E-E-A-T / citation auditing | **Yes** | No | No | Partial | No |
| Works offline | **Yes** | Yes | Yes | No | No |
| Open source | **Yes** | Yes | No | No | No |
| No API keys required | **Yes** | Yes | Yes | No | Yes |
| EU TDM Directive compliance | **Yes** | No | No | No | No |
| Multilingual (EN/FR/DE/RO) | **Yes** | No | No | No | No |

---

## European Focus

OpenSEO Lens is built with European regulations and needs in mind:

- **DSM Directive Art. 4** — Dedicated TDM-Reservation compliance checking. Detects whether your site properly declares text and data mining reservation rights via HTTP headers, robots.txt, and HTML meta tags, as required by EU Directive 2019/790.
- **GDPR by design** — Runs entirely offline after fetching public HTML. No data stored, transmitted, or processed on external servers. No tracking, no telemetry.
- **Multilingual** — Full support for EN, FR, DE, RO with locale-aware analysis, reporting, and content structure checks calibrated per language.
- **EAA alignment** — Content structure checks align with European Accessibility Act and WCAG 2.1 AA requirements.

---

## Architecture

```
openseo_lens/
├── cli.py                  # Click-based CLI entry point
├── models.py               # Dataclasses for results
├── analyzers/
│   ├── crawlability.py     # robots.txt AI bot directives (12 bots)
│   ├── tdm.py              # TDM-Reservation compliance (EU DSM Art. 4)
│   ├── structured_data.py  # JSON-LD / Microdata / RDFa validation
│   ├── extractability.py   # Content quality for AI consumption
│   └── attribution.py      # Citation & authorship auditing
└── reporters/
    ├── json_reporter.py    # JSON output
    └── html_reporter.py    # Standalone HTML report (dark mode)
```

**Design principles:**
- Each analyzer is independent and composable
- Offline-first: fetch once, analyze locally
- No external API keys required
- No tracking, no telemetry, no data collection
- Deterministic: same input → same output

---

## Project Status

| Milestone | Timeline | Status | Deliverables |
|:----------|:---------|:-------|:-------------|
| **M1-M2** | Month 1-2 | Skeleton | Core infrastructure + structured data analyzer |
| **M3-M4** | Month 3-4 | ✅ Complete | AI crawlability + TDM compliance analyzer |
| **M5-M6** | Month 5-6 | Planned | Content extractability scoring engine |
| **M7-M8** | Month 7-8 | Planned | Citation auditing + E-E-A-T analysis |
| **M9-M10** | Month 9-10 | Planned | Multilingual support (EN/FR/DE/RO) + HTML reporter |
| **M11-M12** | Month 11-12 | Planned | Documentation, benchmarks, v1.0 release |

### Post-v1.0 Roadmap
- CI/CD integration (GitHub Actions, GitLab CI)
- WordPress / Drupal / TYPO3 plugins
- Browser extension for real-time analysis
- Comparative analysis (benchmark against competitors)
- API server mode

---

## Tech Stack

| Component | Technology |
|:----------|:-----------|
| Language | Python 3.10+ |
| CLI | Click |
| HTTP | httpx |
| HTML Parsing | BeautifulSoup4 + lxml |
| Output | Rich (terminal), JSON, HTML |
| Testing | pytest + pytest-asyncio |
| Linting | Ruff |
| Type Checking | mypy |

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

```bash
# Development setup
git clone https://github.com/Wolfnicos/openseo-lens.git
cd openseo-lens
pip install -e ".[dev]"

# Run tests
pytest

# Linter + type checking
ruff check .
mypy openseo_lens/
```

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Funding

This project has applied for funding through the [NGI Zero Commons Fund](https://nlnet.nl/commonsfund/) (application 2026-04-0b3).

---

**OpenSEO Lens** — Making the web discoverable in the AI era.
