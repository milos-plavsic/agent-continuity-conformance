# Development

## Requirements

- Python 3.11 or newer
- Git
- A terminal

The runtime uses only the Python standard library. The optional test extra installs pytest, Hypothesis, pytest-cov, pytest-json-report, Ruff, mypy, build, and pip-audit for development and verification.

## Install

```bash
git clone https://github.com/milos-plavsic/agent-continuity-conformance.git
cd agent-continuity-conformance
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip "setuptools>=84.1.0"
python -m pip install -e ".[test]"
```

On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

## Run tests

```bash
ruff check .
mypy --ignore-missing-imports continuity_conformance
python -m pytest --cov=continuity_conformance --cov-branch --cov-report=term-missing --json-report --json-report-file=pytest-report.json
pip-audit --skip-editable
python -m build --wheel
```

## Run the demonstration

```bash
continuity-demo
```

Or run `python -m continuity_conformance.demo`. To retain the database, run
`continuity-demo --database ./runtime/continuity.sqlite3`.

## Expected behaviour

The deterministic scenario creates and authorizes one operation, activates generation 1,
has the provider admit a request while the acknowledgement is lost, transfers ownership
to generation 2, completes the original request, and reconciles using the original
operation identity. The output should report VERIFIED, one provider admission, one
external effect, and a valid event chain.

## Scope and limitations

The per-operation lock coordinates handover and admission within one Python process only.
A multi-process deployment requires a shared linearizable admission gate or fencing at a
trusted provider gateway. SQLite is a durable local registry, not a distributed lock.

The simulated provider is in-memory and supports idempotency and immediately authoritative
status lookup. The restart test retains this provider instance while recreating the local
service and registry connection. A real provider adapter must document whether a
"not found" response is authoritative or merely eventually consistent. If absence cannot
be established authoritatively, the safe result is INCONCLUSIVE, not a retry.

The hash chain detects modification within the retained sequence but is not a signature,
does not authenticate event issuers, cannot detect removal of a trailing suffix without
an external checkpoint, and cannot resist an attacker who can rewrite the entire database
and recompute every hash.

The tests are a conformance starting point, not a security certification.
