# Execution Continuity Conformance

A specification-first project for testing whether distributed services preserve ownership, authorization, execution identity, and verifiable outcomes when work is retried, handed over, interrupted, or resumed.

The project defines a narrow compatibility contract and an adversarial conformance suite for systems that coordinate long-running operations across changing workers and infrastructure boundaries.

## The problem

Distributed systems routinely separate the decision to perform an operation from the component that eventually performs it. During that interval, a process may restart, ownership may change, messages may be redelivered, or a remote provider may return an ambiguous result.

These conditions create several distinct risks:

- A former owner continues acting after responsibility has transferred.
- A retry creates a second external effect.
- A successor proceeds without sufficient evidence about the predecessor's work.
- A stale or incomplete record is treated as proof of completion.
- A request already admitted by a remote provider is incorrectly assumed to be cancellable by local fencing.
- An unresolved outcome is converted into a false success or failure.

Ordinary retry tests and duplicate-message tests do not cover every one of these cases. In particular, duplicate delivery is not equivalent to a request from a former owner that was admitted by a provider before handover and only takes effect afterward.

## Objective

Define and test a small, implementation-neutral contract for safe continuity across ownership changes.

The contract focuses on five properties:

1. **Explicit ownership:** every consequential operation has a well-defined owner and ownership generation.
2. **Fenced authority:** stale generations cannot newly authorize consequential work at the enforcement boundary.
3. **Stable operation identity:** retries and redeliveries retain the identity of the original logical operation.
4. **Evidence-based succession:** a successor reconciles prior work from durable evidence before deciding what may happen next.
5. **Honest outcomes:** verified, failed, and unresolved outcomes remain distinguishable.

The project is intended to be usable across services, queues, workflow engines, databases, and external providers. It does not prescribe a particular cloud, programming language, database, queue, or orchestration framework.

## Current status

<badge>Specification and baseline phase</badge>

This repository currently contains design documentation and a proposed conformance model. It does not yet claim a completed executable test suite, production implementation, independent certification, or third-party interoperability.

Planned implementation work is tracked in [ROADMAP.md](ROADMAP.md). Test expectations are defined in [CONFORMANCE.md](CONFORMANCE.md).

## Repository guide

| File | Purpose |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components, lifecycle, invariants, and trust boundaries |
| [THREAT_MODEL.md](THREAT_MODEL.md) | Threats, assumptions, attacker capabilities, and mitigations |
| [CONFORMANCE.md](CONFORMANCE.md) | Normative behaviours and required adversarial scenarios |
| [PROVIDER_BOUNDARY.md](PROVIDER_BOUNDARY.md) | The limits of local fencing at remote execution boundaries |
| [COMPATIBILITY.md](COMPATIBILITY.md) | Minimal interoperability contract and mapping guidance |
| [ROADMAP.md](ROADMAP.md) | Sequenced implementation plan and acceptance gates |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution and change-control process |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and security review expectations |
| [examples/incident-recovery.md](examples/incident-recovery.md) | Worked handover and recovery scenario |

## Design principles

- **Small contract, not a universal framework.** Define only the fields and behaviours needed to test continuity.
- **Enforcement over convention.** A recorded policy decision is not sufficient unless the consequential boundary enforces it.
- **Evidence over assumption.** A timeout is not proof that a remote operation failed.
- **At-most-once effect where supported.** Use stable operation identity and provider-side idempotency where available; do not promise this property where the provider cannot support it.
- **Fail closed on uncertainty.** Preserve unresolved state and require reconciliation instead of inventing a terminal result.
- **Portable evidence.** Evidence should be inspectable and verifiable without requiring access to the original runtime.
- **Adversarial by default.** Tests should deliberately reorder, delay, duplicate, interrupt, and replay events.

## Non-goals

This project is not intended to:

- Replace an orchestration platform, message broker, database, or workflow engine.
- Define a general-purpose identity system or authorization language.
- Guarantee cancellation of work already admitted by a remote provider.
- Claim exactly-once execution across arbitrary external systems.
- Treat a successful local test run as proof of production security.
- Define a broad standard for every form of distributed process recovery.

## Terminology

- **Operation:** one logical unit of consequential work, identified independently of individual delivery attempts.
- **Owner:** the current authority responsible for coordinating an operation.
- **Generation:** a monotonically increasing ownership epoch used to distinguish successive owners.
- **Fence:** an enforcement check that rejects stale generations at a protected boundary.
- **Provider:** an external system that admits or performs a consequential operation.
- **Evidence:** durable records used to establish what was authorized, attempted, admitted, and observed.
- **Reconciliation:** the process of resolving prior attempts before a successor proceeds.
- **Unresolved outcome:** a state in which available evidence cannot establish success or failure.

## Status and claims

All requirements in this repository are design proposals until backed by executable tests and documented results. A conformance report must state its implementation, environment, test version, provider assumptions, passed cases, failed cases, skipped cases, and limitations.

A test suite can demonstrate that a particular implementation satisfies defined cases under stated assumptions. It cannot by itself establish that every deployment, identity configuration, or external provider behaves the same way.

## License

No open-source license has been selected yet. Unless and until a license is added, no permission to reuse, modify, or distribute this repository is granted beyond rights provided by applicable law.
