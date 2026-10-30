# Threat Model

## 1. Scope

This threat model covers distributed operations that may be retried, resumed, transferred between owners, or executed through remote providers.

It focuses on integrity of ownership, authorization, operation identity, outcome classification, and evidence.

## 2. Assets

- Correct execution of authorized operations.
- Prevention of unauthorized or stale execution.
- Integrity of operation state and ownership generations.
- Unambiguous identity of logical operations and attempts.
- Provider-side effect records and status.
- Evidence used for audit and reconciliation.
- Confidentiality of operation payloads and credentials.

## 3. Security objectives

1. A former owner cannot initiate new consequential work after its authority has been fenced.
2. A successor cannot unknowingly duplicate an operation whose prior result is unresolved.
3. A retry cannot obtain a fresh logical identity merely because it is a new delivery.
4. Evidence cannot be silently altered without detection where integrity protection is enabled.
5. An unresolved provider outcome remains unresolved until sufficient evidence is available.
6. Authorization is checked at the boundary that admits the consequential action.

## 4. Adversary and failure capabilities

The design assumes that one or more of the following may occur, accidentally or through malicious behaviour:

- A worker pauses, crashes, restarts, or resumes after a long delay.
- Messages are duplicated, reordered, delayed, or delivered after a handover.
- Network partitions interrupt requests or responses.
- A response is lost after a provider has admitted a request.
- A local database write succeeds while a subsequent remote call fails, or vice versa.
- Two workers temporarily hold inconsistent views of ownership.
- A stale process retries using cached state.
- A caller replays an old request or evidence record.
- A provider returns delayed, incomplete, or inconsistent status information.
- A credential or signing key is compromised.
- An operator or component misclassifies an ambiguous outcome.

## 5. Trust boundaries

### Local coordination boundary

The operation registry and ownership coordinator establish current state. Their consistency and access controls are security-critical.

### Authorization boundary

The component that admits a consequential action must validate current authority. If this boundary is bypassable, upstream checks do not provide an effective fence.

### Provider boundary

A remote provider may have its own admission, idempotency, cancellation, and status semantics. Local state cannot override those semantics.

### Evidence boundary

Evidence may cross service, storage, or organizational boundaries. Consumers must validate provenance and integrity rather than trusting a record solely because it is present.

## 6. Principal threats and mitigations

| Threat | Potential consequence | Required mitigation |
|---|---|---|
| Stale owner resumes | Unauthorized or duplicate action | Monotonic generation and enforcement at protected boundary |
| Duplicate delivery | Repeated side effect | Stable operation identity and provider idempotency |
| Delayed admitted request | Effect occurs after handover | Provider reconciliation, delayed-result handling, explicit uncertainty |
| Lost provider response | Incorrect retry or false failure | Query provider by stable key; preserve INCONCLUSIVE if unresolved |
| Stale state write | Ownership rollback | Version checks and atomic transition rules |
| Replayed request | Repeated or unauthorized action | Nonce/identity checks, generation validation, idempotency |
| Forged evidence | False audit conclusion | Authenticated issuers, signatures or integrity protection, trust policy |
| Compromised key | False evidence accepted | Key rotation, revocation, narrow trust roots, incident response |
| Overbroad credential | Unauthorized provider action | Least privilege, scoped credentials, short validity |
| Operator override | Unsafe state transition | Dual control for high-risk overrides and immutable audit record |

## 7. Important limitation: admission cannot be recalled locally

A fencing check can prevent a stale owner from obtaining new admission at a boundary that enforces the fence. It cannot retroactively recall a request that a remote provider has already admitted.

A request may be submitted before handover, accepted by the provider, and only produce an observable effect after handover. A local generation change does not erase that provider-side admission.

Implementations must therefore distinguish:

- A stale request rejected before provider admission.
- A request admitted before handover whose effect is pending.
- A request whose admission or effect cannot currently be determined.

The second and third cases require provider-specific reconciliation. They must not be represented as ordinary duplicate-delivery cases.

## 8. Assumptions to document

Every implementation report must state:

- Consistency guarantees of the operation registry.
- How generations are allocated and checked.
- Which components can reach the provider directly.
- Whether provider idempotency is supported and its key-retention period.
- Whether provider status can be queried by operation identity.
- Whether cancellation is supported and what cancellation means.
- Evidence authenticity and key-management model.
- Clock assumptions, if timestamps affect authorization or ordering.
- Recovery behaviour when the provider is unavailable.
- Operator override and escalation procedures.

## 9. Residual risks

No local protocol can guarantee exactly-once effects across an arbitrary provider that offers neither idempotency nor authoritative status queries. In that case, the safe result may be an unresolved operation requiring manual reconciliation.

Cryptographic integrity does not establish factual correctness. A trusted component can sign a false statement. Independent evidence sources, constrained issuer authority, and explicit verification procedures reduce but do not eliminate this risk.

A hash chain without an externally retained checkpoint cannot detect deletion of a trailing suffix. An attacker with full write access to the evidence store may also recompute the chain. Stronger tamper resistance requires externally anchored checkpoints or signatures under separately controlled keys.

## 10. Out of scope

This document does not claim to solve general host compromise, malicious administrators with unrestricted infrastructure control, arbitrary provider dishonesty, or all distributed consensus problems. Implementations should add deployment-specific threat analysis.
