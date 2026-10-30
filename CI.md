# Continuous Integration

The repository uses GitHub Actions to run repeatable quality and security checks.

## Test and quality matrix

The `.github/workflows/tests.yml` workflow runs on pushes to `main`, pull requests
targeting `main`, and manual dispatch. It covers Python 3.11, 3.12, and 3.13.

Each matrix job:

1. Installs the package and development tools.
2. Runs Ruff lint checks.
3. Runs mypy static type checks.
4. Runs pytest with branch coverage and a machine-readable JSON report.
5. Audits installed dependencies with pip-audit.
6. Builds a wheel and installs it into a clean virtual environment.
7. Imports the installed package and executes the installed console command.

The JSON report is uploaded as a workflow artifact even when tests fail, if the report
file was produced. Coverage is reported but is not a claim of complete behavioural
verification; uncovered branches remain visible in the job log.

## Security automation

- `.github/workflows/codeql.yml` runs CodeQL analysis for Python on pushes, pull
  requests, manual dispatch, and a weekly schedule.
- `.github/workflows/secrets.yml` scans the full Git history with Gitleaks on pushes,
  pull requests, manual dispatch, and a weekly schedule.
- `.github/dependabot.yml` checks Python dependencies and GitHub Actions weekly.

These checks complement, rather than replace, manual review and repository-level
security settings. A successful scan is limited to the tools, rules, history, and
permissions available to the workflow.

## Interpretation

A green workflow means the checks executed in that workflow passed on the listed
runtime. It does not certify production deployment behaviour, multi-host fencing,
real provider semantics, or third-party interoperability. Review the test assumptions
and known limitations before interpreting results.
