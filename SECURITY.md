# Security Policy

## Scope

This project concerns ownership fencing, authorization at consequential boundaries, operation identity, provider reconciliation, and evidence integrity.

Security reports are welcome for defects in the specification, reference implementation, test harness, or evidence-verification process once those components exist.

## Reporting

Please do not publish details of an exploitable vulnerability in an issue before maintainers have had an opportunity to assess it.

Use GitHub's private vulnerability reporting feature if it is enabled for this repository. Otherwise, contact the repository maintainer through a private channel listed on the maintainer's GitHub profile.

Include:

- A concise description of the issue.
- Affected revision or component.
- Preconditions and deployment assumptions.
- Reproduction steps or a minimal test case.
- Potential impact.
- Any suggested mitigation.

Do not include live credentials, private customer data, or other secrets in a report.

## Review priorities

Reports involving the following behaviours are especially relevant:

- A stale ownership generation obtains new admission.
- A successor creates a duplicate provider effect after an unresolved predecessor attempt.
- An ambiguous result is incorrectly classified as success or failure.
- Evidence can be modified, substituted, or replayed without detection.
- A transition can be committed by a stale or unauthorized owner.

## Disclosure

Coordinated disclosure is preferred. The timing and content of any public advisory should account for affected users and the availability of mitigations.

## Current implementation status

This repository currently contains design documentation. There is no production implementation or security certification represented by this policy.
