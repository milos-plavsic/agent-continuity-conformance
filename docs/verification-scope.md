# Verification Scope

The current automated workflow runs the reference package's pytest suite on Python 3.11,
3.12, and 3.13.

The suite exercises local generation fencing, concurrent handover serialization, provider
idempotency, lost-acknowledgement recovery, delayed provider completion, process restart,
ambiguous provider status, lifecycle validation, and event-chain tampering.

The deterministic provider is a test double. A successful workflow does not verify the
behaviour of a real provider, multi-host coordination, production identity configuration,
or externally anchored evidence.
