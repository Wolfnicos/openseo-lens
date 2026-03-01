# Contributing to OpenSEO Lens

Thank you for your interest in contributing! This guide will help you get started.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/anthropics/openseo-lens.git
cd openseo-lens

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install in development mode
pip install -e ".[dev]"
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=openseo_lens

# Run a specific test file
pytest tests/test_structured_data.py
```

## Code Style

We use **Ruff** for linting and formatting, and **mypy** for type checking.

```bash
# Lint
ruff check .

# Format
ruff format .

# Type check
mypy openseo_lens/
```

All code must:
- Pass `ruff check` with no errors
- Pass `mypy` with no errors
- Have type annotations on all public functions
- Include docstrings on all public classes and functions

## Pull Request Process

1. **Fork** the repository and create your branch from `main`
2. **Write tests** for any new functionality
3. **Update documentation** if you change public APIs
4. **Run the full test suite** before submitting
5. **Write a clear PR description** explaining what and why

### Commit Messages

Use clear, descriptive commit messages:

```
feat: add RDFa parsing support to structured data analyzer
fix: handle malformed JSON-LD without crashing
docs: add examples for CLI usage
test: add edge cases for robots.txt parsing
```

## Architecture Guidelines

### Adding a New Analyzer

1. Create a new file in `openseo_lens/analyzers/`
2. Subclass `AnalyzerBase` from `openseo_lens/analyzers/__init__.py`
3. Implement the `analyze()` method returning a list of `Issue` objects
4. Register the analyzer in `cli.py`
5. Add tests in `tests/`

### Adding a New Reporter

1. Create a new file in `openseo_lens/reporters/`
2. Subclass `ReporterBase` from `openseo_lens/reporters/__init__.py`
3. Implement the `render()` method
4. Register the format in `cli.py`

## Reporting Bugs

Open an issue with:
- Python version and OS
- Steps to reproduce
- Expected vs actual behavior
- URL being analyzed (if applicable and public)

## Code of Conduct

Be respectful, constructive, and inclusive. We follow the [Contributor Covenant](https://www.contributor-covenant.org/).

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
