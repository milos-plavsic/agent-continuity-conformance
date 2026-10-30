# Execution Continuity Conformance

A compact reference implementation and adversarial test suite for preserving operation ownership, provider identity, and verifiable outcomes across retries, handovers, interruptions, and delayed remote effects.

[![Tests](https://github.com/milos-plavsic/agent-continuity-conformance/actions/workflows/tests.yml/badge.svg)](https://github.com/milos-plavsic/agent-continuity-conformance/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)

## The problem

A distributed operation can cross several independent boundaries. A process may submit a request, lose the acknowledgement, stop running, and be replaced by a successor. The provider may still complete the original request after ownership has transferred.

A successor that treats a missing local acknowledgement as proof of provider failure can submit a duplicate operation. A local ownership change can reject new stale requests at a protected boundary, but it cannot recall a request already admitted by a remote provider.

This project makes that distinction executable and testable.

## What is implemented

The repository includes a runnable Python reference implementation with:

- A SQLite-backed operation registry and explicit lifecycle states.
- Monotonically increasing ownership generations.
- Generation checks before local request preparation.
- A serialized in-process admission and handover boundary.
- Stable operation identity across attempts.
- A deterministic provider simulator with idempotent admission.
- Separate provider admission and completion events.
- Recovery after a lost acknowledgement and process restart.
- Durable `INCONCLUSIVE` state when a provider acknowledgement is lost or status is unavailable.
- A SHA-256 chained event log with a verifier for accidental or unauthorized event modification.
- A command-line demonstration of delayed provider completion after ownership transfer.
- Automated tests and GitHub Actions CI for Python 3.11, 3.12, and 3.13.

## Quick start

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/milos-plavsic/agent-continuity-conformance.git
cd agent-continuity-conformance
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m pytest
continuity-demo
```

On Windows PowerShell, activate the environment with `.venv\Scripts\Activate.ps1`.

The demo should report:

- Final state: `VERIFIED`
- Ownership generation: `2`
- Provider admissions: `1`
- Provider effects: `1`
- Event-chain verification: `true`

## Core scenario

1. Create and approve a logical operation.
2. Activate ownership generation 1.
3. Submit a provider request.
4. Simulate provider admission followed by a lost acknowledgement.
5. Transfer ownership to generation 2.
6. Complete the original provider request after the handover.
7. Reconcile using the original operation identity.
8. Verify the original effect without submitting a duplicate.

Two related cases are tested separately: a stale generation arriving after handover must be rejected before admission, and provider unavailability must leave the operation `INCONCLUSIVE`.

## Design invariants

1. An operation identifier represents one logical operation, not one delivery attempt.
2. Ownership generations increase monotonically and are not reused.
3. A stale generation cannot prepare new work after a handover has taken effect at the local boundary.
4. A successor reconciles prior work before preparing a potentially duplicative attempt.
5. Retries retain the same provider idempotency identity.
6. Provider admission is distinct from provider completion.
7. A lost response or unavailable status endpoint is not proof of failure.
8. An unresolved outcome cannot be promoted to `VERIFIED` without new evidence.
9. Event integrity checks do not establish the factual truth of an event.

## Architecture and project files

| File | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, lifecycle, invariants, and trust boundaries |
| [THREAT_MODEL.md](THREAT_MODEL.md) | Threats, assumptions, and mitigations |
| [CONFORMANCE.md](CONFORMANCE.md) | Proposed requirements and adversarial scenario catalogue |
| [PROVIDER_BOUNDARY.md](PROVIDER_BOUNDARY.md) | Provider admission, idempotency, and reconciliation |
| [COMPATIBILITY.md](COMPATIBILITY.md) | Minimal interoperability concepts |
| [DECISIONS.md](DECISIONS.md) | Implementation decisions and known limitations |
| [DEVELOPMENT.md](DEVELOPMENT.md) | Installation, test, and demonstration instructions |
| [ROADMAP.md](ROADMAP.md) | Remaining implementation and validation work |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution and change-control process |
| [SECURITY.md](SECURITY.md) | Security reporting guidance |
| [REPOSITORY_SETTINGS.md](REPOSITORY_SETTINGS.md) | Recommended GitHub branch protection and security settings |
| [examples/incident-recovery.md](examples/incident-recovery.md) | Worked delayed-request recovery scenario |

## Current status

**Status: Working reference implementation; conformance suite in progress.**

The current automated suite contains 44 tests, including generated lifecycle sequences, separate-process handover races, provider evidence substitution, malformed responses, and recovery after a failure between remote admission and local persistence. CI runs the suite on Python 3.11, 3.12, and 3.13, measures branch coverage, and publishes a machine-readable pytest report. The workflow also runs Ruff, mypy, pip-audit, and a non-editable wheel installation check. Separate workflows run CodeQL, full-history secret scanning, and scheduled dependency updates. The broader conformance catalogue still contains scenarios that are not yet implemented.

This is a reference implementation, not a production-ready distributed coordination service or an independent certification. The provider is simulated; no real provider adapter is included.

## Explicit limitations

- The per-operation lock coordinates admission and handover within one Python process only. Multiple service processes or hosts require a shared linearizable admission gate or a trusted gateway that enforces fencing.
- SQLite is used for durable local state. It is not presented as a distributed lock or consensus system.
- The fake provider supports stable idempotency keys and status lookup. Real provider semantics, key-retention windows, and cancellation guarantees must be verified independently.
- The event hash chain detects modification within the retained sequence. It is not a digital signature, does not authenticate event issuers, cannot detect removal of a trailing suffix without an external checkpoint, and can be recomputed by an attacker with full database control.
- The reference test suite does not prove correctness for untested providers, deployment configurations, or failure modes.
- Exactly-once effects cannot be promised for arbitrary providers that lack suitable idempotency and authoritative status facilities.

## License

Distributed under the MIT License. See [LICENSE](LICENSE).
