# Continuous Integration

The workflow in `.github/workflows/tests.yml` runs on pushes to `main`, pull requests
targeting `main`, and manual dispatch.

The test matrix covers Python 3.11, 3.12, and 3.13. Each job checks out the repository,
installs the package with its test extra, and runs the complete pytest suite.

A green workflow means the automated tests passed on the listed interpreter version.
It does not certify production deployment behaviour, multi-host fencing, or real provider
semantics. Review the test assumptions and known limitations before interpreting results.
