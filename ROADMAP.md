# Roadmap

## Guiding constraint

Build the smallest useful conformance package. Do not expand into a general orchestration platform, universal authorization framework, or multi-provider integration catalogue.

Every phase should produce a reviewable artifact and a reproducible acceptance result.

## Phase 0: Specification baseline

**Status:** Documentation drafted; review required.

Deliverables:

- Architecture and lifecycle model.
- Threat model and explicit assumptions.
- Provider-boundary semantics.
- Compatibility concepts.
- Adversarial test catalogue.
- Worked incident-recovery scenario.

Acceptance:

- Terms are consistent across documents.
- Every lifecycle state has a defined meaning.
- Provider admission is distinguished from provider completion.
- The delayed admitted-request case is explicitly covered.
- No implementation or test result is claimed without evidence.

## Phase 1: Minimal executable reference

Deliverables:

- Small operation registry.
- Ownership-generation transitions.
- Protected execution boundary.
- Deterministic fake provider.
- Stable operation and attempt identities.
- Durable event/evidence records.

Acceptance:

- Tests demonstrate monotonic generations.
- Stale requests are rejected at the protected boundary.
- Conflicting transitions are rejected.
- Restart reconstructs state from durable records.

## Phase 2: Adversarial conformance suite

Deliverables:

- Deterministic event scheduler or equivalent test harness.
- Fault injection for delay, duplication, reordering, crash, and response loss.
- Tests T01-T12 from CONFORMANCE.md.
- Machine-readable test results.

Acceptance:

- Every required scenario has an explicit result.
- The delayed admitted-request scenario is distinct from duplicate delivery.
- INCONCLUSIVE is preserved when provider evidence is insufficient.
- Test runs are repeatable from a clean checkout.

## Phase 3: Evidence package and verifier

Deliverables:

- Versioned evidence envelope.
- Integrity protection and trust configuration.
- Offline verification utility.
- Tampering and replay test vectors.

Acceptance:

- Modified protected content is rejected.
- Wrong-operation and stale-evidence replay are rejected.
- Trust-root and revocation assumptions are documented.
- Verification output distinguishes valid signature from factual truth.

## Phase 4: Independent interoperability exercise

Deliverables:

- Two separately implemented contract participants or adapters.
- Shared versioned test vectors.
- Reproducible integration report.

Acceptance:

- Both implementations pass the same required vectors.
- Deviations and unsupported provider capabilities are published.
- No interoperability claim is made from tests performed against only one implementation.

## Phase 5: Release candidate

Deliverables:

- Versioned specification.
- Reproducible test package.
- Reference implementation.
- Security review notes.
- Example evidence bundle.
- Release and compatibility policy.

Acceptance:

- Clean-environment instructions work.
- All published results can be independently reproduced.
- Known limitations are visible.
- License is selected and included before public reuse is invited.

## Explicit exclusions

Unless a concrete conformance requirement demands otherwise, do not add:

- Multiple cloud deployment examples.
- A generic workflow designer.
- Broad provider-specific adapter collections.
- An extensible policy language.
- A dashboard that does not improve verification.
- Benchmark claims without reproducible baselines.
- Compatibility claims based only on shared terminology.

## Immediate next steps

1. Review and freeze the terminology in the current documents.
2. Choose the implementation language and test runner.
3. Define the minimal persistent record model.
4. Implement the deterministic fake provider and operation registry.
5. Build T01, T05, and T06 first, because they exercise the most important distinction between stale admission, ambiguous response, and delayed provider effect.
