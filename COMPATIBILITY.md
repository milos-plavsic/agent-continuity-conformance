# Compatibility Contract

## 1. Goal

This document defines the minimum information two independently implemented components need to exchange to coordinate an operation safely.

It intentionally avoids prescribing a universal schema, wire protocol, or framework. An implementation may use JSON, protocol buffers, relational records, signed documents, or another representation if it preserves the required semantics.

## 2. Required concepts

A compatible exchange must carry or resolve the following concepts:

| Concept | Requirement |
|---|---|
| Operation identity | Stable across retries and handover |
| Attempt identity | Unique for each execution attempt |
| Ownership generation | Monotonically increasing fencing value |
| Current state | Explicit lifecycle state |
| Action scope | The action and target covered by authorization |
| Authorization reference | Verifiable decision or policy reference |
| Provider identity | Target provider and request reference |
| Idempotency identity | Stable key where provider supports it |
| Evidence references | Durable records supporting prior events |
| Outcome | VERIFIED, FAILED, or INCONCLUSIVE as applicable |

## 3. Semantic requirements

### Identity

An operation identifier MUST identify one logical operation across all delivery attempts. Attempt identifiers MUST NOT be substituted for operation identifiers.

### Generation

A generation MUST be ordered and scoped to the operation or ownership domain. A receiver must be able to determine whether a request is stale relative to the current generation.

### Authorization

Authorization must bind the operation, action, target, and generation. A receiver must not infer authorization merely from possession of an operation identifier.

### Evidence

Evidence references must be resolvable or packaged with the exchange. A receiver must be able to distinguish an issuer assertion from provider-originated evidence.

### Outcome

The exchange must preserve uncertainty. A sender must not map a timeout to failure or success without additional evidence.

## 4. Suggested logical envelope

The following is illustrative, not a finalized schema:

```json
{
  "contract_version": "0.1",
  "operation_id": "stable-logical-id",
  "attempt_id": "unique-attempt-id",
  "generation": 8,
  "state": "RECONCILED",
  "action": {
    "name": "provider-operation",
    "target": "provider-resource"
  },
  "authorization": {
    "decision_ref": "evidence-reference",
    "policy_version": "policy-revision"
  },
  "provider": {
    "name": "provider-name",
    "request_id": "provider-request-reference",
    "idempotency_key": "stable-key"
  },
  "outcome": "INCONCLUSIVE",
  "evidence_refs": [
    "evidence-reference"
  ]
}
```

The values above are placeholders. A real implementation must define identifier syntax, field validation, canonicalization, signature coverage, and compatibility rules.

## 5. Versioning

The contract version must be explicit. Changes should be classified as:

- **Additive:** optional fields or capabilities that older consumers can safely ignore.
- **Restrictive:** validation or semantic changes that may reject previously accepted exchanges.
- **Breaking:** changes to identity, generation, state, or outcome semantics.

Breaking changes require a new major contract version and migration guidance. Consumers must reject unsupported major versions rather than silently guessing.

## 6. Evidence portability

A portable evidence package should include:

- Contract version.
- Operation and attempt identifiers.
- Event sequence or causal references.
- Issuer identities.
- Relevant public keys or resolvable trust-root references.
- Signature algorithm and canonicalization method, if signed.
- Revocation and validity policy.
- Provider evidence references or retained provider responses.
- Verification instructions.

A verifier should be able to validate integrity offline when all required evidence and trust material are included. Offline integrity verification does not independently establish that the original assertions were factually correct.

## 7. Compatibility testing

Two implementations should exchange a fixed set of test vectors covering:

- Current and stale generations.
- Same operation with multiple attempts.
- Duplicate evidence references.
- Unsupported contract versions.
- Missing mandatory identity fields.
- Conflicting outcomes.
- Invalid signatures or modified payloads.
- Provider result ambiguity.

Interoperability should be claimed only after both sides pass the same versioned test vectors and publish the scope and limitations of the test.
