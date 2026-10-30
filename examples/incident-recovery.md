# Example: Delayed Provider Result During Ownership Handover

This example illustrates the most important provider-boundary case in the specification. It is a design scenario, not a report of an observed production incident.

## Situation

A service is coordinating a consequential operation identified as `op-2048`.

- Worker A owns generation 12.
- Worker A submits provider request `req-77`.
- The provider admits the request.
- The provider response is lost.
- Worker A becomes unavailable.
- Ownership transfers to Worker B at generation 13.
- The provider later completes the effect associated with `req-77`.

## Unsafe recovery

An unsafe successor might:

1. Observe that Worker A did not record a successful response.
2. Assume the provider did not perform the operation.
3. Submit a new request under generation 13.
4. Cause the same external effect a second time.

This is unsafe because absence of a local response is not evidence that the provider did not admit or complete the original request.

## Required recovery

Worker B should:

1. Load the durable record for `op-2048`.
2. Confirm generation 13 is current.
3. Identify the predecessor attempt and provider request `req-77`.
4. Query the provider using the stable request identity or idempotency key.
5. If the provider confirms completion, record the provider evidence and verify the required postcondition.
6. If the provider reports that the request remains pending, wait or use documented cancellation semantics.
7. If the provider cannot establish the outcome, preserve `INCONCLUSIVE` and escalate rather than blindly resubmit.
8. Record the reconciliation decision and its evidence.

## Expected event history

| Event | Owner generation | Interpretation |
|---|---:|---|
| Operation created | 12 | Logical operation established |
| Request submitted | 12 | Attempt started |
| Provider admitted request | 12 | Provider may complete it |
| Response lost | 12 | Outcome not locally established |
| Ownership transferred | 13 | New owner becomes current |
| Provider completion observed | 13 | Effect belongs to original operation |
| Reconciliation completed | 13 | Success may be verified from evidence |

The provider completion observed under generation 13 does not mean generation 13 initiated the original request. The request identity and event history preserve that distinction.

## Test assertions

A deterministic test for this scenario should assert:

- The provider records one admission for the original idempotency identity.
- The response-loss fault does not cause a false FAILED state.
- Generation 13 can reconcile the predecessor request.
- Generation 13 does not submit a second logical operation while the first outcome is unresolved.
- A later provider completion is associated with the original operation and attempt.
- VERIFIED is reached only after the required evidence and postcondition are available.

## Variant: stale request not yet admitted

A separate test should cover a request from generation 12 that reaches the protected boundary only after generation 13 is current. That request must be rejected before provider admission.

These two tests must remain separate. One tests local stale-generation enforcement; the other tests reconciliation of work already admitted by the provider.
