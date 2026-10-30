# Contributing

## Current project stage

The repository is specification-first. Contributions should strengthen clarity, testability, and the accuracy of stated guarantees before adding implementation breadth.

## Before proposing a change

- Read README.md, ARCHITECTURE.md, THREAT_MODEL.md, and CONFORMANCE.md.
- Identify the invariant or conformance case the change addresses.
- State whether the change affects compatibility or existing semantics.
- Include a failure scenario that demonstrates why the change is needed.

## Design expectations

Contributions should:

- Keep operation identity separate from attempt identity.
- Keep ownership generation separate from provider request identity.
- Distinguish local authorization from provider admission.
- Preserve unresolved outcomes.
- Avoid claiming guarantees that depend on undocumented provider behaviour.
- Prefer deterministic tests over timing-dependent tests.
- Document consistency, trust, and key-management assumptions.

## Changes to normative requirements

Changes to MUST/MUST NOT requirements require:

1. A written rationale.
2. A description of affected invariants.
3. At least one positive and one adversarial example.
4. Compatibility impact analysis.
5. Updated test scenarios.
6. Review of related architecture and threat-model sections.

## Tests

New executable tests should state their initial conditions, event ordering, injected fault, expected durable state, expected provider effect, and evidence needed to support the result.

A passing test must not be described as proof of a broader guarantee than the test establishes.

## Documentation style

Use precise, implementation-neutral language. Define terms before relying on them. Mark examples as illustrative. Separate normative requirements from recommendations and explanatory notes.

## Pull request checklist

- [ ] The change addresses a defined requirement or documented gap.
- [ ] Related documents and test vectors are updated.
- [ ] No guarantee is stated without its assumptions.
- [ ] Unresolved outcomes remain explicit.
- [ ] Compatibility impact is described.
- [ ] Tests are deterministic and reproducible, where applicable.
