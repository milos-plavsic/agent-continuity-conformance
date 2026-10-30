# Design Decisions

## D-001: Separate operation identity from attempt identity

The operation identifier remains stable across retries and ownership changes. Each attempt
has a unique identifier. This lets recovery locate provider-side work after restart.

## D-002: Separate provider admission from completion

The provider simulator exposes admission and completion separately. A provider may accept
work while the caller loses the acknowledgement; the effect may become observable later.

## D-003: Derive provider idempotency identity from operation identity

All attempts for one logical operation use the same provider key. A production adapter
must validate key scope, payload rules, and retention period.

## D-004: Use SQLite for a compact durable reference

SQLite transactions keep the example reproducible without external infrastructure.
This does not imply that SQLite alone coordinates multiple hosts.

## D-005: Serialize local admission and handover

A per-operation lock protects the local generation check, preparation, provider admission,
and ownership transfer in one process. Multi-process deployments need a shared
linearizable gate or fencing at a trusted gateway.

## D-006: Preserve ambiguous outcomes

Provider unavailability maps to INCONCLUSIVE. A timeout or failed status query is not
proof that the provider did not admit or complete a request.

## D-007: Use a hash chain, not signatures

Events are linked with SHA-256 over canonical JSON. This demonstrates tamper detection,
not issuer authentication or non-repudiation. A signed evidence format is deferred until
key custody, trust roots, canonicalization, and revocation policy are specified.

## D-008: Keep tests deterministic

The fake provider is controlled directly by tests rather than timing sleeps. This makes
failure scenarios repeatable.

## Known limitations

- The admission lock is process-local.
- Provider idempotency semantics are simpler than many real providers.
- The event chain is not externally anchored.
- There is no distributed lease or consensus implementation.
- There is no production provider adapter.
- Passing this test suite does not establish correctness for untested infrastructure.
