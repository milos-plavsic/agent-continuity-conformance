# Architecture

## 1. Purpose

This document describes a minimal architecture for preserving operation continuity when ownership changes or execution is interrupted. It is deliberately implementation-neutral.

The architecture separates coordination, authorization, execution, evidence, and reconciliation. These concerns may be implemented in one service or distributed across several services, but their responsibilities and trust boundaries must remain explicit.

## 2. Logical components

### 2.1 Operation registry

Stores the durable identity and current lifecycle state of each logical operation.

Minimum responsibilities:

- Allocate or validate a stable operation identifier.
- Store the current ownership generation.
- Record state transitions with concurrency control.
- Prevent invalid or stale transitions.
- Retain references to evidence needed for reconciliation.

### 2.2 Ownership coordinator

Determines which execution owner is currently permitted to coordinate an operation.

Minimum responsibilities:

- Establish a new generation during handover.
- Ensure generations increase monotonically.
- Prevent two generations from both being treated as current.
- Make ownership changes durable before a successor acts.

The coordinator does not, by itself, guarantee that a remote provider will reject a request from an older generation. That requires enforcement at the provider boundary or a trusted intermediary.

### 2.3 Authorization boundary

Checks whether an operation is permitted immediately before a consequential action is admitted.

The check should bind at least:

- Operation identifier.
- Ownership generation.
- Action or capability.
- Target resource or provider.
- Relevant policy or authorization version.
- Expiry or validity constraints, where applicable.

A check performed only when a task is queued is insufficient if ownership can change before execution.

### 2.4 Execution adapter

Translates an authorized logical operation into a provider-specific request.

It should preserve the stable operation identifier across retries and expose provider-specific admission and result semantics. It must not silently translate an ambiguous result into success.

### 2.5 Evidence store

Retains records required to reconstruct the operation history.

Evidence should be append-only where practical, access-controlled, timestamped, and linked by stable identifiers. A record should distinguish an assertion made by a component from a fact attested by a provider.

### 2.6 Reconciliation worker

Runs after restart, redelivery, or ownership transfer.

It inspects prior attempts and provider evidence, determines whether an operation can safely continue, and records the basis for its decision. If the available evidence is insufficient, the outcome remains unresolved.

## 3. Operation lifecycle

The proposed lifecycle is:

`PROPOSED → APPROVED → FENCED → RECONCILED → PREPARED → COMMITTED → VERIFIED`

Terminal or exceptional outcomes:

- `FAILED`: failure is established by authoritative evidence.
- `INCONCLUSIVE`: available evidence cannot establish whether the consequential effect occurred.

State meanings:

| State | Meaning |
|---|---|
| PROPOSED | An operation has been identified but not authorized. |
| APPROVED | Required policy and business authorization have been recorded. |
| FENCED | The current ownership generation has been established and stale generations are excluded at the relevant local boundary. |
| RECONCILED | Prior attempts have been examined and their status recorded. |
| PREPARED | Required inputs and provider request identity are fixed for the attempt. |
| COMMITTED | The provider has acknowledged admission or commitment according to its documented semantics. |
| VERIFIED | Evidence establishes the intended effect or postcondition. |
| FAILED | Evidence establishes that the operation did not complete as intended. |
| INCONCLUSIVE | Evidence is insufficient to classify the result safely. |

Implementations may use different internal states, but their mapping to these externally meaningful states must be documented.

## 4. Core invariants

1. An operation identifier denotes one logical operation, not one delivery attempt.
2. Ownership generations are monotonically increasing and never reused.
3. A stale generation cannot obtain new authorization at a protected boundary.
4. A successor must reconcile prior attempts before issuing a potentially duplicative request.
5. A retry preserves the logical operation identity and the relevant provider idempotency key.
6. A provider acknowledgement is not automatically proof of the intended final effect.
7. A timeout or lost response is not proof of failure.
8. An unresolved outcome cannot be promoted to VERIFIED without new evidence.
9. Evidence records identify their issuer, subject, operation, generation, and relevant event.
10. State transitions are concurrency-safe and reject stale writes.

## 5. Handover sequence

A safe handover has the following logical order:

1. Read the current operation and generation.
2. Establish a new generation using an atomic or otherwise linearizable ownership update.
3. Ensure the protected local boundary recognizes the new generation.
4. Prevent the former generation from initiating new consequential actions.
5. Inspect all prior attempts, including attempts whose provider outcome is not yet known.
6. Query provider status or inspect authoritative provider evidence where supported.
7. Decide whether to resume, wait, compensate, or preserve an unresolved outcome.
8. Record the reconciliation evidence and decision.
9. Permit the successor to proceed only within the authority of the new generation.

The exact mechanism depends on the consistency guarantees of the storage and provider systems. Implementations must document those assumptions.

## 6. Consistency requirements

The operation registry must provide a concurrency model strong enough to prevent two owners from independently advancing the same operation as current. A compare-and-swap update, transactional row version, consensus-backed lease, or equivalent mechanism may be appropriate.

A lease alone is not a complete fence. A process may pause beyond lease expiry and later resume. The protected boundary must validate a generation or equivalent fencing token rather than trusting that a former owner has stopped.

## 7. Evidence model

Evidence should distinguish at least:

- Authorization decision.
- Ownership-generation change.
- Attempt creation.
- Provider request submission.
- Provider admission acknowledgement.
- Provider result or status query.
- Observed postcondition.
- Reconciliation decision.

Each event should include a stable event identifier, operation identifier, generation, event type, issuer, timestamp, and integrity metadata. Provider-specific identifiers and raw response references should be retained where permitted.

Cryptographic signatures may be used to protect evidence portability and integrity. A signature proves that a particular key signed particular bytes; it does not prove that the underlying assertion is true or that the signer was entitled to make it. Key identity, trust roots, revocation, canonical serialization, and verification policy must therefore be specified separately.

## 8. Deployment patterns

The contract can be implemented with:

- A transactional database and worker pool.
- A message broker and durable operation registry.
- A workflow engine with explicit generation fencing.
- A service acting as a provider gateway.
- A combination of these patterns.

No deployment pattern is conformant merely because it uses a particular technology. Conformance depends on observed behaviour at the defined boundaries.
