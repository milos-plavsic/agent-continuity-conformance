# Repository Settings Checklist

The workflows in this repository provide automated checks, but repository-level merge
controls are configured in GitHub Settings rather than committed source files.

## Protect the main branch

Create a branch ruleset targeting `main` and enable:

- Require a pull request before merging.
- Require the three test-matrix checks: `Python 3.11`, `Python 3.12`, and
  `Python 3.13`, and `Python 3.14`.
- Require branches to be up to date before merging, if practical for this solo project.
- Require conversation resolution.
- Block force pushes.
- Block branch deletion.

A mandatory approval from another person is optional; do not make the repository
unmergeable if no second maintainer is available. The required test checks are the
important minimum.

## Enable repository security features

Under Settings → Code security and analysis, enable the available options:

- Dependabot alerts.
- Dependabot security updates.
- Secret scanning and push protection, where available.
- Private vulnerability reporting.

CodeQL and Gitleaks workflows are already defined in this repository. GitHub's
security dashboard availability and alert settings still depend on the account's
repository permissions and plan.

## Verification

After saving the ruleset, open a small test pull request and confirm that GitHub blocks
merging until the three Python matrix checks pass. Do not merge a test change solely to
validate the ruleset; close it after confirming the checks are enforced.

These settings are administrative controls and are not represented as enabled merely
because this checklist exists.
