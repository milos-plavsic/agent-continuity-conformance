# Conformance Specification

## 1. Status and language

This is a proposed specification. It is not yet a certification standard.

The current reference package implements a subset of these requirements. The test suite is
evidence about that reference package only; it does not establish conformance of external
implementations or production deployments.

The terms **MUST**, **MUST NOT**, **SHOULD**, and **MAY** express requirement strength for implementations claiming alignment with this specification.

A conformance report must identify the exact implementation and version tested. Passing this suite does not establish security outside the tested environment and assumptions.

## 2. Conformance subjects

A test target may be:

- An operation registry.
- An ownership coordinator.
- An authorization boundary.
- An execution adapter.
- A complete deployment integrating these components.

Reports must state which subject was tested and which boundaries were simulated.

## 3. Required data concepts

An implementation MUST represent, directly or through a documented mapping:

- Stable logical operation identity.
- Attempt identity.
- Ownership generation or equivalent fencing value.
- Current lifecycle state.
- Authorization decision and scope.
- Provider request identity or idempotency key, where supported.
- Provider admission and outcome evidence.
- Reconciliation decision.
- Explicit unresolved outcome.

The exact field names and serialization are implementation-defined at this stage.

## 4. Normative behaviours

### C1. Stable operation identity

A retry, restart, or redelivery MUST retain the same logical operation identity. A distinct attempt may have its own attempt identifier.

### C2. Monotonic ownership generation

A handover MUST advance the ownership generation. Generations MUST NOT be reused or moved backwards.

### C3. Stale-owner rejection

After a new generation is active at the protected boundary, a request carrying an older generation MUST be rejected before new consequential admission.

### C4. Reconciliation before successor action

A successor MUST inspect prior attempts before issuing an operation that could duplicate a prior external effect.

### C5. Duplicate-delivery safety

Repeated delivery of the same logical operation MUST NOT create more than one provider effect where the provider supports an appropriate idempotency mechanism and the implementation uses it correctly.

Where the provider lacks such a mechanism, the implementation MUST document the limitation and preserve uncertainty rather than claim an unconditional at-most-once guarantee.

### C6. Delayed admitted request

The implementation MUST distinguish a request rejected before provider admission from a request admitted before handover whose effect is observed afterward.

The implementation MUST NOT claim that local fencing recalls a request already admitted by a remote provider.

A test must cover a predecessor request that crosses the provider admission boundary before handover, with its result or effect delayed until after the successor takes ownership. The successor must reconcile that request before issuing a potentially duplicative operation.

### C7. Ambiguous provider result

If a request may have been admitted but its result cannot be established, the implementation MUST preserve an unresolved outcome. It MUST NOT mark the operation VERIFIED or FAILED solely because a timeout occurred.

### C8. Evidence integrity

Where signed or integrity-protected evidence is used, modification of protected content MUST be detected by the verifier. Reports MUST document trust roots and key-revocation assumptions.

### C9. Transition integrity

Invalid transitions and stale concurrent updates MUST be rejected. A test must exercise conflicting state updates from two ownership generations.

### C10. Restart and recovery

After process restart, the implementation MUST reconstruct the operation state from durable records and reconcile outstanding attempts before proceeding.

## 5. Required adversarial scenarios

| ID | Scenario | Expected result |
|---|---|---|
| T01 | Former owner submits after handover | Rejected at protected boundary |
| T02 | Old owner resumes with cached state | Rejected using stale generation |
| T03 | Same message delivered repeatedly | One logical operation; provider idempotency applied |
| T04 | Successor starts while predecessor result is pending | Successor waits or reconciles; no blind duplicate |
| T05 | Provider admits request, response is lost | Outcome remains unresolved until reconciled |
| T06 | Provider effect appears after ownership transfer | Attributed to original operation; no false cancellation claim |
| T07 | Two owners race to advance state | Only current generation can commit transition |
| T08 | Process restarts after provider admission | Durable state recovered and provider queried |
| T09 | Evidence bytes are modified | Integrity verification fails |
| T10 | Old evidence is replayed for another operation | Binding or identity validation rejects it |
| T11 | Provider cannot answer status query | Operation remains unresolved and is escalated |
| T12 | Operator attempts unsupported terminal transition | Transition rejected or explicitly audited as an override |

## 6. Test methodology

Each scenario should specify:

1. Initial state and ownership generation.
2. Actors and trust boundaries.
3. Exact event ordering.
4. Fault injected.
5. Expected provider-side effects.
6. Expected durable state.
7. Evidence required to support the conclusion.
8. Cleanup and repeatability conditions.

Tests should control event ordering rather than relying on timing sleeps. Use barriers, deterministic fake providers, controllable queues, and explicit fault injection where possible.

## 7. Result classification

Every test result must be one of:

- **PASS:** observed behaviour satisfies the stated expectation.
- **FAIL:** observed behaviour violates the expectation.
- **INCONCLUSIVE:** the test environment or evidence cannot establish the result.
- **NOT RUN:** the scenario was not executed.
- **NOT APPLICABLE:** the requirement does not apply, with justification.

Do not combine INCONCLUSIVE and NOT RUN into PASS.

## 8. Conformance report

A report should include:

- Implementation name, version, and source revision.
- Test suite revision.
- Runtime and infrastructure versions.
- Provider type and relevant semantics.
- Configuration and consistency assumptions.
- Scenario-by-scenario results.
- Evidence artifacts and verification instructions.
- Known gaps, exclusions, and deviations.
- Date and responsible test operator.

## 9. Limits

Passing these tests demonstrates only that the tested implementation behaved as expected in the declared environment. It does not prove universal correctness, eliminate all races, or certify third-party systems not included in the test boundary.
