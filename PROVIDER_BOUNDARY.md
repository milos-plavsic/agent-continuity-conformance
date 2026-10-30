# Provider Boundary

## 1. Why this boundary matters

The provider boundary is where a logical operation becomes an externally consequential request. It is also where local ownership rules meet the provider's own admission, idempotency, cancellation, and status semantics.

A local system can reject a stale request before forwarding it. It cannot assume that changing local ownership cancels a request already admitted by a remote provider.

## 2. Distinguish the relevant events

An implementation should distinguish these events:

1. **Created:** the local system created an attempt.
2. **Authorized:** the local system approved the attempt under a particular generation.
3. **Submitted:** bytes or a request were sent toward the provider.
4. **Admitted:** the provider accepted responsibility for processing the request, according to its documented contract.
5. **Effected:** the intended external state change occurred.
6. **Observed:** the local system obtained evidence of the effect or its absence.

These events are not interchangeable. In particular, submission does not prove admission, admission does not necessarily prove completion, and a lost response does not prove that admission failed.

## 3. Idempotency

Where supported, every logical operation should use a stable provider idempotency key. The key should remain stable across retries of the same operation and should not be reused for a different logical operation.

The implementation must document:

- Key format and scope.
- Provider retention period.
- Whether payload equality is required on reuse.
- Behaviour when the same key is used with different parameters.
- Whether the provider guarantees one effect, one response, or merely request deduplication.
- What happens after the provider's idempotency retention period expires.

An idempotency key is not a substitute for authorization or ownership fencing.

## 4. Delayed request example

Consider the following ordering:

- Generation 7 is current.
- The predecessor submits request R using logical operation O.
- The provider admits R.
- The response is delayed or lost.
- Ownership transfers to generation 8.
- The successor begins recovery.
- The provider later reports or performs the effect associated with R.

The generation change prevents new stale admission only if the protected boundary checks the generation. It does not erase R after provider admission.

The successor must query or otherwise reconcile O before submitting another request that could create the same effect.

## 5. Provider capability classes

For test planning, classify a provider by the capabilities it actually documents and exposes:

| Capability | Meaning |
|---|---|
| Idempotent request admission | Repeated requests with the same key are deduplicated within defined scope |
| Lookup by operation key | Status can be queried using a stable request identity |
| Authoritative completion status | Provider can distinguish accepted, completed, failed, and unknown states |
| Cancellation | Provider can cancel some admitted work under documented conditions |
| Postcondition query | Caller can inspect whether the intended external state exists |

Do not infer one capability from another. For example, a provider may support idempotent admission but not authoritative completion status.

## 6. Reconciliation decision table

| Evidence | Safe interpretation | Typical next step |
|---|---|---|
| Provider confirms no admission | No provider admission established | Retry only after authorization and identity checks |
| Provider confirms admitted, pending | Work may still complete | Wait, monitor, or use documented cancellation |
| Provider confirms completed | Completion established to provider's stated semantics | Verify required postcondition |
| Provider confirms rejected | Rejection established | Correct cause or terminate |
| Provider unavailable or status ambiguous | Outcome unresolved | Preserve INCONCLUSIVE; do not blindly resubmit |
| Provider reports conflicting evidence | Evidence conflict | Hold and escalate |

## 7. Cancellation semantics

Cancellation must be treated as a provider operation with its own identity and result. A cancellation request does not prove cancellation succeeded.

Record whether cancellation was requested, admitted, acknowledged, and confirmed. If the provider cannot establish whether the original request will still take effect, retain the unresolved outcome.

## 8. Required adapter contract

An execution adapter should expose:

- Submit using stable operation identity.
- Return provider request identity.
- Report provider admission separately from completion.
- Query status where supported.
- Request cancellation where supported.
- Preserve raw or verifiable provider evidence.
- Surface ambiguous outcomes explicitly.
- Reject stale ownership generations before forwarding new requests.

Provider-specific adapters must document deviations and unsupported capabilities.
