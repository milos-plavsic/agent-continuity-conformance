# Roadmap

## Current status

- **Phase 0, specification baseline:** complete as an initial draft.
- **Phase 1, minimal executable reference:** implemented for a single-process reference deployment.
- **Phase 2, adversarial conformance suite:** initial tests are implemented; the full catalogue is not yet covered.
- **Phase 3, portable signed evidence:** not started. The current event chain is a tamper-evident hash chain, not signed evidence.
- **Phase 4, independent interoperability exercise:** not started.
- **Phase 5, release candidate:** not started.

## Phase 1: Minimal executable reference

Implemented:

- SQLite operation registry.
- Lifecycle state transitions.
- Monotonic ownership generations.
- Per-operation in-process admission and handover serialization.
- Stable operation and attempt identities.
- Deterministic provider simulator.
- Provider admission and completion separation.
- Lost-acknowledgement recovery.
- Event hash-chain verification.
- Runnable command-line demonstration.

Known limitation: the per-operation lock is process-local. It does not provide cross-process or cross-host fencing.

## Phase 2: Adversarial conformance suite

Initial automated coverage includes:

- Stale generation rejected before provider admission.
- Lost acknowledgement reconciled without duplicate provider effect.
- Provider completion delayed until after ownership transfer.
- Lost acknowledgement persisted as INCONCLUSIVE before returning to the caller.
- Provider unavailability preserved as INCONCLUSIVE.
- Duplicate provider admission deduplicated by stable key.
- Process restart and durable state recovery.
- Monotonic generation and invalid transition checks.
- Event modification and deletion detection.
- Independent operation identity scopes.
- Concurrent handover attempts with exactly one successful generation advance.
- Malformed event data rejected by the integrity verifier.
- Installed command-line entry point exercised in CI.

Remaining work:

1. Add a provider simulator with conflicting and malformed status responses.
2. Add explicit replay and cross-operation evidence substitution tests.
3. Add property-based transition testing if it materially improves coverage.
4. Publish a machine-readable test result format.

## Phase 3: Portable evidence package

Deliverables:

- Versioned evidence envelope.
- Issuer identity and signature coverage.
- Trust-root and revocation policy.
- Offline verification utility.
- Tampering, substitution, and replay test vectors.

Acceptance:

- Modified protected content is rejected.
- Wrong-operation and stale-evidence replay are rejected.
- Trust-root assumptions are explicit.
- A valid signature is not represented as proof that an assertion is factually true.

## Phase 4: Independent interoperability exercise

Deliverables:

- Two separately implemented contract participants or adapters.
- Shared, versioned test vectors.
- Reproducible integration report.

Acceptance:

- Both implementations pass the same required vectors.
- Deviations and unsupported provider capabilities are published.
- No interoperability claim is made from testing only one implementation.

## Phase 5: Release candidate

Deliverables:

- Versioned specification.
- Reproducible test package.
- Reference implementation.
- Security review notes.
- Example evidence bundle.
- Compatibility and release policy.

Acceptance:

- Clean-environment instructions work.
- Published results can be independently reproduced.
- Known limitations are visible.
- License and ownership details are confirmed before wider distribution.

## Scope constraint

Do not add broad orchestration features, a general-purpose policy language, multiple cloud deployments, or a large adapter catalogue unless a concrete conformance requirement needs them. Prioritize deterministic tests at the provider boundary.
