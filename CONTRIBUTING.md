# Contributing

Thank you for contributing to yfinance-service. This document describes the preferred workflow, branch naming, and the basic checks required before opening a pull request.

## Links
- Project overview: [README.md](README.md)  
- Build / CI: [.github/workflows/ci.yml](.github/workflows/ci.yml)  
- Lint rules & formatters: [pyproject.toml](pyproject.toml)  
- Tests: [tests/](tests/)

## Workflow (Gitflow)
This repository follows Gitflow:
- Work from the `develop` branch.
- Create feature branches from `develop` with this exact naming convention:
  - feature/<issue-name-with-dashes>
  - Example: `feature/add-health-check-metrics`

Branch names must use `-` as the separator (no spaces, no underscores).

## Typical contribution steps (Windows / PowerShell)
1. Sync develop:
   ```
   git checkout develop
   git fetch origin
   git pull --rebase origin develop
   ```
2. Create a feature branch:
   ```
   git checkout -b feature/your-issue-name
   ```
3. Implement changes, add tests.
4. Rebase frequently onto develop to keep history linear:
   ```
   git fetch origin
   git rebase origin/develop
   ```
5. Push branch:
   ```
   git push -u origin feature/your-issue-name
   ```

## Pull Requests
- Base branch: `develop`.
- Title: short, imperative summary. Reference issue number when applicable (e.g., `Add caching for info endpoint (#123)`).
- Description: what changed, why, and how to test locally.
- Ensure CI passes (tests + lint). See [.github/workflows/ci.yml](.github/workflows/ci.yml).

## Tests & Quality checks (run locally)
- Install dependencies (see [pyproject.toml](pyproject.toml)). Using Poetry:
  ```
  poetry install
  ```
- Run tests:
  ```
  poetry run pytest --maxfail=1 --disable-warnings --tb=short
  ```
- Lint / formatting:
  ```
  poetry run ruff check app tests
  poetry run ruff format --check app tests
  poetry run black --check .
  ```
  Fix formatting before pushing; CI runs the same checks.

## Commit messages
- Use short, meaningful subject line in imperative mood.
- Reference issue numbers when relevant.
- Example:
  ```
  Add historical endpoint date validation

  - Validate start <= end
  - Add unit tests
  Fixes #123
  ```

## Code review and merging
- Open a PR targeting `develop`.
- At least one approving review required before merge.
- Squash or rebase commits as requested by reviewers. Keep history clear.
- Merge strategy: fast-forward or merge with squash (follow repo maintainer preference shown in PR).

## Tests required
- New features: include unit tests and/or integration tests in `tests/`.
- Bug fixes: include a regression test where feasible.

## Troubleshooting
- If CI fails, fetch the latest `develop` and rebase, resolve conflicts, and re-run tests locally.
- For environment issues, check [README.md](README.md) for running the service and tests.

Thanks for improving yfinance-service — your contributions are appreciated.
